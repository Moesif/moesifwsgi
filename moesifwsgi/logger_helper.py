try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO
from .parse_body import ParseBody
from io import BytesIO


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

    def request_url(self, environ):
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

    def get_user_id(self, environ, settings, app, debug):
        username = None
        try:
            identify_user = settings.get("IDENTIFY_USER")
            if identify_user is not None:
                username = identify_user(app, environ)
        except Exception as e:
            if debug:
                print("can not execute identify_user function, please check moesif settings.")
                print(e)
        return username

    def get_company_id(self, environ, settings, app, debug):
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

    def get_metadata(self, environ, settings, app, debug):
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

    def get_session_token(self, environ, settings, app, debug):
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

    def should_skip(self, environ, settings, app, debug):
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

    def mask_event(self, event_model, settings, debug):
        try:
            mask_event_model = settings.get("MASK_EVENT_MODEL")
            if mask_event_model is not None:
                return mask_event_model(event_model)
        except:
            if debug:
                print("Can not execute MASK_EVENT_MODEL function. Please check moesif settings.")
        return event_model
