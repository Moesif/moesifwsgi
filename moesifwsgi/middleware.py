# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
import queue
import random
import itertools
import math
try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO
from moesifapi.moesif_api_client import *
from .update_companies import Company
from .update_users import User
from .app_config import AppConfig
from .parse_body import ParseBody
from .logger_helper import LoggerHelper
from .moesif_data_holder import DataHolder
from .event_mapper import EventMapper
from .send_batch_events import SendEventAsync
from .client_ip import ClientIp
from .http_response_catcher import HttpResponseCatcher
from moesifpythonrequest.start_capture.start_capture import StartCapture
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
import atexit
import logging


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
        Configuration.version = 'moesifwsgi-python/1.3.5'
        self.DEBUG = settings.get('DEBUG', False)
        if settings.get('CAPTURE_OUTGOING_REQUESTS', False):
            try:
                if self.DEBUG:
                    print('Start capturing outgoing requests')
                # Start capturing outgoing requests
                StartCapture().start_capture_outgoing(settings)
            except:
                print('Error while starting to capture the outgoing events')
        self.api_version = settings.get('API_VERSION')
        self.api_client = self.client.api
        self.LOG_BODY = self.settings.get('LOG_BODY', True)
        if self.DEBUG:
            response_catcher = HttpResponseCatcher()
            self.api_client.http_call_back = response_catcher
        self.client_ip = ClientIp()
        self.app_config = AppConfig()
        self.parse_body = ParseBody()
        self.logger_helper = LoggerHelper()
        self.event_mapper = EventMapper()
        self.send_async_events = SendEventAsync()
        self.config_etag = None
        self.config = self.app_config.get_config(self.api_client, self.DEBUG)
        self.sampling_percentage = 100
        self.last_updated_time = datetime.utcnow()
        self.moesif_events_queue = queue.Queue()
        self.BATCH_SIZE = self.settings.get('BATCH_SIZE', 25)
        self.last_event_job_run_time = datetime(1970, 1, 1, 0, 0)  # Assuming job never ran, set it to epoch start time
        self.scheduler = None
        self.is_event_job_scheduled = False
        try:
            if self.config:
                self.config_etag, self.sampling_percentage, self.last_updated_time = self.app_config.parse_configuration(
                    self.config, self.DEBUG)
        except Exception as ex:
            if self.DEBUG:
                print('Error while parsing application configuration on initialization')
                print(str(ex))

    # Function to get configuration uri
    def get_configuration_uri(self, settings, field, deprecated_field):
        uri = settings.get(field)
        if uri:
            return uri
        else:
            return settings.get(deprecated_field, 'https://api.moesif.net')

    def __call__(self, environ, start_response):
        data_holder = DataHolder(
                        self.settings.get('DISABLED_TRANSACTION_ID', False),
                        self.request_counter(),
                        environ['REQUEST_METHOD'],
                        self.logger_helper.request_url(environ),
                        self.client_ip.get_client_address(environ),
                        self.logger_helper.get_user_id(environ, self.settings, self.app, self.DEBUG),
                        self.logger_helper.get_company_id(environ, self.settings, self.app, self.DEBUG),
                        self.logger_helper.get_metadata(environ, self.settings, self.app, self.DEBUG),
                        self.logger_helper.get_session_token(environ, self.settings, self.app, self.DEBUG),
                        [(k, v) for k,v in self.logger_helper.parse_request_headers(environ)],
                        *self.logger_helper.request_body(environ)
                    )

        def _start_response(status, response_headers, *args):
            # Capture status and response_headers for later processing
            data_holder.capture_response_status(status, response_headers)
            return start_response(status, response_headers, *args)

        response_chunks = data_holder.finish_response(self.app(environ, _start_response))

        # return data to WSGI server
        try:
            return response_chunks
        finally:
            if not self.logger_helper.should_skip(environ, self.settings, self.app, self.DEBUG):
                random_percentage = random.random() * 100

                self.sampling_percentage = self.app_config.get_sampling_percentage(self.config,
                                                                                   self.logger_helper.get_user_id(environ, self.settings, self.app, self.DEBUG),
                                                                                   self.logger_helper.get_company_id(environ, self.settings, self.app, self.DEBUG))

                if self.sampling_percentage >= random_percentage:
                    # Prepare event to be sent to Moesif
                    event_data = self.process_data(data_holder)
                    if event_data:
                        # Add Weight to the event
                        event_data.weight = 1 if self.sampling_percentage == 0 else math.floor(100 / self.sampling_percentage)
                        try:
                            if not self.is_event_job_scheduled and datetime.utcnow() > self.last_event_job_run_time + timedelta(
                                    minutes=5):
                                try:
                                    self.schedule_background_job()
                                    self.is_event_job_scheduled = True
                                    self.last_event_job_run_time = datetime.utcnow()
                                except Exception as ex:
                                    self.is_event_job_scheduled = False
                                    if self.DEBUG:
                                        print('Error while starting the event scheduler job in background')
                                        print(str(ex))
                            # Add Event to the queue
                            if self.DEBUG:
                                print('Add Event to the queue')
                            self.moesif_events_queue.put(event_data)
                        except Exception as ex:
                            if self.DEBUG:
                                print("Error while adding event to the queue")
                                print(str(ex))
                    else:
                        if self.DEBUG:
                            print('Skipped Event as the moesif event model is None')
                else:
                    if self.DEBUG:
                        print("Skipped Event due to sampling percentage: " + str(self.sampling_percentage) + " and random percentage: " + str(random_percentage))
            else:
                if self.DEBUG:
                    print('Skipped Event using should_skip configuration option')

    def process_data(self, data):

        # Prepare Event Request Model
        event_req = self.event_mapper.to_request(data, self.LOG_BODY, self.api_version)

        # Prepare Event Response Model
        event_rsp = self.event_mapper.to_response(data, self.LOG_BODY, self.DEBUG)

        # Prepare Event Model
        event_model = self.event_mapper.to_event(data, event_req, event_rsp)

        # Mask Event Model
        return self.logger_helper.mask_event(event_model, self.settings, self.DEBUG)

    # Function to listen to the send event job response
    def moesif_event_listener(self, event):
        if event.exception:
            if self.DEBUG:
                print('Error reading response from the scheduled job')
        else:
            if event.retval:
                response_etag, self.last_event_job_run_time = event.retval
                if response_etag is not None \
                    and self.config_etag is not None \
                    and self.config_etag != response_etag \
                        and datetime.utcnow() > self.last_updated_time + timedelta(minutes=5):
                    try:
                        self.config = self.app_config.get_config(self.api_client, self.DEBUG)
                        self.config_etag, self.sampling_percentage, self.last_updated_time = self.app_config.parse_configuration(
                            self.config, self.DEBUG)
                    except Exception as ex:
                        if self.DEBUG:
                            print('Error while updating the application configuration')
                            print(str(ex))

    def schedule_background_job(self):
        try:
            if not self.scheduler:
                self.scheduler = BackgroundScheduler(daemon=True)
            if not self.scheduler.get_jobs():
                self.scheduler.add_listener(self.moesif_event_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
                self.scheduler.start()
                self.scheduler.add_job(
                    func=lambda: self.send_async_events.batch_events(self.api_client, self.moesif_events_queue,
                                                                     self.DEBUG, self.BATCH_SIZE),
                    trigger=IntervalTrigger(seconds=2),
                    id='moesif_events_batch_job',
                    name='Schedule events batch job every 2 second',
                    replace_existing=True)

                # Avoid passing logging message to the ancestor loggers
                logging.getLogger('apscheduler.executors.default').setLevel(logging.WARNING)
                logging.getLogger('apscheduler.executors.default').propagate = False

                # Exit handler when exiting the app
                atexit.register(lambda: self.send_async_events.exit_handler(self.scheduler, self.DEBUG))
        except Exception as ex:
            if self.DEBUG:
                print("Error when scheduling the job")
                print(str(ex))

    def update_user(self, user_profile):
        User().update_user(user_profile, self.api_client, self.DEBUG)

    def update_users_batch(self, user_profiles):
        User().update_users_batch(user_profiles, self.api_client, self.DEBUG)

    def update_company(self, company_profile):
        Company().update_company(company_profile, self.api_client, self.DEBUG)

    def update_companies_batch(self, companies_profiles):
        Company().update_companies_batch(companies_profiles, self.api_client, self.DEBUG)
