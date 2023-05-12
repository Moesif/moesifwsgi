import queue
import threading
import time

from moesifwsgi.logger_helper import LoggerHelper

class Batcher(threading.Thread):
    def __init__(self, input_queue, output_queue, batch_size, timeout):
        super().__init__()
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.batch_size = batch_size
        self.timeout = timeout
        self._stop_event = threading.Event()  # Create a stop event

    def stop(self):
        self._stop_event.set()  # Set the stop event

    def run(self):
        while not self._stop_event.is_set():  # Check if the stop event is set
            try:
                batch = self._create_batch(block=True)
                if batch:
                    self.output_queue.put(batch)
            except Exception as e:
                print(f"Exception occurred in Batcher thread: {e}")
                continue

        # After stop event is set, continue to drain the input queue until it's empty
        self.timeout = 0
        while not self.input_queue.empty():
            try:
                batch = self._create_batch(block=False)
                if batch:
                    self.output_queue.put(batch)
            except Exception as e:
                print(f"Exception occurred in Batcher thread: {e}")
                continue

    def _create_batch(self, block):
        batch = []
        start_time = time.time()
        while len(batch) < self.batch_size and not self.input_queue.empty():
            try:
                item = self.input_queue.get(block=block, timeout=self.timeout)
                batch.append(item)
            except queue.Empty:
                break
            if time.time() - start_time > self.timeout:
                break
        return batch


class Worker(threading.Thread):
    def __init__(self, queue, api_client, debug):
        super().__init__()
        self.queue = queue
        self.api_client = api_client
        self.debug = debug
        self.logger_helper = LoggerHelper()
        self._stop_event = threading.Event()  # Create a stop event

    def stop(self):
        self._stop_event.set()  # Set the stop event

    def run(self):
        while not self._stop_event.is_set():  # Check if the stop event is set
            try:
                # blocking here until a batch is available is the desired behavior
                batch = self.queue.get(block=True, timeout=1)
                if batch:
                    self.send_events(batch)
                    self.queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Exception occurred in Worker thread: {e}")
                continue

    def send_events(self, batch_events):
        try:
            if self.debug:
                print("Sending events to Moesif for pid - " + self.logger_helper.get_worker_pid())
            batch_events_api_response = self.api_client.create_events_batch(batch_events)
            if self.debug:
                print("Events sent successfully for pid - " + self.logger_helper.get_worker_pid())
            # Fetch Config ETag from response header
            batch_events_response_config_etag = batch_events_api_response.get("X-Moesif-Config-ETag")
            # Return Config Etag
            return batch_events_response_config_etag
        except Exception as ex:
            if self.debug:
                print("Error sending event to Moesif for pid - " + self.logger_helper.get_worker_pid())
                print(str(ex))
            return None

class BatchedWorkerPool:
    def __init__(self, worker_count, event_queue, api_client, debug, batch_size, timeout):
        self.event_queue = event_queue
        self.batch_queue = queue.Queue()
        self.batch_size = batch_size
        self.timeout = timeout
        self.worker_count = worker_count
        self.api_client = api_client
        self.debug = debug

        # Start batcher
        self.batcher = Batcher(self.event_queue, self.batch_queue, self.batch_size, self.timeout)
        self.batcher.start()

        # Start workers
        self.workers = []
        for _ in range(self.worker_count):
            worker = Worker(self.b, self.api_client, self.debug)
            worker.start()
            self.workers.append(worker)

    def stop(self):
        # Stop batcher
        if self.batcher:
            self.batcher.stop()
            self.batcher.join()

        for worker in self.workers:
            worker.stop()

        # Wait for all tasks in the queue to be processed
        self.output_queue.join()

        for worker in self.workers:
            worker.join()

        # Clear workers
        self.batcher = None
        self.workers = []
