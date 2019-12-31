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
    return {
        'datacenter': 'westus',
        'deployment_version': 'v1.2.3',
    }

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


if __name__ == '__main__':
    bottle.run(app=app.wsgi_app,
        host='localhost',
        debug=True,
        port=6080)
