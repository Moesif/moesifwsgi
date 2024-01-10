"""
    moesif.http_response_catcher
"""

from moesifapi.http.http_call_back import *
from .logger_helper import LoggerHelper
import logging

logger = logging.getLogger(__name__)

class HttpResponseCatcher(HttpCallBack):

    """A class used for catching the HttpResponse object from controllers.

    This class inherits HttpCallBack and implements the on_after_response
    method to catch the HttpResponse object as returned by the HttpClient
    after a request is executed.
    """

    def __init__(self):
        self.logger_helper = LoggerHelper()

    def on_before_request(self, request):
        pass

    def on_after_response(self, context):
        self.response = context.response
        logger.info('status from the Moesif API call for pid - ' + self.logger_helper.get_worker_pid())
        logger.info(context.response.status_code)
        logger.info('headers from moesif response for pid - ' + self.logger_helper.get_worker_pid())
        logger.info(context.response.headers)
        logger.info('body from moesif response for pid - ' + self.logger_helper.get_worker_pid())
        logger.info(context.response.raw_body)
        #pass
