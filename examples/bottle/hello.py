import gzip
import json

import bottle
from bottle import HTTPResponse, request, response
from moesifwsgi import MoesifMiddleware

app = application = bottle.Bottle()

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
            'Content-Type': environ['moesif_response_headers']['Content-Type'],
            'Content-Length': environ['moesif_response_headers']['Content-Length'],
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
    'CAPTURE_OUTGOING_REQUESTS': False,
}

app.wsgi_app = MoesifMiddleware(app, moesif_settings)

@app.route('/hello')
def hello():
    return "Hello World!"


def check_login(user, psword):
    if user == 'xing' and psword == 'blah':
        return True
    else:
        return False

@app.get('/login')
def login():
    return HTTPResponse(body='''
        <form action="/login" method="post">
            Username: <input name="username" type="text" />
            Password: <input name="password" type="password" />
            <input value="Login" type="submit" />
        </form>
    ''', status=201)

@app.post('/login')
def do_login():
    username = request.forms.get('username')
    password = request.forms.get('password')
    if check_login(username, password):
        return "<p>Your login information was correct.</p>"
    else:
        return "<p>Login failed.</p>"

@app.post('/users/<id>')
def update_users(id):
    app.wsgi_app.update_user({
        'user_id': id,
        'company_id': '67890',  # If set, associate user with a company object
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
            }
        }
    })
    return HTTPResponse(status=201, body={'user_id': id, 'update_users': 'success'})

@app.post('/companies/<id>')
def update_companies(id):
    app.wsgi_app.update_company({
            'company_id': id,
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
                }
            }
        })
    return HTTPResponse(status=201, body={'company_id': id, 'update_companies': 'success'})

@app.route('/iso')
def get_iso():
    response.charset = 'ISO-8859-15'
    return u'This will be sent with ISO-8859-15 encoding.'

@app.route('/latin9')
def get_latin():
    response.content_type = 'text/html; charset=latin9'
    return u'ISO-8859-15 is also known as latin9.'

response = [
    {
        'id': 1,
        'title': u'Buy groceries',
        'description': u'Milk, Cheese, Pizza, Fruit, Tylenol',
        'done': False
    },
    {
        'id': 2,
        'title': u'Learn Python',
        'description': u'Need to find a good Python tutorial on the web',
        'done': False
    }
]

@app.route('/test/html_response', methods=['GET'])
def html_response():
    html_text = """
        <!DOCTYPE html>
        <html>
        <body>
    
        <h1>My First Heading</h1>
    
        <p>My first paragraph.</p>
    
        </body>
        </html>
        """

    headers = {'Content-Type': 'application/html'}

    return HTTPResponse(body=html_text, **headers)

@app.route('/test/xml_response', methods=['GET'])
def xml_response():
    xml_text = """
        <note>
        <to>Tove</to>
        <from>Jani</from>
        <heading>Reminder</heading>
        <body>Don't forget me this weekend!</body>
        </note>
        """

    headers = {'Content-Type': 'xml/application'}
    return HTTPResponse(body=xml_text, **headers)

@app.route('/test/json_response', methods=['GET'])
def json_response():
    return HTTPResponse(status=201, body={'company_id': "9273892", 'update_companies': 'success'})

@app.route('/test/gzip_response', methods=['POST'])
def gzip_response():
    very_long_content = [{'a': 1, 'b': 2}, {'c': 3, 'd': 4}]
    content = gzip.compress(json.dumps(very_long_content).encode('utf-8'), 5)
    headers = {'Content-Type': 'gzip',
               'Content-Encoding': 'gzip'}

    return HTTPResponse(status=201, body=content, **headers)

if __name__ == '__main__':
    bottle.run(app=app.wsgi_app,
        host='localhost',
        debug=True,
        port=6080)
