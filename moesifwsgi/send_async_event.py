
class SendEventAsync:
    def exit_handler(self, scheduler, debug):
        try:
            # Shut down the scheduler
            scheduler.shutdown()
        except:
            if debug:
                print("Error while closing the queue or scheduler shut down")

    def send_event(self, api_client, batch_events, debug):
        try:
            if debug:
                print("Sending events to Moesif")
            batch_events_api_response = api_client.create_events_batch(batch_events)
            if debug:
                print("Events sent successfully")
            # Fetch Config ETag from response header
            batch_events_response_config_etag = batch_events_api_response.get("X-Moesif-Config-ETag")
            # Return Config Etag
            return batch_events_response_config_etag
        except Exception as ex:
            if debug:
                print("Error sending event to Moesif")
                print(str(ex))
            return None

    def async_client_create_event(self, api_client, moesif_events_queue, debug, batch_size):
        batch_events = []
        try:
            while moesif_events_queue.qsize() > 0:
                batch_events.append(moesif_events_queue.get_nowait())
                if len(batch_events) == batch_size:
                    batch_response = self.send_event(api_client, batch_events, debug)
                    batch_events.clear()
                    return batch_response
            if batch_events:
                return self.send_event(api_client, batch_events, debug)
            else:
                if debug:
                    print("No events to send")
        except:
            if debug:
                print("No message to read from the queue")
