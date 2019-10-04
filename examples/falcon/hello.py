import falcon
from falcon_multipart.middleware import MultipartMiddleware
from moesifwsgi import MoesifMiddleware

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


# falcon.API instances are callable WSGI apps
# Add the MultipartMiddleware to your api middlewares
app = falcon.API(middleware=[MultipartMiddleware()],
                 independent_middleware=True)

# Resources are represented by long-lived class instances
hello = HelloResource()

# things will handle all requests to the '/things' URL path
app.add_route('/hello', hello)

# Add Moesif Middleware
app = MoesifMiddleware(app, {
    'APPLICATION_ID': 'Your Moesif Application Id',
})
