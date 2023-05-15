# -*- coding: utf-8 -*-
import itertools
import math
import random
from datetime import datetime
import sys

from moesifwsgi.config_manager import ConfigUpdateManager
from moesifwsgi.workers import BatchedWorkerPool

try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO

import atexit
import logging

from moesifapi.moesif_api_client import *
from moesifpythonrequest.app_config.app_config import AppConfig
from moesifpythonrequest.start_capture.start_capture import StartCapture

from .client_ip import ClientIp
from .event_mapper import EventMapper
from .http_response_catcher import HttpResponseCatcher
from .logger_helper import LoggerHelper
from .moesif_data_holder import DataHolder
from .parse_body import ParseBody
from .update_companies import Company
from .update_users import User

logger = logging.getLogger(__name__)


class MoesifMiddleware(object):
    """WSGI Middleware for recording of request-response"""

    def __init__(self, app, settings):
        self.app = app
        self.settings = settings
        self.DEBUG = self.settings.get("DEBUG", False)
        self.initialize_logger()
        self.validate_settings()

        self.initialize_counter()
        self.initialize_client()
        self.initialize_config()
        self.initialize_worker_pool()

        # graceful shutodown handlers
        atexit.register(self.worker_pool.stop)

    def initialize_logger(self):
        """Initialize logger mirroring the debug and stdout behavior of previous print statements for compatibility"""
        logging.basicConfig(
            level=logging.DEBUG if self.DEBUG else logging.INFO,
            format='%(asctime)s\t%(levelname)s\tPID: %(process)d\tThread: %(thread)d\t%(funcName)s\t%(message)s',
            handlers=[logging.StreamHandler()]
        )

    def validate_settings(self):
        if self.settings is None or not self.settings.get("APPLICATION_ID", None):
            raise Exception("Moesif Application ID is required in settings")

    def initialize_counter(self):
        try:
            self.request_counter = itertools.count().next  # Threadsafe counter for Python 2
        except AttributeError:
            self.request_counter = itertools.count().__next__  # Threadsafe counter for Python 3
        self.dropped_events = 0
        self.parse_body = ParseBody()
        self.event_mapper = EventMapper()
        self.logger_helper = LoggerHelper()

    def initialize_client(self):
        self.api_version = self.settings.get("API_VERSION")
        self.client = MoesifAPIClient(self.settings.get("APPLICATION_ID"))
        self.api_client = self.client.api

    def initialize_config(self):
        if self.DEBUG:
            logger.debug("Debug is enabled. Starting Moesif middleware for pid - " + self.logger_helper.get_worker_pid())
            response_catcher = HttpResponseCatcher()
            self.api_client.http_call_back = response_catcher
            Configuration.BASE_URI = self.settings.get("BASE_URI") or self.settings.get("LOCAL_MOESIF_BASEURL", "https://api.moesif.net")
        Configuration.version = "moesifwsgi-python/1.6.1"
        if self.settings.get("CAPTURE_OUTGOING_REQUESTS", False):
            self.start_capture_outgoing()

        self.LOG_BODY = self.settings.get("LOG_BODY", True)
        self.client_ip = ClientIp()
        self.app_config = AppConfig()
        self.config = ConfigUpdateManager(self.api_client, self.app_config, self.DEBUG)

    def initialize_worker_pool(self):
        # Create queues and threads which will batch and send events in the background
        self.worker_pool = BatchedWorkerPool(
            worker_count=self.settings.get("EVENT_WORKER_COUNT", 2),
            api_client=self.api_client,
            config=self.config,
            debug=self.DEBUG,
            max_queue_size=self.settings.get("EVENT_QUEUE_SIZE", 10000),
            batch_size=self.settings.get("BATCH_SIZE", 100),
            timeout=self.settings.get("EVENT_BATCH_TIMEOUT", 2),
        )

    def __call__(self, environ, start_response):
        request_time = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
        logger.debug(f"event request time: {request_time}")

        event_info = self.prepare_event_info(environ, start_response, request_time)

        response_headers_mapping = {}
        def _start_response(status, response_headers, *args):
            # Capture status and response_headers for later processing
            event_info.capture_response_status(status, response_headers, self.DEBUG)
            if response_headers:
                try:
                    for pair in response_headers:
                        response_headers_mapping[pair[0]] = pair[1]
                except Exception as e:
                    logger.exception("Error while parsing response headers", e)
            return start_response(status, response_headers, *args)
        response_chunks = event_info.finish_response(self.app(environ, _start_response))

        try:
            logger.debug(f"event response time: {event_info.response_time}")
        except Exception as e:
            logger.exception(f"Error while fetching response time", e)

        self.add_user_and_metadata(event_info, environ, response_headers_mapping)

        try:
            return response_chunks
        finally:
            self.process_and_add_event_if_required(event_info, environ, response_headers_mapping)

    def prepare_event_info(self, environ, start_response, request_time):
        event_info = DataHolder(
            self.settings.get("DISABLED_TRANSACTION_ID", False),
            self.request_counter(),
            environ["REQUEST_METHOD"],
            self.logger_helper.request_url(environ),
            self.client_ip.get_client_address(environ),
            [(k, v) for k, v in self.logger_helper.parse_request_headers(environ)],
            *self.logger_helper.request_body(environ),
            request_time,
        )
        return event_info

    def add_user_and_metadata(self, event_info, environ, response_headers_mapping):
        event_info.set_user_id(self.logger_helper.get_user_id(environ, self.settings, self.app, self.DEBUG, response_headers_mapping))
        event_info.set_company_id(self.logger_helper.get_company_id(environ, self.settings, self.app, self.DEBUG, response_headers_mapping))
        event_info.set_metadata(self.logger_helper.get_metadata(environ, self.settings, self.app, self.DEBUG))
        event_info.set_session_token(self.logger_helper.get_session_token(environ, self.settings, self.app, self.DEBUG))

    def process_and_add_event_if_required(self, event_info, environ, response_headers_mapping):
        if event_info is None:
            logger.debug("Skipped Event as the moesif event model is None")
            return
        if self.logger_helper.should_skip(environ, self.settings, self.app, self.DEBUG):
            logger.debug("Skipped Event using should_skip configuration option")
            return
                
        # Prepare event to be sent to Moesif and check the config for applicable sampling rules
        event_data = self.process_data(event_info)
        event_sampling_percentage = self.config.get_sampling_percentage(
            event_data,
            self.logger_helper.get_user_id(environ, self.settings, self.app, self.DEBUG, response_headers_mapping),
            self.logger_helper.get_company_id(environ, self.settings, self.app, self.DEBUG, response_headers_mapping)
        )

        # if the event has a sample rate of less than 100, then we need to check if this event should be skipped and not sent to Moesif
        random_percentage = random.random() * 100
        if random_percentage >= event_sampling_percentage:
            logger.debug("Skipped Event due to sampling percentage: " + str(event_sampling_percentage) + " and random percentage: " + str(random_percentage))
            return

        # Add proportionate weight to the event for sampling percentage lower than 100
        event_data.weight = 1 if event_sampling_percentage == 0 else math.floor(100 / event_sampling_percentage)
        try:
            # Add Event to the queue if able and count the dropped event if at capacity
            if self.worker_pool.add_event(event_data):
                logger.debug("Add Event to the queue")
            else:
                self.dropped_events += 1
                logger.info("Dropped Event due to queue capacity drop_count=" + str(self.dropped_events))
        # add_event does not throw exceptions so this is unexepected
        except Exception as ex:
            logger.exception("Error while adding event to the queue for", ex)


    def process_data(self, data):
        # Prepare Event Request Model
        event_req = self.event_mapper.to_request(data, self.LOG_BODY, self.api_version)

        # Prepare Event Response Model
        event_rsp = self.event_mapper.to_response(data, self.LOG_BODY, self.DEBUG)

        # Prepare Event Model
        event_model = self.event_mapper.to_event(data, event_req, event_rsp)

        # Mask Event Model
        return self.logger_helper.mask_event(event_model, self.settings, self.DEBUG)

    def update_user(self, user_profile):
        User().update_user(user_profile, self.api_client, self.DEBUG)

    def update_users_batch(self, user_profiles):
        User().update_users_batch(user_profiles, self.api_client, self.DEBUG)

    def update_company(self, company_profile):
        Company().update_company(company_profile, self.api_client, self.DEBUG)

    def update_companies_batch(self, companies_profiles):
        Company().update_companies_batch(companies_profiles, self.api_client, self.DEBUG)
