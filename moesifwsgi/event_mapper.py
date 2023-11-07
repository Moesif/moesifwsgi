from moesifapi.models import *
from .parse_body import ParseBody
from .logger_helper import LoggerHelper


class EventMapper:

    def __init__(self):
        self.parse_body = ParseBody()
        self.logger_helper = LoggerHelper()

    @classmethod
    def to_event(cls, data, event_req, event_rsp, blocked_by):
        # Prepare Event Model
        return EventModel(request=event_req,
                          response=event_rsp,
                          user_id=data.user_id,
                          company_id=data.company_id,
                          session_token=data.session_token,
                          metadata=data.metadata,
                          direction="Incoming",
                          blocked_by=blocked_by)

    @classmethod
    def to_request(cls, data, log_body, api_version):
        req_body = None
        req_transfer_encoding = None
        if log_body:
            req_body = data.request_body
            req_transfer_encoding = data.transfer_encoding

        req_headers = None
        if data.request_headers:
            req_headers = dict(data.request_headers)

        # Prepare Event Request Model
        return EventRequestModel(time=data.request_time,
                                 uri=data.url,
                                 verb=data.method,
                                 api_version=api_version,
                                 ip_address=data.ip_address,
                                 headers=req_headers,
                                 body=req_body,
                                 transfer_encoding=req_transfer_encoding)

    def to_response(self, data, log_body, debug):
        response_content = None

        try:
            response_content = "".join(data.response_chunks)
        except:
            try:
                response_content = b"".join(data.response_chunks)
            except:
                if debug:
                    print('try to join response chunks failed - for pid - ' + self.logger_helper.get_worker_pid())

        rsp_headers = None
        if data.response_headers:
            rsp_headers = dict(data.response_headers)

        rsp_body = None
        rsp_transfer_encoding = None
        if log_body and response_content:
            if debug:
                print("about to process response for pid - " + self.logger_helper.get_worker_pid())
                print(response_content)
            if isinstance(response_content, str):
                rsp_body, rsp_transfer_encoding = self.parse_body.parse_string_body(response_content, None,
                                                                                         self.parse_body.transform_headers(
                                                                                             rsp_headers))
            else:
                rsp_body, rsp_transfer_encoding = self.parse_body.parse_bytes_body(response_content, None,
                                                                                        self.parse_body.transform_headers(
                                                                                            rsp_headers))

        response_status = None
        if data.status:
            response_status = int(data.status[:3])

        # Prepare Event Response Model
        return EventResponseModel(time=data.response_time,
                                  status=response_status,
                                  headers=rsp_headers,
                                  body=rsp_body,
                                  transfer_encoding=rsp_transfer_encoding)
