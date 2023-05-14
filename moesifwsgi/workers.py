import queue
import threading
import time

from moesifwsgi.logger_helper import LoggerHelper

class Batcher(threading.Thread):
    """
    A class used for batching events. This runs in a single background thread,
    and consumes events from the input queue, executes batch size and maximum 
    wait time constraints and puts batches of events into the batch queue for
    the worker threads to consume.
    """
    def __init__(self, event_queue, batch_queue, batch_size, timeout):
        super().__init__()
        self.event_queue = event_queue # input queue
        self.batch_queue = batch_queue # output queue
        # batch_size is used to control how many events are in a batch maximum
        self.batch_size = batch_size
        # timeout is used to control how long the batcher will wait for the next event
        self.timeout = timeout
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def run(self):
        # Continue to consume the input queue until stop event is set
        while not self._stop_event.is_set():
            try:
                batch = self._create_batch(block=True)
                if batch:
                    self.batch_queue.put(batch)
            except Exception as e:
                print(f"Exception occurred in Batcher thread: {e}")
                continue

        # After stop event is set, continue to drain the input queue until it's empty
        self.timeout = 0
        while not self.event_queue.empty():
            try:
                batch = self._create_batch(block=False)
                if batch:
                    self.batch_queue.put(batch)
            except Exception as e:
                print(f"Exception occurred in Batcher thread: {e}")
                continue

    def _create_batch(self, block):
        batch = []
        start_time = time.time()
        # Continue to consume the input queue until the batch is full or the batcher has been waiting for too long
        while len(batch) < self.batch_size and not self.event_queue.empty():
            # Calculate the max wait time for the next event in the batch based on the timeout
            max_wait = self.timeout - (time.time() - start_time)
            try:
                # If block is True, this will block until the next event is available which is the default behavior we want
                # this is the primary wait loop which aggregates events into a batch and enforces the max wait time
                # if block is False, this will return immediately when the input queue is empty, and this is used during shutdown
                item = self.event_queue.get(block=block, timeout=max_wait)
                batch.append(item)
            except queue.Empty:
                break
            # If the batcher has been waiting for too long, return the batch
            if time.time() - start_time >= self.timeout:
                break
        return batch


class Worker(threading.Thread):
    """
    A class used for sending events to Moesif asynchronously. This runs in a pool of
    background threads, and consumes batches of events from the batch queue.
    """
    def __init__(self, queue, api_client, config, debug):
        super().__init__()
        self.queue = queue
        self.api_client = api_client
        self.config = config
        self.debug = debug
        self.logger_helper = LoggerHelper()
        # stop_event is used to signal the worker to stop during graceful shutdown
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

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
            # Update the configuration if necessary
            etag = batch_events_api_response.get("X-Moesif-Config-ETag")
            self.config.check_and_update(etag)
            if self.debug:
                print("Events sent successfully for pid - " + self.logger_helper.get_worker_pid())
        except Exception as ex:
            if self.debug:
                print("Error sending event to Moesif for pid - " + self.logger_helper.get_worker_pid())
                print(str(ex))

class BatchedWorkerPool:
    """
    A class used for managing a pool of workers and a batcher. This class is
    responsible for starting and stopping the workers and the batcher, and
    for adding events to the event queue.
    """
    def __init__(self, worker_count, api_client, config, debug, max_queue_size, batch_size, timeout):
        self.event_queue = queue.Queue(maxsize=max_queue_size)
        self.batch_queue = queue.Queue(maxsize=max_queue_size)
        self.batch_size = batch_size
        self.timeout = timeout
        self.worker_count = worker_count
        self.api_client = api_client
        self.config = config
        self.debug = debug

        # Start batcher
        self.batcher = Batcher(self.event_queue, self.batch_queue, self.batch_size, self.timeout)
        self.batcher.start()

        # Start workers
        self.workers = []
        for _ in range(self.worker_count):
            worker = Worker(self.batch_queue, self.api_client, self.config, self.debug)
            worker.start()
            self.workers.append(worker)
    
    def add_event(self, event):
        self.event_queue.put(event)

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
