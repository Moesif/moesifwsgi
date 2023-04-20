from datetime import datetime
import time
import uuid
from .logger_helper import LoggerHelper

class DataHolder(object):
    """Capture the data for a request-response."""
    def __init__(self, disable_capture_transaction_id, id, method, url, ip, request_headers, content_length, request_body, transfer_encoding, request_time):
        self.request_id = id
        self.method = method
        self.url = url
        self.ip_address = ip
        self.user_id = None
        self.company_id = None
        self.metadata = None
        self.session_token = None
        self.request_headers = request_headers
        self.content_length = content_length
        self.request_body = request_body
        self.transfer_encoding = transfer_encoding
        self.status = -1
        self.response_headers = None
        self.response_chunks = None
        self.response_body_data = None
        self.request_time = request_time
        self.start_at = time.time()
        self.transaction_id = None
        self.logger_helper = LoggerHelper()

        if not disable_capture_transaction_id:
            req_trans_id = [value for key, value in request_headers if key == "X-Moesif-Transaction-Id"]
            if req_trans_id:
                self.transaction_id = req_trans_id[0]
                if not self.transaction_id:
                    self.transaction_id = str(uuid.uuid4())
            else:
                self.transaction_id = str(uuid.uuid4())
            # Add transaction id to the request header
            self.request_headers.append(("X-Moesif-Transaction-Id", self.transaction_id))

    def set_user_id(self, user_id):
        self.user_id = user_id

    def set_company_id(self, company_id):
        self.company_id = company_id

    def set_metadata(self, metadata):
        self.metadata = metadata

    def set_session_token(self, session_token):
        self.session_token = session_token

    def capture_response_status(self, status, response_headers, debug):
        self.status = status
        # Add transaction id to the response header
        if self.transaction_id:
            response_headers.append(("X-Moesif-Transaction-Id", self.transaction_id))
        # Add worker process Id
        if debug:
            response_headers.append(("X-Moesif-Wsgi-Pid", self.logger_helper.get_worker_pid()))
        self.response_headers = response_headers

    def capture_body_data(self, body_data):
        if self.response_body_data is None:
            self.response_body_data = body_data
        else:
            self.response_body_data = self.response_body_data + body_data

    def finish_response(self, response_chunks):
        self.response_time = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
        self.response_chunks = response_chunks
        new_response_chunks = []
        stored_response_chunks = []
        for line in response_chunks:
            new_response_chunks.append(line)
            stored_response_chunks.append(line)
        self.response_chunks = stored_response_chunks
        return new_response_chunks

