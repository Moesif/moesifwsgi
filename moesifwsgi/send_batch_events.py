from datetime import datetime
from .logger_helper import LoggerHelper

class SendEventAsync:

    def __init__(self):
        self.logger_helper = LoggerHelper()

    def exit_handler(self, scheduler, debug):
        try:
            # Shut down the scheduler
            scheduler.remove_job('moesif_events_batch_job')
            scheduler.shutdown()
        except Exception as ex:
            if debug:
                print("Error while closing the queue or scheduler shut down for pid - " + self.logger_helper.get_worker_pid())
                print(str(ex))

    def send_events(self, api_client, batch_events, debug):
        try:
            if debug:
                print("Sending events to Moesif for pid - " + self.logger_helper.get_worker_pid())
            batch_events_api_response = api_client.create_events_batch(batch_events)
            if debug:
                print("Events sent successfully for pid - " + self.logger_helper.get_worker_pid())
            # Fetch Config ETag from response header
            batch_events_response_config_etag = batch_events_api_response.get("X-Moesif-Config-ETag")
            # Return Config Etag
            return batch_events_response_config_etag
        except Exception as ex:
            if debug:
                print("Error sending event to Moesif for pid - " + self.logger_helper.get_worker_pid())
                print(str(ex))
            return None

    def batch_events(self, api_client, moesif_events_queue, debug, batch_size):
        batch_events = []
        try:
            while not moesif_events_queue.empty():
                batch_events.append(moesif_events_queue.get_nowait())
                if len(batch_events) == batch_size:
                    break

            if batch_events:
                batch_response = self.send_events(api_client, batch_events, debug)
                batch_events[:] = []
                return batch_response, datetime.utcnow()
            else:
                if debug:
                    print("No events to send for pid - " + self.logger_helper.get_worker_pid())
                # Set the last time event job ran but no message to read from the queue
                return None, datetime.utcnow()
        except:
            if debug:
                print("No message to read from the queue for pid - " + self.logger_helper.get_worker_pid())
            # Set the last time event job ran when exception occurred while sending event
            return None, datetime.utcnow()
