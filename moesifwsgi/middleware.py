# -*- coding: utf-8 -*-
from datetime import datetime
import random
import itertools
import math
from moesifwsgi.config_manager import ConfigUpdateManager

from moesifwsgi.workers import BatchedWorkerPool

try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO
from moesifapi.moesif_api_client import *
from .update_companies import Company
from .update_users import User
from moesifpythonrequest.app_config.app_config import AppConfig
from .parse_body import ParseBody
from .logger_helper import LoggerHelper
from .moesif_data_holder import DataHolder
from .event_mapper import EventMapper
from .client_ip import ClientIp
from .http_response_catcher import HttpResponseCatcher
from moesifpythonrequest.start_capture.start_capture import StartCapture
import atexit


class MoesifMiddleware(object):
    """WSGI Middleware for recording of request-response"""
    def __init__(self, app, settings):
        self.app = app
        try:
            self.request_counter = itertools.count().next  # Threadsafe counter for Python 2
        except AttributeError:
            self.request_counter = itertools.count().__next__  # Threadsafe counter for Python 3

        if settings is None:
            raise Exception('Moesif Application ID is required in settings')
        self.settings = settings

        if settings.get('APPLICATION_ID', None):
            self.client = MoesifAPIClient(settings.get('APPLICATION_ID'))
        else:
            raise Exception('Moesif Application ID is required in settings')

        if settings.get('DEBUG', False):
            Configuration.BASE_URI = self.get_configuration_uri(settings, 'BASE_URI', 'LOCAL_MOESIF_BASEURL')
        Configuration.version = 'moesifwsgi-python/1.6.1'
        self.DEBUG = settings.get('DEBUG', False)
        self.logger_helper = LoggerHelper()
        if settings.get('CAPTURE_OUTGOING_REQUESTS', False):
            try:
                if self.DEBUG:
                    print('Start capturing outgoing requests for pid - ' + self.logger_helper.get_worker_pid())
                # Start capturing outgoing requests
                StartCapture().start_capture_outgoing(settings)
            except:
                print('Error while starting to capture the outgoing events for pid - ' + self.logger_helper.get_worker_pid())
        self.api_version = settings.get('API_VERSION')
        self.api_client = self.client.api
        self.LOG_BODY = self.settings.get('LOG_BODY', True)
        if self.DEBUG:
            response_catcher = HttpResponseCatcher()
            self.api_client.http_call_back = response_catcher
        self.client_ip = ClientIp()
        # AppConfig stores and fetches the config from the server
        self.app_config = AppConfig()
        self.config = ConfigUpdateManager(self.api_client, self.app_config, self.DEBUG)
        self.parse_body = ParseBody()
        self.event_mapper = EventMapper()
        # Create queues and threads which will batch and send events in the background
        self.worker_pool = BatchedWorkerPool(
            worker_count=settings.get('EVENT_WORKER_COUNT', 2),
            api_client=self.api_client,
            config=self.config,
            debug=self.DEBUG,
            max_queue_size=settings.get('EVENT_QUEUE_SIZE', 1000),
            batch_size=settings.get('BATCH_SIZE', 100),
            timeout=settings.get('EVENT_BATCH_TIMEOUT', 2)
        )
        # When shutting down, stop the worker pool and wait for it to finish
        atexit.register(self.worker_pool.stop)

    # Function to get configuration uri
    def get_configuration_uri(self, settings, field, deprecated_field):
        uri = settings.get(field)
        if uri:
            return uri
        else:
            return settings.get(deprecated_field, 'https://api.moesif.net')

    def __call__(self, environ, start_response):
        request_time = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
        if self.DEBUG:
            print("event request time: ", request_time)

        data_holder = DataHolder(
                        self.settings.get('DISABLED_TRANSACTION_ID', False),
                        self.request_counter(),
                        environ['REQUEST_METHOD'],
                        self.logger_helper.request_url(environ),
                        self.client_ip.get_client_address(environ),
                        [(k, v) for k,v in self.logger_helper.parse_request_headers(environ)],
                        *self.logger_helper.request_body(environ),
                        request_time
                    )

        response_headers_mapping = {}
        def _start_response(status, response_headers, *args):
            # Capture status and response_headers for later processing
            data_holder.capture_response_status(status, response_headers, self.DEBUG)

            if response_headers:
                try:
                    for pair in response_headers:
                        response_headers_mapping[pair[0]] = pair[1]
                except Exception as e:
                    print('Error while parsing response headers for pid - ' + self.logger_helper.get_worker_pid(), e)

            return start_response(status, response_headers, *args)

        response_chunks = data_holder.finish_response(self.app(environ, _start_response))
        if self.DEBUG:
            try:
                print("event response time for pid - " + self.logger_helper.get_worker_pid(), data_holder.response_time)
            except Exception as e:
                print("Error while fetching response time for pid - " + self.logger_helper.get_worker_pid(), e)

        data_holder.set_user_id(self.logger_helper.get_user_id(environ, self.settings, self.app, self.DEBUG, response_headers_mapping))
        data_holder.set_company_id(self.logger_helper.get_company_id(environ, self.settings, self.app, self.DEBUG, response_headers_mapping))
        data_holder.set_metadata(self.logger_helper.get_metadata(environ, self.settings, self.app, self.DEBUG))
        data_holder.set_session_token(self.logger_helper.get_session_token(environ, self.settings, self.app, self.DEBUG))

        # return data to WSGI server
        try:
            return response_chunks
        finally:
            if not self.logger_helper.should_skip(environ, self.settings, self.app, self.DEBUG):
                random_percentage = random.random() * 100

                # Prepare event to be sent to Moesif
                event_data = self.process_data(data_holder)

                event_sampling_percentage = self.config.get_sampling_percentage(event_data,
                                                                                   self.logger_helper.get_user_id(
                                                                                       environ, self.settings, self.app,
                                                                                       self.DEBUG, response_headers_mapping),
                                                                                   self.logger_helper.get_company_id(
                                                                                       environ, self.settings, self.app,
                                                                                       self.DEBUG, response_headers_mapping))

                if event_sampling_percentage >= random_percentage:
                    if event_data:
                        # Add Weight to the event
                        event_data.weight = 1 if event_sampling_percentage == 0 else math.floor(100 / event_sampling_percentage)
                        try:
                            # Add Event to the queue
                            if self.DEBUG:
                                print('Add Event to the queue for pid - ' + self.logger_helper.get_worker_pid())
                            self.worker_pool.add_event(event_data)
                        except Exception as ex:
                            if self.DEBUG:
                                print("Error while adding event to the queue for pid - " + self.logger_helper.get_worker_pid())
                                print(str(ex))
                    else:
                        if self.DEBUG:
                            print('Skipped Event as the moesif event model is None for pid - ' + self.logger_helper.get_worker_pid())
                else:
                    if self.DEBUG:
                        print("Skipped Event due to sampling percentage: " + str(event_sampling_percentage)
                              + " and random percentage: " + str(random_percentage) + " for pid - " + self.logger_helper.get_worker_pid())
            else:
                if self.DEBUG:
                    print('Skipped Event using should_skip configuration option for pid - ' + self.logger_helper.get_worker_pid())

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
