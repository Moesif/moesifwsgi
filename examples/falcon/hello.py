import falcon
from falcon_multipart.middleware import MultipartMiddleware
from moesifwsgi import MoesifMiddleware
from wsgiref.simple_server import make_server


# Falcon follows the REST architectural style, meaning (among
# other things) that you think in terms of resources and state
# transitions, which map to HTTP verbs.
class HelloResource(object):
    def on_get(self, req, resp):
        """Handles GET requests"""
        resp.status = falcon.HTTP_200  # This is the default status
        resp.body = ('\nTwo things awe me most, the starry sky '
                     'above me and the moral law within me.\n'
                     '\n'
                     '    ~ Immanuel Kant\n\n')

    def on_post(self, req, resp, **kwargs):
        """Handles POST requests"""
        resp.status = falcon.HTTP_201  # This is the default status
        resp.body = ('\nTwo things awe me most, the starry sky '
                     'above me and the moral law within me.\n'
                     '\n'
                     '    ~ Immanuel Kant\n\n')

class HTML_test_resource(object):
    def on_get(self, req, resp):
        resp.status = falcon.HTTP_200
        resp.content_type = 'text/html'

        resp.body = """
        <p>Hello</p>
        <p>world</p>
        """

class XML_test_resource(object):
    def on_get(self, req, resp):
        resp.status = falcon.HTTP_200
        resp.content_type = 'text/xml'

        resp.body = "TEXT XML OK"

class Json_test_resource(object):
    def on_get(self, req, resp):
        resp.status = falcon.HTTP_200
        resp.content_type = 'application/json'

        resp.body = """{
            "foo": "bar"
        }"""

# falcon.API instances are callable WSGI apps
# Add the MultipartMiddleware to your api middlewares
app = falcon.API(middleware=[MultipartMiddleware()],
                 independent_middleware=True)

# Resources are represented by long-lived class instances
hello = HelloResource()

# things will handle all requests to the '/things' URL path
app.add_route('/hello', hello)
app.add_route('/test/html_response', HTML_test_resource())
app.add_route('/test/xml_response', XML_test_resource())
app.add_route('/test/json_response', Json_test_resource())

def identify_user(app, environ):
    return '12345'


def identify_company(app, environ):
    return '67890'


def get_token(app, environ):
    # If you don't want to use the standard WSGI session token,
    # add your custom code that returns a string for session/API token
    return "XXXXXXXXXXXXXX"


def should_skip(app, environ):
    # Your custom code that returns true to skip logging
    return "health/probe" in environ.get('PATH_INFO', '')


def get_metadata(app, environ):
    metadata = None
    try:
        metadata = {
            'response-body': environ['response-body'],
            'Content-Type': environ['response-headers']['Content-Type'.lower()],
            'Content-Length': environ['response-headers']['Content-Length'.lower()],
            'X-Moesif-Transaction-Id': environ['response-headers']['X-Moesif-Transaction-Id'.lower()]
        }
    except KeyError:
        print('environ has no field [response-body] or [response-headers]')
    return metadata


def mask_event(eventmodel):
    # Your custom code to change or remove any sensitive fields
    if 'password' in eventmodel.response.body:
        eventmodel.response.body['password'] = None
    return eventmodel

moesif_settings = {
    'APPLICATION_ID': 'Your Moesif Application Id',
    'IDENTIFY_USER': identify_user,
    'IDENTIFY_COMPANY': identify_company,
    'LOG_BODY': True,
    'SKIP': should_skip,
    'DEBUG': False,
    'MASK_EVENT_MODEL': mask_event,
    'GET_SESSION_TOKEN': get_token,
    'GET_METADATA': get_metadata,
    'CAPTURE_OUTGOING_REQUESTS': False
}

# Add Moesif Middleware
app = MoesifMiddleware(app, moesif_settings)

if __name__ == '__main__':
    with make_server('', 8000, app) as httpd:
        print('Serving on port 8000...')

        # Serve until process is killed
        httpd.serve_forever()
