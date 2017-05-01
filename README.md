# Moesif Middleware for Python WSGI based Frameworks

[WSGI (Web Server Gateway Interface)](https://wsgi.readthedocs.io/en/latest/)
is a standard (PEP 3333) that describes
how a web server communicates with web applications. Many Python Frameworks
are build on top of WSGI, such as [Flask](http://flask.pocoo.org/),
[Bottle](https://bottlepy.org/docs/dev/), [Pyramid](https://trypyramid.com/) etc.
Moesif WSGI Middleware help APIs that are build on top of these Frameworks to
easily integrate with [Moesif](https://www.moesif.com).

## How to install

```shell
pip install moesifwsgi
```

## How to use

In __Flask__, add middleware is simply wrap your wsgi_app with the Moesif middleware.

```python
from moesifwsgi import MoesifMiddleware

moesif_settings = {
    'APPLICATION_ID': 'Your application id'
}

app.wsgi_app = MoesifMiddleware(app.wsgi_app, moesif_settings)

```

You can find your Application Id from [_Moesif Dashboard_](https://www.moesif.com/) -> _Top Right Menu_ -> _App Setup_

In __Bottle__, adding middelware is very similiar.

```python

from moesifwsgi import MoesifMiddleware

app = bottle.Bottle()

moesif_settings = {
    'APPLICATION_ID': 'Your application id',
    'DEBUG': True
}

bottle.run(app=MoesifMiddleware(app, moesif_settings))

```

If you are using a Framework that is build on top of WSGI, it should just work.
Please read the documentation for that framework on how to add middlewares to
your app.


## Setting options

#### __`APPLICATION_ID`__
(__required__), _string_, is obtained via your Moesif Account, this is required.

#### __`SKIP`__
(optional) _(app, environ) => boolean_, a function that takes a wsgi app and an environ, and returns true if you want to skip this particular event.

#### __`IDENTIFY_USER`__
(optional) _(request, response) => string_, a function that takes an app and an environ, and returns a string that is the user id used by your system. While Moesif identify users automatically, and this middleware try to use the standard Django request.user.username, if your set up is very different from the standard implementations, it would be helpful to provide this function.

#### __`GET_SESSION_TOKEN`__
(optional) _(request, response) => string_, a function that takes an app and an environ, and returns a string that is the session token for this event. Again, Moesif tries to get the session token automatically, but if you setup is very different from standard, this function will be very help for tying events together, and help you replay the events.

#### __`MASK_EVENT_MODEL`__
(optional) _(EventModel) => EventModel_, a function that takes an EventModel and returns an EventModel with desired data removed. Use this if you prefer to write your own mask function than use the string based filter options: REQUEST_BODY_MASKS, REQUEST_HEADER_MASKS, RESPONSE_BODY_MASKS, & RESPONSE_HEADER_MASKS. The return value must be a valid EventModel required by Moesif data ingestion API. For details regarding EventModel please see the [Moesif Python API Documentation](https://www.moesif.com/docs/api?python).


### Example:

```python
def identifyUser(app, environ):
    # if your setup do not use the standard request.user.username
    # return the user id here
    return "user_id_1"

def should_skip(app, environ):
    if "healthprobe" in req.path:
        return True
    else:
        return False

def get_token(app, environ):
    # if your setup do not use the standard Django method for
    # setting session tokens. do it here.
    return "token"

def mask_event(eventmodel):
    # do something to remove sensitive fields
    # be sure not to remove any required fields.
    return eventmodel

moesif_settings = {
    'APPLICATION_ID': 'Your application id',
    'DEBUG': False,
    'IDENTIFY_USER': identifyUser,
    'GET_SESSION_TOKEN': get_token,
    'SKIP': should_skip,
    'MASK_EVENT_MODEL': mask_event,
}

app.wsgi_app = MoesifMiddleware(app.wsgi_app, moesif_settings)

```

## Other integrations

To view more more documentation on integration options, please visit __[the Integration Options Documentation](https://www.moesif.com/docs/getting-started/integration-options/).__
