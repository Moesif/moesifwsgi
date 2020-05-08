# -*- coding: utf-8 -*-

import time
from datetime import datetime, timedelta
import threading
import json
import base64
import re
import random
import uuid
from io import BytesIO
import itertools
import math
try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO

from moesifapi.moesif_api_client import *
from moesifapi.api_helper import *
from moesifapi.exceptions.api_exception import *
from moesifapi.models import *
from .update_companies import Company
from .update_users import User
from .app_config import AppConfig
from .client_ip import ClientIp
from .http_response_catcher import HttpResponseCatcher
from moesifpythonrequest.start_capture.start_capture import StartCapture
import gzip

class DataHolder(object):
    """Capture the data for a request-response."""
    def __init__(self, capture_transaction_id, id, method, url, ip, user_id, company_id, metadata, session_token, request_headers, content_length, request_body, transfer_encoding):
        self.request_id = id
        self.method = method
        self.url = url
        self.ip_address = ip
        self.user_id = user_id
        self.company_id = company_id
        self.metadata = metadata
        self.session_token = session_token
        self.request_headers = request_headers
        self.content_length = content_length
        self.request_body = request_body
        self.transfer_encoding = transfer_encoding
        self.status = -1
        self.response_headers = None
        self.response_chunks = None
        self.response_body_data = None
        self.request_time = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
        self.start_at = time.time()
        self.transaction_id = None
        if not capture_transaction_id:
            req_trans_id = [value for key, value in request_headers if key == "X-Moesif-Transaction-Id"]
            if req_trans_id:
                self.transaction_id = req_trans_id[0]
                if not self.transaction_id:
                    self.transaction_id = str(uuid.uuid4())
            else:
                self.transaction_id = str(uuid.uuid4())
            # Add transaction id to the request header
            self.request_headers.append(("X-Moesif-Transaction-Id", self.transaction_id))

    def capture_response_status(self, status, response_headers):
        self.status = status
        # Add transaction id to the response header
        if self.transaction_id:
            response_headers.append(("X-Moesif-Transaction-Id", self.transaction_id))
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
            Configuration.BASE_URI = settings.get('LOCAL_MOESIF_BASEURL', 'https://api.moesif.net')

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

        self.regex_http_          = re.compile(r'^HTTP_.+$')
        self.regex_content_type   = re.compile(r'^CONTENT_TYPE$')
        self.regex_content_length = re.compile(r'^CONTENT_LENGTH$')
        if self.DEBUG:
            response_catcher = HttpResponseCatcher()
            self.api_client.http_call_back = response_catcher
        self.client_ip = ClientIp()
        self.app_config = AppConfig()
        self.config = self.app_config.get_config(self.api_client, self.DEBUG)
        self.sampling_percentage = 100
        self.last_updated_time = datetime.utcnow()
        try:
            if self.config:
                self.config_etag, self.sampling_percentage, self.last_updated_time = self.app_config.parse_configuration(
                    self.config, self.DEBUG)
        except:
            if self.DEBUG:
                print('Error while parsing application configuration on initialization')


    def __call__(self, environ, start_response):
        data_holder = DataHolder(
                        self.settings.get('DISABLED_TRANSACTION_ID', False),
                        self.request_counter(),
                        environ['REQUEST_METHOD'],
                        self.request_url(environ),
                        self.client_ip.get_client_address(environ),
                        self.get_user_id(environ),
                        self.get_company_id(environ),
                        self.get_metadata(environ),
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
                random_percentage = random.random() * 100

                self.sampling_percentage = self.app_config.get_sampling_percentage(self.config, self.get_user_id(environ),
                                                                                   self.get_company_id(environ))
                if self.sampling_percentage >= random_percentage:
                    sending_background_thread = threading.Thread(target=background_process)
                    sending_background_thread.start()
            else:
                if self.DEBUG:
                    print('skipped')

    def start_with_json(self, body):
        return body.startswith("{") or body.startswith("[")

    def transform_headers(self, headers):
        return {k.lower(): v for k, v in headers.items()}

    def base64_body(self, body):
        return base64.standard_b64encode(body).decode(encoding="UTF-8"), "base64"

    def parse_bytes_body(self, body, content_encoding, headers):
        try:
            if content_encoding is not None and "gzip" in content_encoding.lower() or \
                    (headers is not None and "content-encoding" in headers and headers["content-encoding"] is not None
                     and "gzip" in (headers["content-encoding"]).lower()):
                parsed_body, transfer_encoding = self.base64_body(gzip.decompress(body))
            else:
                string_data = body.decode(encoding="UTF-8")
                if self.start_with_json(string_data):
                    parsed_body = json.loads(string_data)
                    transfer_encoding = 'json'
                else:
                    parsed_body, transfer_encoding = self.base64_body(body)
        except:
            parsed_body, transfer_encoding = self.base64_body(body)
        return parsed_body, transfer_encoding

    def parse_string_body(self, body, content_encoding, headers):
        try:
            if self.start_with_json(body):
                parsed_body = json.loads(body)
                transfer_encoding = 'json'
            elif content_encoding is not None and "gzip" in content_encoding.lower() or \
                    (headers is not None and "content-encoding" in headers and headers["content-encoding"] is not None
                     and "gzip" in (headers["content-encoding"]).lower()):
                decompressed_body = gzip.GzipFile(fileobj=StringIO(body)).read()
                parsed_body, transfer_encoding = self.base64_body(decompressed_body)
            else:
                parsed_body, transfer_encoding = self.base64_body(body)
        except:
            parsed_body, transfer_encoding = self.base64_body(body)
        return parsed_body, transfer_encoding

    def process_data(self, data):
        req_body = None
        req_body_transfer_encoding = None
        if self.LOG_BODY:
            req_body = data.request_body
            req_body_transfer_encoding = data.transfer_encoding

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
            try:
                response_content = b"".join(data.response_chunks)
            except:
                if self.DEBUG:
                    print('try to join response chunks failed - ')

        rsp_headers = None
        if data.response_headers:
            rsp_headers = dict(data.response_headers)

        rsp_body = None
        rsp_body_transfer_encoding = None
        if self.LOG_BODY and response_content:
            if self.DEBUG:
                print("about to process response")
                print(response_content)
            if isinstance(response_content, str):
                rsp_body, rsp_body_transfer_encoding = self.parse_string_body(response_content, None, self.transform_headers(rsp_headers))
            else:
                rsp_body, rsp_body_transfer_encoding = self.parse_bytes_body(response_content, None, self.transform_headers(rsp_headers))

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
                                 company_id=data.company_id,
                                 session_token=data.session_token,
                                 metadata=data.metadata,
                                 direction="Incoming")

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
            event_model.weight = 1 if self.sampling_percentage == 0 else math.floor(100 / self.sampling_percentage)
            event_api_response = self.api_client.create_event(event_model)
            event_response_config_etag = event_api_response.get("X-Moesif-Config-ETag")

            if event_response_config_etag is not None \
                    and self.config_etag is not None \
                    and self.config_etag != event_response_config_etag \
                    and datetime.utcnow() > self.last_updated_time + timedelta(minutes=5):
                try:
                    self.config = self.app_config.get_config(self.api_client, self.DEBUG)
                    self.config_etag, self.sampling_percentage, self.last_updated_time = self.app_config.parse_configuration(
                        self.config, self.DEBUG)
                except:
                    if self.DEBUG:
                        print('Error while updating the application configuration')
            if self.DEBUG:
                print("Event sent successfully")
        except APIException as inst:
            if 401 <= inst.response_code <= 403:
                print("Unauthorized access sending event to Moesif. Please check your Appplication Id.")
            if self.DEBUG:
                print("Error sending event to Moesif, with status code:")
                print(inst.response_code)

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

    def get_company_id(self, environ):
        company_id = None
        try:
            identify_company = self.settings.get("IDENTIFY_COMPANY")
            if identify_company is not None:
                company_id = identify_company(self.app, environ)
        except Exception as e:
            if self.DEBUG:
                print("can not execute identify_company function, please check moesif settings.")
                print(e)
        return company_id

    def get_metadata(self, environ):
        metadata = None
        try:
            get_meta = self.settings.get("GET_METADATA")
            if get_meta is not None:
                metadata = get_meta(self.app, environ)
        except Exception as e:
            if self.DEBUG:
                print("can not execute GET_METADATA function, please check moesif settings.")
                print(e)
        return metadata

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


    def request_url(self, environ):
        return '{0}{1}{2}{3}{4}'.format(
                environ.get('SCRIPT_NAME', ''),
                environ.get('wsgi.url_scheme', ''),
                '://' + environ.get('HTTP_HOST', ''),
                environ.get('PATH_INFO', ''),
                '?' + environ['QUERY_STRING'] if environ.get('QUERY_STRING') else '',
            )


    _parse_headers_special = {
        'HTTP_CGI_AUTHORIZATION': 'Authorization',
        'CONTENT_LENGTH': 'Content-Length',
        'CONTENT_TYPE': 'Content-Type',
        }


    def parse_request_headers(self, environ):
        try:
            for cgi_var, value in environ.iteritems():
                if cgi_var in self._parse_headers_special:
                    yield self._parse_headers_special[cgi_var], value
                elif cgi_var.startswith('HTTP_'):
                    yield cgi_var[5:].title().replace('_', '-'), value
        except AttributeError:
            for cgi_var, value in environ.items():
                if cgi_var in self._parse_headers_special:
                    yield self._parse_headers_special[cgi_var], value
                elif cgi_var.startswith('HTTP_'):
                    yield cgi_var[5:].title().replace('_', '-'), value

    def request_body(self, environ):
        content_encoding = environ.get('HTTP_CONTENT_ENCODING')
        content_length = environ.get('CONTENT_LENGTH')
        body = None
        encoded_body = None
        transfer_encoding = None
        if content_length:
            if content_length == '-1':
                # case where the content length is basically undetermined
                body = environ['wsgi.input'].read(-1)
                content_length = len(body)
            else:
                content_length = int(content_length)
                body = environ['wsgi.input'].read(content_length)

            if isinstance(body, str):
                environ['wsgi.input'] = StringIO(body) # reset request body for the nested app Python2
                encoded_body, transfer_encoding = self.parse_string_body(body, content_encoding, None)
            else:
                environ['wsgi.input'] = BytesIO(body) # reset request body for the nested app Python3
                encoded_body, transfer_encoding = self.parse_bytes_body(body, content_encoding, None)
        else:
            content_length = 0
        return content_length, encoded_body, transfer_encoding

    def update_user(self, user_profile):
        User().update_user(user_profile, self.api_client, self.DEBUG)

    def update_users_batch(self, user_profiles):
        User().update_users_batch(user_profiles, self.api_client, self.DEBUG)

    def update_company(self, company_profile):
        Company().update_company(company_profile, self.api_client, self.DEBUG)

    def update_companies_batch(self, companies_profiles):
        Company().update_companies_batch(companies_profiles, self.api_client, self.DEBUG)
