# -*- coding: utf-8 -*-

import logging
import time
import datetime
import threading
import copy
import json
import base64
import re
import copy

import itertools
from cStringIO import StringIO

from moesifapi.moesif_api_client import *
from moesifapi.api_helper import *
from moesifapi.exceptions.api_exception import *
from moesifapi.models import *

from .http_response_catcher import HttpResponseCatcher

class DataHolder(object):
    """Capture the data for a request-response."""
    def __init__(self, id, method, url, ip, user_id, session_token, request_headers, content_length, request_body):
        self.request_id = id
        self.method = method
        self.url = url
        self.ip_address = ip
        self.user_id = user_id
        self.session_token = session_token
        self.request_headers = request_headers
        self.content_length = content_length
        self.request_body = request_body
        self.status = -1
        self.response_headers = None
        self.response_chunks = None
        self.response_body_data = None
        self.request_time = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
        self.start_at = time.time()

    def capture_response_status(self, status, response_headers):
        self.status = status
        self.response_headers = response_headers

    def capture_body_data(self, body_data):
        if self.response_body_data is None:
            self.response_body_data = body_data
        else:
            self.response_body_data = self.response_body_data + body_data

    def finish_response(self, response_chunks):
        self.response_time = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
        self.response_chunks = response_chunks
        new_response_chunks = []
        stored_response_chunks = []
        for line in response_chunks:
            new_response_chunks.append(line)
            stored_response_chunks.append(line)
        self.response_chunks = stored_response_chunks
        return new_response_chunks


