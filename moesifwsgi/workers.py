import queue
import threading
import time

from moesifwsgi.logger_helper import LoggerHelper

class Batcher(threading.Thread):
    def __init__(self, input_queue, output_queue, batch_size=10, timeout=2):
        super().__init__()
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.batch_size = batch_size
        self.timeout = timeout

    def run(self):
        while True:
            try:
                batch = []
                start_time = time.time()
                while len(batch) < self.batch_size:
                    try:
                        item = self.input_queue.get(timeout=self.timeout)
                        batch.append(item)
                    except queue.Empty:
                        break
                    if time.time() - start_time > self.timeout:
                        break
                if batch:
                    self.output_queue.put(batch)
            except Exception as e:
                print(f"Exception occurred in Batcher thread: {e}")
                continue

class Worker(threading.Thread):
    def __init__(self, queue, api_client, debug):
        super().__init__()
        self.queue = queue
        self.api_client = api_client
        self.debug = debug
        self.logger_helper = LoggerHelper()

    def run(self):
        while True:
            try:
                # blocking here until a batch is available is the desired behavior
                # however, for Python 2 compatibility, we need to specify a timeout
                # because Python 2's queue.Queue.get() method will not respond to
                # system signals while blocking without a timeout
                batch = self.queue.get(block=True, timeout=1)
                if batch:
                    self.send_events(batch)
                    self.queue.task_done()
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

def start_workers(queue, num_workers):
    workers = []
    for w in workers:
        worker = Worker(queue)
        workers.append(worker)
        worker.start()
    return workers
