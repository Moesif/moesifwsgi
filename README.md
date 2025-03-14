# Moesif Middleware for Python WSGI-based Frameworks
by [Moesif](https://moesif.com), the [API analytics](https://www.moesif.com/features/api-analytics) and [API monetization](https://www.moesif.com/solutions/metered-api-billing) platform.

[![Built For][ico-built-for]][link-built-for]
[![Latest Version][ico-version]][link-package]
[![Language Versions][ico-language]][link-language]
[![Software License][ico-license]][link-license]
[![Source Code][ico-source]][link-source]

With Moesif middleware for Python WSGI-based frameworks, you can automatically log API calls
and send them to [Moesif](https://www.moesif.com) for API analytics and monitoring.

> If you're new to Moesif, see [our Getting Started](https://www.moesif.com/docs/) resources to quickly get up and running.

## Overview
This middleware allows you to integrate Moesif's API analytics and
API monetization features with minimal configuration into APIs that are built on Python WSGI-based (Web Server Gateway Interface) frameworks.

[WSGI (Web Server Gateway Interface)](https://wsgi.readthedocs.io/en/latest/)
is a standard (PEP 3333) that describes
how a web server communicates with web applications. Many Python Frameworks
are build on top of WSGI, such as [Flask](http://flask.pocoo.org/),
[Bottle](https://bottlepy.org/docs/dev/), and [Pyramid](https://trypyramid.com/).

## Prerequisites
Before using this middleware, make sure you have the following:

- [An active Moesif account](https://moesif.com/wrap)
- [A Moesif Application ID](#get-your-moesif-application-id)

### Get Your Moesif Application ID
After you log into [Moesif Portal](https://www.moesif.com/wrap), you can get your Moesif Application ID during the onboarding steps. You can always access the Application ID any time by following these steps from Moesif Portal after logging in:

1. Select the account icon to bring up the settings menu.
2. Select **Installation** or **API Keys**.
3. Copy your Moesif Application ID from the **Collector Application ID** field.

<img class="lazyload blur-up" src="images/app_id.png" width="700" alt="Accessing the settings menu in Moesif Portal">

## Install the Middleware
Install with `pip` using the following command:

```shell
pip install moesifwsgi
```

## Configure the Middleware
See the available [configuration options](#configuration-options) to learn how to configure the middleware for your use case.

## How to Use

### Flask

Wrap your `wsgi_app` with the Moesif middleware.

```python
from moesifwsgi import MoesifMiddleware

moesif_settings = {
    'APPLICATION_ID': 'YOUR_MOESIF_APPLICATION_ID',
    'LOG_BODY': True,
    # ... For other options see below.
}

app.wsgi_app = MoesifMiddleware(app.wsgi_app, moesif_settings)
```

Replace *`YOUR_MOESIF_APPLICATION_ID`* with your [Moesif Application ID](#get-your-moesif-application-id).


For an example with Flask, see the `/examples/flask` folder of this repository.

### Bottle
Wrap your Bottle application with the Moesif middleware:

```python

from moesifwsgi import MoesifMiddleware

app = bottle.Bottle()

moesif_settings = {
    'APPLICATION_ID': 'YOUR_MOESIF_APPLICATION_ID',
    'LOG_BODY': True,
    # ... For other options see below.
}

bottle.run(app=MoesifMiddleware(app, moesif_settings))
```

Replace *`YOUR_MOESIF_APPLICATION_ID`* with your [Moesif Application ID](#get-your-moesif-application-id).

For an example with Bottle, see the `/examples/bottle` folder of this repository.

### Pyramid


```python
from pyramid.config import Configurator
from moesifwsgi import MoesifMiddleware

if __name__ == '__main__':
    config = Configurator()
    config.add_route('hello', '/')
    config.scan()
    app = config.make_wsgi_app()

    # configure your moesif settings
    moesif_settings = {
        'APPLICATION_ID': 'YOUR_MOESIF_APPLICATION_ID',
        'LOG_BODY': True,
        # ... For other options see below.
    }
    # Put middleware
    app = MoesifMiddleware(app, moesif_settings)

    server = make_server('0.0.0.0', 8080, app)
    server.serve_forever()

```

Replace *`YOUR_MOESIF_APPLICATION_ID`* with your [Moesif Application ID](#get-your-moesif-application-id).

### Other WSGI Frameworks

If you are using a framework that is built on top of WSGI, it should work just by adding the Moesif middleware.
Please read the documentation for your specific framework on how to add middlewares.

### Optional: Capturing Outgoing API Calls
In addition to your own APIs, you can also start capturing calls out to third party services through by setting the `CAPTURE_OUTGOING_REQUESTS` option:

```python
from moesifwsgi import MoesifMiddleware
from flask import Flask

moesif_settings = {
    'APPLICATION_ID': 'YOUR_MOESIF_APPLICATION_ID',
    'LOG_BODY': True,
    'CAPTURE_OUTGOING_REQUESTS': False
}

app = Flask(__name__)

app.wsgi_app = MoesifMiddleware(app.wsgi_app, moesif_settings)
```

For configuration options specific to capturing outgoing API calls, see [Options For Outgoing API Calls](#options-for-outgoing-api-calls).

## Troubleshoot
For a general troubleshooting guide that can help you solve common problems, see [Server Troubleshooting Guide](https://www.moesif.com/docs/troubleshooting/server-troubleshooting-guide/).

Other troubleshooting supports:

- [FAQ](https://www.moesif.com/docs/faq/)
- [Moesif support email](mailto:support@moesif.com)

### Thread Pool Issues

This library manages a thread pool to send data to Moesif in the background without impacting your app's latency.

However, the `preload` feature of Gunicorn (or `preload-app` for Hypercorn) may interfere with the thread pool before the worker is forked. If you encounter issues, avoid setting `preload` to `True`.

### Solve Timezone Issue with Docker
When using Docker with Ubuntu-based image, events may not be captured if the image fails to find any timezone configuration. To solve this issue, add the following line to your Dockerfile:

```
ENV TZ=UTC
```

Otherwise, you can add `RUN apt-get install tzdata` in the Dockerfile.

## Repository Structure

```
.
├── BUILDING.md
├── examples/
├── images/
├── LICENSE
├── MANIFEST.in
├── moesifwsgi/
├── README.md
├── requirements.txt
├── setup.cfg
└── setup.py
```

## Configuration options
The following sections describe the available configuration options for this middleware. You can set these options in a Python dictionary and then pass that as a parameter when you create the middleware instance. See the `examples/` folder for better understanding.

Notice the following about the configuration options:

- The `app` is the original WSGI app instance.
- The `environ` is a [WSGI `environ`](http://wsgi.readthedocs.io/en/latest/definitions.html).

Moesif also adds the following keys to `environ`:

- __`environ['moesif.request_body']`__: a JSON object or base64 encoded string if couldn't parse the request body as JSON

- __`environ["moesif.response_body_chunks"]`__: a response body chunks

- __`environ["moesif.response_headers"]`__: a dictionary representing the response headers

### `APPLICATION_ID`
<table>
  <tr>
   <th scope="col">
    Data type
   </th>
  </tr>
  <tr>
   <td>
    String
   </td>
  </tr>
</table>

A string that [identifies your application in Moesif](#get-your-moesif-application-id).

### `SKIP`
<table>
  <tr>
   <th scope="col">
    Data type
   </th>
   <th scope="col">
    Parameters
   </th>
   <th scope="col">
    Return type
   </th>
  </tr>
  <tr>
   <td>
    Function
   </td>
   <td>
    <code>(app, environ)</code>
   </td>
   <td>
    Boolean
   </td>
  </tr>
</table>

Optional.

A function that takes a WSGI application and an `environ` object,
and returns `True` if you want to skip this particular event.

### `IDENTIFY_USER`
<table>
  <tr>
   <th scope="col">
    Data type
   </th>
   <th scope="col">
    Parameters
   </th>
   <th scope="col">
    Return type
   </th>
  </tr>
  <tr>
   <td>
    Function
   </td>
   <td>
    <code>(app, environ, response_headers)</code>
   </td>
   <td>
    String
   </td>
  </tr>
</table>

Optional, but highly recommended.

A function with the following arguments:

- A WSGI application
- An `environ` object
- An optional parameter for response headers

Returns returns a string that represents the user ID used by your system.

Moesif identifies users automatically. However, due to the differences arising from different frameworks and implementations, provide this function to ensure user identification properly.

### `IDENTIFY_COMPANY`
<table>
  <tr>
   <th scope="col">
    Data type
   </th>
   <th scope="col">
    Parameters
   </th>
   <th scope="col">
    Return type
   </th>
  </tr>
  <tr>
   <td>
    Function
   </td>
   <td>
    <code>(app, environ, response_headers)</code>
   </td>
   <td>
    String
   </td>
  </tr>
</table>

Optional.

A function with the following arguments:

- A WSGI application
- An `environ` object
- An optional parameter for response headers

Returns a string that represents the company ID for this event.

### `GET_METADATA`
<table>
  <tr>
   <th scope="col">
    Data type
   </th>
   <th scope="col">
    Parameters
   </th>
   <th scope="col">
    Return type
   </th>
  </tr>
  <tr>
   <td>
    Function
   </td>
   <td>
    <code>(app, environ)</code>
   </td>
   <td>
    Dictionary
   </td>
  </tr>
</table>

Optional.

A function that takes a WSGI application and an `environ` object, and
returns a dictionary.

This function allows you
to add custom metadata that Moesif can associate with the event. The metadata must be a simple Python dictionary that can be converted to JSON.

For example, you may want to save a virtual machine instance ID, a trace ID, or a resource ID with the request.

### `GET_SESSION_TOKEN`
<table>
  <tr>
   <th scope="col">
    Data type
   </th>
   <th scope="col">
    Parameters
   </th>
   <th scope="col">
    Return type
   </th>
  </tr>
  <tr>
   <td>
    Function
   </td>
   <td>
    <code>(app, environ)</code>
   </td>
   <td>
    String
   </td>
  </tr>
</table>


Optional.

A function that takes a WSGI application and an `environ`, and returns a string that represents the session token for this event.

Similar to users and companies, Moesif tries to retrieve session tokens automatically. But if it doesn't work for your service, provide this function to help identify sessions.

### `MASK_EVENT_MODEL`
<table>
  <tr>
   <th scope="col">
    Data type
   </th>
   <th scope="col">
    Parameters
   </th>
   <th scope="col">
    Return type
   </th>
  </tr>
  <tr>
   <td>
    Function
   </td>
   <td>
    <code>(EventModel)</code>
   </td>
   <td>
    <code>EventModel</code>
   </td>
  </tr>
</table>

Optional.

A function that takes the final Moesif event model and returns an event model with desired data removed.

The return value must be a valid eventt model required by Moesif data ingestion API. For more information about the `EventModel` object, see the [Moesif Python API documentation](https://www.moesif.com/docs/api?python).

### `DEBUG`
<table>
  <tr>
   <th scope="col">
    Data type
   </th>
  </tr>
  <tr>
   <td>
    Boolean
   </td>
  </tr>
</table>

Optional.

Set to `True` to print debug logs if you're having integration issues.

### `LOG_BODY`
<table>
  <tr>
   <th scope="col">
    Data type
   </th>
   <th scope="col">
    Default
   </th>
  </tr>
  <tr>
   <td>
    Boolean
   </td>
   <td>
    <code>True</code>
   </td>
  </tr>
</table>

Optional.

Whether to log request and response body to Moesif.

### `EVENT_QUEUE_SIZE`
<table>
  <tr>
   <th scope="col">
    Data type
   </th>
   <th scope="col">
    Default
   </th>
  </tr>
  <tr>
   <td>
    <code>int</code>
   </td>
   <td>
    <code>1000_000</code>
   </td>
  </tr>
</table>

Optional.

The maximum number of event objects queued in memory pending upload to Moesif. For a full queue, additional calls to `MoesifMiddleware` returns immediately without logging the event. Therefore, set this option based on the event size and memory capacity you expect.

### `EVENT_WORKER_COUNT`
<table>
  <tr>
   <th scope="col">
    Data type
   </th>
   <th scope="col">
    Default
   </th>
  </tr>
  <tr>
   <td>
    <code>int</code>
   </td>
   <td>
    <code>2</code>
   </td>
  </tr>
</table>

Optional.

The number of worker threads to use for uploading events to Moesif.

If you have a large number of events being logged, increasing this number can improve upload performance.

### `BATCH_SIZE`
<table>
  <tr>
   <th scope="col">
    Data type
   </th>
   <th scope="col">
    Default
   </th>
  </tr>
  <tr>
   <td>
    <code>int</code>
   </td>
   <td>
    <code>100</code>
   </td>
  </tr>
</table>

An optional field name that specifies the maximum batch size when sending to Moesif.

### `EVENT_BATCH_TIMEOUT`
<table>
  <tr>
   <th scope="col">
    Data type
   </th>
   <th scope="col">
    Default
   </th>
  </tr>
  <tr>
   <td>
    <code>int</code>
   </td>
   <td>
    <code>1</code>
   </td>
  </tr>
</table>

Optional.

Maximum time in seconds to wait before sending a batch of events to Moesif when reading from the queue.

### `AUTHORIZATION_HEADER_NAME`
<table>
  <tr>
   <th scope="col">
    Data type
   </th>
   <th scope="col">
    Default
   </th>
  </tr>
  <tr>
   <td>
    String
   </td>
   <td>
    <code>authorization</code>
   </td>
  </tr>
</table>

Optional.

A request header field name used to identify the User in Moesif. It also supports a comma separated string. Moesif checks headers in order like `"X-Api-Key,Authorization"`.

### `AUTHORIZATION_USER_ID_FIELD`
<table>
  <tr>
   <th scope="col">
    Data type
   </th>
   <th scope="col">
    Default
   </th>
  </tr>
  <tr>
   <td>
    String
   </td>
   <td>
    <code>sub</code>
   </td>
  </tr>
</table>

Optional.

A field name used to parse the user from authorization header in Moesif.

### `BASE_URI`
<table>
  <tr>
   <th scope="col">
    Data type
   </th>
  </tr>
  <tr>
   <td>
    String
   </td>
  </tr>
</table>

Optional.

A local proxy hostname when sending traffic through secure proxy. Remember to set this field when using secure proxy. For more information, see [Secure Proxy documentation.](https://www.moesif.com/docs/platform/secure-proxy/#2-configure-moesif-sdk).

### Options For Outgoing API Calls

The following options apply to outgoing API calls. These are calls you initiate using the Python [Requests](http://docs.python-requests.org/en/master/) library to third parties like Stripe or to your own services.

Several options use request and response as input arguments. These correspond to the [Requests](http://docs.python-requests.org/en/master/api/) library's request or response objects.

If you are not using WSGI, you can import [`moesifpythonrequest`](https://github.com/Moesif/moesifpythonrequest) directly.

#### `CAPTURE_OUTGOING_REQUESTS`
<table>
  <tr>
   <th scope="col">
    Data type
   </th>
   <th scope="col">
    Default
   </th>
  </tr>
  <tr>
   <td>
    Boolean
   </td>
   <td>
    <code>False</code>
   </td>
  </tr>
</table>

Set to `True` to capture all outgoing API calls.

#### `GET_METADATA_OUTGOING`
<table>
  <tr>
   <th scope="col">
    Data type
   </th>
   <th scope="col">
    Parameters
   </th>
   <th scope="col">
    Return type
   </th>
  </tr>
  <tr>
   <td>
    Function
   </td>
   <td>
    <code>(req, res)</code>
   </td>
   <td>
    Dictionary
   </td>
  </tr>
</table>

Optional.

A function that enables you to return custom metadata associated with the logged API calls.

Takes in the [Requests](http://docs.python-requests.org/en/master/api/) request and response objects as arguments.

We recommend that you implement a function that
returns a dictionary containing your custom metadata. The dictionary must be a valid one that can be encoded into JSON. For example, you may want to save a virtual machine instance ID, a trace ID, or a resource ID with the request.

#### `SKIP_OUTGOING`
<table>
  <tr>
   <th scope="col">
    Data type
   </th>
   <th scope="col">
    Parameters
   </th>
   <th scope="col">
    Return type
   </th>
  </tr>
  <tr>
   <td>
    Function
   </td>
   <td>
    <code>(req, res)</code>
   </td>
   <td>
    Boolean
   </td>
  </tr>
</table>

Optional.

A function that takes a [Requests](http://docs.python-requests.org/en/master/api/) request and response objects,
and returns `True` if you want to skip this particular event.

#### `IDENTIFY_USER_OUTGOING`
<table>
  <tr>
   <th scope="col">
    Data type
   </th>
   <th scope="col">
    Parameters
   </th>
   <th scope="col">
    Return type
   </th>
  </tr>
  <tr>
   <td>
    Function
   </td>
   <td>
    <code>(req, res)</code>
   </td>
   <td>
    String
   </td>
  </tr>
</table>

Optional, but highly recommended.

A function that takes [Requests](http://docs.python-requests.org/en/master/api/) request and response objects, and returns a string that represents the user ID used by your system.

While Moesif tries to identify users automatically, different frameworks and your implementation might vary. So we highly recommend that you accurately provide a
user ID using this function.

#### `IDENTIFY_COMPANY_OUTGOING`
<table>
  <tr>
   <th scope="col">
    Data type
   </th>
   <th scope="col">
    Parameters
   </th>
   <th scope="col">
    Return type
   </th>
  </tr>
  <tr>
   <td>
    Function
   </td>
   <td>
    <code>(req, res)</code>
   </td>
   <td>
    String
   </td>
  </tr>
</table>

Optional.

A function that takes [Requests](http://docs.python-requests.org/en/master/api/) request and response objects, and returns a string that represents the company ID for this event.

#### `GET_SESSION_TOKEN_OUTGOING`
<table>
  <tr>
   <th scope="col">
    Data type
   </th>
   <th scope="col">
    Parameters
   </th>
   <th scope="col">
    Return type
   </th>
  </tr>
  <tr>
   <td>
    Function
   </td>
   <td>
    <code>(req, res)</code>
   </td>
   <td>
    String
   </td>
  </tr>
</table>

Optional.

A function that takes [Requests](http://docs.python-requests.org/en/master/api/) request and response objects, and returns a string that corresponds to the session token for this event.

Similar to [user IDs](#identify_user_outgoing), Moesif tries to get the session token automatically. However, if you setup differs from the standard, this function can help tying up events together and help you replay the events.

#### `LOG_BODY_OUTGOING`
<table>
  <tr>
   <th scope="col">
    Data type
   </th>
   <th scope="col">
    Default
   </th>
  </tr>
  <tr>
   <td>
    Boolean
   </td>
   <td>
    <code>True</code>
   </td>
  </tr>
</table>

Optional.

Set to `False` to remove logging request and response body.

## Examples
See the `examples/` directory for example applications using Flask, Falcon, and Bottle frameworks.

Here's a Flask example:

```python
def identify_user(app, environ, response_headers=dict()):
    # Your custom code that returns a user id string
    return "12345"

def identify_company(app, environ, response_headers=dict()):
    # Your custom code that returns a company id string
    return "67890"

def should_skip(app, environ):
    # Your custom code that returns true to skip logging
    return "health/probe" in environ.get('PATH_INFO', '')

def get_token(app, environ):
    # If you don't want to use the standard WSGI session token,
    # add your custom code that returns a string for session/API token
    return "XXXXXXXXXXXXXX"

def mask_event(eventmodel):
    # Your custom code to change or remove any sensitive fields
    if 'password' in eventmodel.response.body:
        eventmodel.response.body['password'] = None
    return eventmodel

def get_metadata(app, environ):
    return {
        'datacenter': 'westus',
        'deployment_version': 'v1.2.3',
    }

moesif_settings = {
    'APPLICATION_ID': 'YOUR_MOESIF_APPLICATION_ID',
    'DEBUG': False,
    'LOG_BODY': True,
    'IDENTIFY_USER': identify_user,
    'IDENTIFY_COMPANY': identify_company,
    'GET_SESSION_TOKEN': get_token,
    'SKIP': should_skip,
    'MASK_EVENT_MODEL': mask_event,
    'GET_METADATA': get_metadata,
    'CAPTURE_OUTGOING_REQUESTS': False
}

app.wsgi_app = MoesifMiddleware(app.wsgi_app, moesif_settings)

```

The following examples demonstrate how to add and update customer information.

### Update A Single User
To create or update a [user](https://www.moesif.com/docs/getting-started/users/) profile in Moesif, use the `update_user()` function.

```python
api_client = MoesifAPIClient("Your Moesif Application Id").api

# Only user_id is required.
# Campaign object is optional, but useful if you want to track ROI of acquisition channels
# See https://www.moesif.com/docs/api#users for campaign schema
# metadata can be any custom object
user = {
  'user_id': '12345',
  'company_id': '67890', # If set, associate user with a company object
  'campaign': {
    'utm_source': 'google',
    'utm_medium': 'cpc',
    'utm_campaign': 'adwords',
    'utm_term': 'api+tooling',
    'utm_content': 'landing'
  },
  'metadata': {
    'email': 'john@acmeinc.com',
    'first_name': 'John',
    'last_name': 'Doe',
    'title': 'Software Engineer',
    'sales_info': {
        'stage': 'Customer',
        'lifetime_value': 24000,
        'account_owner': 'mary@contoso.com'
    },
  }
}

update_user = api_client.update_user(user)
```

The `metadata` field can contain any customer demographic or other info you want to store. Moesif only requires the `user_id` field.

For more information, see the function documentation in [Moesif Python API Reference](https://www.moesif.com/docs/api?python#update-a-user).


### Update Users in Batch
To update a list of [users](https://www.moesif.com/docs/getting-started/users/) in one batch, use the `update_users_batch()` function.

```python
api_client = MoesifAPIClient("Your Moesif Application Id").api

userA = {
  'user_id': '12345',
  'company_id': '67890', # If set, associate user with a company object
  'metadata': {
    'email': 'john@acmeinc.com',
    'first_name': 'John',
    'last_name': 'Doe',
    'title': 'Software Engineer',
    'sales_info': {
        'stage': 'Customer',
        'lifetime_value': 24000,
        'account_owner': 'mary@contoso.com'
    },
  }
}

userB = {
  'user_id': '54321',
  'company_id': '67890', # If set, associate user with a company object
  'metadata': {
    'email': 'mary@acmeinc.com',
    'first_name': 'Mary',
    'last_name': 'Jane',
    'title': 'Software Engineer',
    'sales_info': {
        'stage': 'Customer',
        'lifetime_value': 48000,
        'account_owner': 'mary@contoso.com'
    },
  }
}
update_users = api_client.update_users_batch([userA, userB])
```

The `metadata` field can contain any customer demographic or other info you want to store. Moesif only requires the `user_id` field.

For more information, see the function documentation in [Moesif Python API Reference](https://www.moesif.com/docs/api?python#update-users-in-batch).

### Update A Single Company
To update a single [company](https://www.moesif.com/docs/getting-started/companies/), use the `update_company()` function.

```python
api_client = MoesifAPIClient("Your Moesif Application Id").api

# Only company_id is required.
# Campaign object is optional, but useful if you want to track ROI of acquisition channels
# See https://www.moesif.com/docs/api#update-a-company for campaign schema
# metadata can be any custom object
company = {
  'company_id': '67890',
  'company_domain': 'acmeinc.com', # If domain is set, Moesif will enrich your profiles with publicly available info
  'campaign': {
    'utm_source': 'google',
    'utm_medium': 'cpc',
    'utm_campaign': 'adwords',
    'utm_term': 'api+tooling',
    'utm_content': 'landing'
  },
  'metadata': {
    'org_name': 'Acme, Inc',
    'plan_name': 'Free',
    'deal_stage': 'Lead',
    'mrr': 24000,
    'demographics': {
        'alexa_ranking': 500000,
        'employee_count': 47
    },
  }
}

update_company = api_client.update_company(company)
```

The `metadata` field can contain any company demographic or other information you want to store. Moesif only requires the `company_id` field. For more information, see the function documentation in [Moesif Python API Reference](https://www.moesif.com/docs/api?python#update-a-company).

### Update Companies in Batch
To update a list of [companies](https://www.moesif.com/docs/getting-started/companies/) in one batch, use the `update_companies_batch()` function.


```python
api_client = MoesifAPIClient("Your Moesif Application Id").api

companyA = {
  'company_id': '67890',
  'company_domain': 'acmeinc.com', # If domain is set, Moesif will enrich your profiles with publicly available info
  'metadata': {
    'org_name': 'Acme, Inc',
    'plan_name': 'Free',
    'deal_stage': 'Lead',
    'mrr': 24000,
    'demographics': {
        'alexa_ranking': 500000,
        'employee_count': 47
    },
  }
}

companyB = {
  'company_id': '09876',
  'company_domain': 'contoso.com', # If domain is set, Moesif will enrich your profiles with publicly available info
  'metadata': {
    'org_name': 'Contoso, Inc',
    'plan_name': 'Free',
    'deal_stage': 'Lead',
    'mrr': 48000,
    'demographics': {
        'alexa_ranking': 500000,
        'employee_count': 53
    },
  }
}

update_companies = api_client.update_companies_batch([companyA, companyB])
```
The `metadata` field can contain any company demographic or other information you want to store. Moesif only requires the `company_id` field. For more information, see the function documentation in [Moesif Python API Reference](https://www.moesif.com/docs/api?python#update-companies-in-batch).

## How to Get Help
If you face any issues using this middleware, try the [troubleshooting guidelines](#troubleshoot). For further assistance, reach out to our [support team](mailto:support@moesif.com).

## Explore Other Integrations

Explore other integration options from Moesif:

- [Server integration options documentation](https://www.moesif.com/docs/server-integration//)
- [Client integration options documentation](https://www.moesif.com/docs/client-integration/)

[ico-built-for]: https://img.shields.io/badge/built%20for-python%20wsgi-blue.svg
[ico-version]: https://img.shields.io/pypi/v/moesifwsgi.svg
[ico-language]: https://img.shields.io/pypi/pyversions/moesifwsgi.svg
[ico-license]: https://img.shields.io/badge/License-Apache%202.0-green.svg
[ico-source]: https://img.shields.io/github/last-commit/moesif/moesifwsgi.svg?style=social

[link-built-for]: https://en.wikipedia.org/wiki/Web_Server_Gateway_Interface
[link-package]: https://pypi.python.org/pypi/moesifwsgi
[link-language]: https://pypi.python.org/pypi/moesifwsgi
[link-license]: https://raw.githubusercontent.com/Moesif/moesifwsgi/master/LICENSE
[link-source]: https://github.com/Moesif/moesifwsgi