class MoesifMiddleware(object):
    """WSGI Middleware for recording of request-response"""
    def __init__(self, app, settings):
        self.app = app
        self.request_counter = itertools.count().next # Threadsafe counter

        if settings is None:
            raise Exception('Moesif Application ID is required in settings')
        self.settings = settings

        if settings.get('APPLICATION_ID', None):
            self.client = MoesifAPIClient(settings.get('APPLICATION_ID'))
        else:
            raise Exception('Moesif Application ID is required in settings')

        if settings.get('DEBUG', False):
            Configuration.BASE_URI = settings.get('LOCAL_MOESIF_BASEURL', 'https://api.moesif.net')

        self.DEBUG = settings.get('DEBUG', False)
        self.api_version = settings.get('API_VERSION')
        self.api_client = self.client.api

        self.regex_http_          = re.compile(r'^HTTP_.+$')
        self.regex_content_type   = re.compile(r'^CONTENT_TYPE$')
        self.regex_content_length = re.compile(r'^CONTENT_LENGTH$')
        if self.DEBUG:
            response_catcher = HttpResponseCatcher()
            self.api_client.http_call_back = response_catcher

    def __call__(self, environ, start_response):
        data_holder = DataHolder(
                        self.request_counter(),
                        environ['REQUEST_METHOD'],
                        self.request_url(environ),
                        self.get_client_address(environ),
                        self.get_user_id(environ),
                        self.get_session_token(environ),
                        [(k, v) for k,v in self.parse_request_headers(environ)],
                        *self.request_body(environ)
                    )

        def _start_response(status, response_headers, *args):
            # Capture status and response_headers for later processing
            data_holder.capture_response_status(status, response_headers)
            return start_response(status, response_headers, *args)
            # data.capture_response_status(status, response_headers)
            # write = start_response(status, response_headers, *args)
            # def my_write(body_data):
            #     data.capture_body_data(body_data)
            #     print('inside my_write')
            #     print(body_data)
            #     write(body_data)
            # return my_write

        response_chunks = data_holder.finish_response(self.app(environ, _start_response))

        def background_process():
            try:
                self.process_data(data_holder)
            except Exception as e:
                if self.DEBUG:
                    print('failed processing data but move on')
                    print(e)

        # return data to WSGI server
        try:
            return response_chunks
        finally:
            #background_process()
            if not self.should_skip(environ):
                sending_background_thread = threading.Thread(target=background_process)
                sending_background_thread.start()
            else:
                if self.DEBUG:
                    print('skipped')


    def process_data(self, data):
        req_body = None
        req_body_transfer_encoding = None
        try:
            if self.DEBUG:
                print("about to process request body" + data.request_body)
            if data.request_body:
                req_body = json.loads(data.request_body)
        except:
            if data.request_body:
                req_body = base64.standard_b64encode(data.request_body)
                req_body_transfer_encoding = 'base64'

        req_headers = None
        if data.request_headers:
            req_headers = dict(data.request_headers)


        event_req = EventRequestModel(time=data.request_time,
                                      uri=data.url,
                                      verb=data.method,
                                      api_version=self.api_version,
                                      ip_address=data.ip_address,
                                      headers=req_headers,
                                      body=req_body,
                                      transfer_encoding=req_body_transfer_encoding)

        response_content = None

        try:
            response_content = "".join(data.response_chunks)
        except:
            if self.DEBUG:
                print('try to join response chunks failed')

        rsp_body = None
        rsp_body_transfer_encoding = None
        if self.DEBUG:
            print("about to process response")
            print(response_content)
        if response_content:
            try:
                rsp_body = json.loads(response_content)
                if self.DEBUG:
                    print("jason parsed succesfully")
            except:
                if self.DEBUG:
                    print("could not json parse, so base64 encode")
                rsp_body = base64.standard_b64encode(response_content)
                rsp_body_transfer_encoding = 'base64'
                if self.DEBUG:
                    print("base64 encoded body: " + rsp_body)

        rsp_headers = None
        if data.response_headers:
            rsp_headers = dict(data.response_headers)

        response_status = None
        if data.status:
            response_status = int(data.status[:3])

        event_rsp = EventResponseModel(time=data.response_time,
                               status=response_status,
                               headers=rsp_headers,
                               body=rsp_body,
                               transfer_encoding=rsp_body_transfer_encoding)

        event_model = EventModel(request=event_req,
                                 response=event_rsp,
                                 user_id=data.user_id,
                                 session_token=data.session_token)

        try:
            mask_event_model = self.settings.get("MASK_EVENT_MODEL")
            if mask_event_model is not None:
                event_model = mask_event_model(event_model)
        except:
            if self.DEBUG:
                print("Can not execute MASK_EVENT_MODEL function. Please check moesif settings.")

        if self.DEBUG:
            print("sending event to moesif")
            print(APIHelper.json_serialize(event_model))
        try:
            self.api_client.create_event(event_model)
            if self.DEBUG:
                print("sent done")
        except APIException as inst:
            if 401 <= inst.response_code <= 403:
                print("Unauthorized access sending event to Moesif. Please check your Appplication Id.")
            if self.DEBUG:
                print("Error sending event to Moesif, with status code:")
                print(inst.response_code)


    def get_client_address(self, environ):
        try:
            return environ['HTTP_X_FORWARDED_FOR'].split(',')[-1].strip()
        except KeyError:
            return environ['REMOTE_ADDR']


    def get_user_id(self, environ):
        username = None
        try:
            identify_user = self.settings.get("IDENTIFY_USER")
            if identify_user is not None:
                username = identify_user(self.app, environ)
        except Exception as e:
            if self.DEBUG:
                print("can not execute identify_user function, please check moesif settings.")
                print(e)
        return username


    def get_session_token(self, environ):
        session_token = None
        # try the standard method for getting session id.
        # if 'HTTP_COOKIE' in environ:
        #     cookie = {s.split('=')[0].strip(): s.split('=')[1].strip() for s in environ['HTTP_COOKIE'].split(';')}
        #     session_token = cookie['sessionid']
        # then see if get_session_token is implemented.
        try:
            get_session = self.settings.get("GET_SESSION_TOKEN")
            if get_session is not None:
                session_token = get_session(self.app, environ)
        except Exception as e:
            if self.DEBUG:
                print("can not execute get_session function, please check moesif settings.")
                print(e)
        return session_token


    def should_skip(self, environ):
        try:
            skip_proc = self.settings.get("SKIP")
            if skip_proc is not None:
                return skip_proc(self.app, environ)
            else:
                return False
        except:
            if self.DEBUG:
                print("error trying to execute skip function.")
            return False
        return False


    def request_url(self, environ):
        return '{0}{1}{2}'.format(
                environ.get('SCRIPT_NAME', ''),
                environ.get('PATH_INFO', ''),
                '?' + environ['QUERY_STRING'] if environ.get('QUERY_STRING') else '',
            )


    _parse_headers_special = {
        'HTTP_CGI_AUTHORIZATION': 'Authorization',
        'CONTENT_LENGTH': 'Content-Length',
        'CONTENT_TYPE': 'Content-Type',
        }


    def parse_request_headers(self, environ):
        for cgi_var, value in environ.iteritems():
            if cgi_var in self._parse_headers_special:
                yield self._parse_headers_special[cgi_var], value
            elif cgi_var.startswith('HTTP_'):
                yield cgi_var[5:].title().replace('_', '-'), value


    def request_body(self, environ):
        content_length = environ.get('CONTENT_LENGTH')
        body = None
        if content_length:
            if content_length == '-1':
                # case where the content length is basically undetermined
                body = environ['wsgi.input'].read(-1)
                content_length = len(body)
            else:
                content_length = int(content_length)
                body = environ['wsgi.input'].read(content_length)
            environ['wsgi.input'] = StringIO(body) # reset request body for the nested app
        else:
            content_length = 0
        return content_length, body


def is_binary_content_type(content_type):
    type_subtype = content_type.split(';')
    _type, subtype = type_subtype.split('/')
    if _type == 'text':
        return False
    elif _type == 'application':
        return subtype not in (
            'atom+xml', 'ecmascript', 'json', 'javascript', 'rss+xml', 'soap+xml', 'xhtml+xml')
    else:
        return True
