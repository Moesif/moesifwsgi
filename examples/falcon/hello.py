import gzip

import falcon
from falcon_multipart.middleware import MultipartMiddleware
from moesifwsgi import MoesifMiddleware
import json
import falcon_jsonify



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
            <!DOCTYPE html>
            <html>
            <body>
        
            <h1>My First Heading</h1>
        
            <p>My first paragraph.</p>
        
            </body>
            </html>
            """

class XML_test_resource(object):
    def on_get(self, req, resp):
        resp.status = falcon.HTTP_200
        resp.content_type = 'text/xml'

        resp.body = """
            <note>
            <to>Tove</to>
            <from>Jani</from>
            <heading>Reminder</heading>
            <body>Don't forget me this weekend!</body>
            </note>
            """


class Json_test_resource(object):
    def on_get(self, req, resp):
        resp.status = falcon.HTTP_200
        resp.content_type = 'application/json'

        resp.body = json.dumps({'id': 123, 'name': 'work in office'})

class gzip_test_resource(object):
    def on_get(self, req, resp):
        resp.status = falcon.HTTP_200
        resp.content_type = 'gzip'

        very_long_content = [{'a': 1, 'b': 2}, {'c': 3, 'd': 4}]
        content = gzip.compress(json.dumps(very_long_content).encode('utf-8'), 5)
        resp.body = content

# falcon.API instances are callable WSGI apps
# Add the MultipartMiddleware to your api middlewares
app = falcon.App(middleware=[
    MultipartMiddleware(),
    falcon_jsonify.Middleware(help_messages=True),
                             ],
                 independent_middleware=True)


# Resources are represented by long-lived class instances
hello = HelloResource()

# things will handle all requests to the '/things' URL path
app.add_route('/hello', hello)
app.add_route('/test/html_response', HTML_test_resource())
app.add_route('/test/xml_response', XML_test_resource())
app.add_route('/test/json_response', Json_test_resource())
app.add_route('/test/gzip_response', gzip_test_resource())


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
        request_body_size = int(environ.get('CONTENT_LENGTH', 0))
    except (ValueError):
        request_body_size = 0

    request_body = environ['wsgi.input'].read(request_body_size)

    try:
        metadata = {
            'request_body': request_body,
            'response-body': environ['moesif-response-body'],
            'Content-Type': environ['moesif_response_headers']['content-type'],
            'Content-Length': environ['moesif_response_headers']['content-length'],
            'X-Moesif-Transaction-Id': environ['moesif_response_headers']['X-Moesif-Transaction-Id']
        }
    except KeyError:
        print('environ has no field [moesif_response_body] or [moesif_response_headers]')
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

