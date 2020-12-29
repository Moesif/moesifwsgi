try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO
from .parse_body import ParseBody
from io import BytesIO
import json
import base64


class LoggerHelper:

    def __init__(self):
        self.parse_body = ParseBody()
        self._parse_headers_special = {
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

    @classmethod
    def request_url(cls, environ):
        return '{0}{1}{2}{3}{4}'.format(
            environ.get('SCRIPT_NAME', ''),
            environ.get('wsgi.url_scheme', ''),
            '://' + environ.get('HTTP_HOST', ''),
            environ.get('PATH_INFO', ''),
            '?' + environ['QUERY_STRING'] if environ.get('QUERY_STRING') else '',
        )

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
                encoded_body, transfer_encoding = self.parse_body.parse_string_body(body, content_encoding, None)
            else:
                environ['wsgi.input'] = BytesIO(body) # reset request body for the nested app Python3
                encoded_body, transfer_encoding = self.parse_body.parse_bytes_body(body, content_encoding, None)
        else:
            content_length = 0
        return content_length, encoded_body, transfer_encoding

    @classmethod
    def transform_token(cls, token):
        if not isinstance(token, str):
            token = token.decode('utf-8')
        return token

    @classmethod
    def fetch_token(cls, request_headers, auth_header_name, token_type):
        return request_headers[auth_header_name].split(token_type, 1)[1].strip()

    @classmethod
    def split_token(cls, token):
        return token.split('.')

    def parse_authorization_header(self, token, field, debug):
        try:
            # Fix the padding issue before decoding
            token += '=' * (-len(token) % 4)
            # Decode the payload
            base64_decode = base64.b64decode(token)
            # Transform token to string to be compatible with Python 2 and 3
            base64_decode = self.transform_token(base64_decode)
            # Convert the payload to json
            json_decode = json.loads(base64_decode)
            # Check if field is present in the body
            if field in json_decode:
                # Fetch user Id
                return str(json_decode[field])
        except Exception as e:
            if debug:
                print("Error while parsing authorization header to fetch user id.")
                print(e)
        return None

    def get_user_id(self, environ, settings, app, debug):
        username = None
        try:
            identify_user = settings.get("IDENTIFY_USER")
            if identify_user is not None:
                username = identify_user(app, environ)
            if not username:
                # Parse request headers
                request_headers = dict([(k.lower(), v) for k, v in self.parse_request_headers(environ)])
                # Fetch the auth header name from the config
                auth_header_name = settings.get('AUTHORIZATION_HEADER_NAME', 'authorization').lower()
                # Fetch the field from the config
                field = settings.get('AUTHORIZATION_USER_ID_FIELD', 'sub')
                # Check if the auth header name in request headers
                if auth_header_name in request_headers:
                    # Fetch the token from the request headers
                    token = request_headers[auth_header_name]
                    # Check if token is of type Bearer
                    if 'Bearer' in token:
                        # Fetch the bearer token
                        token = self.fetch_token(request_headers, auth_header_name, 'Bearer')
                        # Split the bearer token by dot(.)
                        split_token = self.split_token(token)
                        # Check if payload is not None
                        if split_token[1]:
                            # Parse and set user Id
                            username = self.parse_authorization_header(split_token[1], field, debug)
                    # Check if token is of type Basic
                    elif 'Basic' in token:
                        # Fetch the basic token
                        token = self.fetch_token(request_headers, auth_header_name, 'Basic')
                        # Decode the token
                        decoded_token = base64.b64decode(token)
                        # Transform token to string to be compatible with Python 2 and 3
                        decoded_token = self.transform_token(decoded_token)
                        # Fetch the username and set the user Id
                        username = decoded_token.split(':', 1)[0].strip()
                    # Check if token is of user-defined custom type
                    else:
                        # Split the token by dot(.)
                        split_token = self.split_token(token)
                        # Check if payload is not None
                        if len(split_token) > 1 and split_token[1]:
                            # Parse and set user Id
                            username = self.parse_authorization_header(split_token[1], field, debug)
                        else:
                            # Parse and set user Id
                            username = self.parse_authorization_header(token, field, debug)
        except Exception as e:
            if debug:
                print("can not execute identify_user function, please check moesif settings.")
                print(e)
        return username

    @classmethod
    def get_company_id(cls, environ, settings, app, debug):
        company_id = None
        try:
            identify_company = settings.get("IDENTIFY_COMPANY")
            if identify_company is not None:
                company_id = identify_company(app, environ)
        except Exception as e:
            if debug:
                print("can not execute identify_company function, please check moesif settings.")
                print(e)
        return company_id

    @classmethod
    def get_metadata(cls, environ, settings, app, debug):
        metadata = None
        try:
            get_meta = settings.get("GET_METADATA")
            if get_meta is not None:
                metadata = get_meta(app, environ)
        except Exception as e:
            if debug:
                print("can not execute GET_METADATA function, please check moesif settings.")
                print(e)
        return metadata

    @classmethod
    def get_session_token(cls, environ, settings, app, debug):
        session_token = None
        try:
            get_session = settings.get("GET_SESSION_TOKEN")
            if get_session is not None:
                session_token = get_session(app, environ)
        except Exception as e:
            if debug:
                print("can not execute get_session function, please check moesif settings.")
                print(e)
        return session_token

    @classmethod
    def should_skip(cls, environ, settings, app, debug):
        try:
            skip_proc = settings.get("SKIP")
            if skip_proc is not None:
                return skip_proc(app, environ)
            else:
                return False
        except:
            if debug:
                print("error trying to execute skip function.")
            return False

    @classmethod
    def mask_event(cls, event_model, settings, debug):
        try:
            mask_event_model = settings.get("MASK_EVENT_MODEL")
            if mask_event_model is not None:
                return mask_event_model(event_model)
        except:
            if debug:
                print("Can not execute MASK_EVENT_MODEL function. Please check moesif settings.")
        return event_model
