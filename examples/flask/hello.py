from moesifwsgi import MoesifMiddleware
from flask import Flask, jsonify, abort, make_response, request, Response
import gzip
import json

app = Flask(__name__)

def identify_user(app, environ, response_headers=dict()):
    return '12345'

def identify_company(app, environ, response_headers=dict()):
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
    'APPLICATION_ID': 'eyJhcHAiOiI3MTA6NzEyIiwidmVyIjoiMi4wIiwib3JnIjoiMjYyOjU0OSIsImlhdCI6MTY1NjYzMzYwMH0.CiU4oW_PuDXhLM8_scQktI_wrqZcu3GAFxUMb0DyQCc',
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
app.wsgi_app = MoesifMiddleware(app.wsgi_app, moesif_settings)

@app.route('/')
def index():
    return 'Index Page'

@app.route('/hello')
def hello():
    return 'Hello, world'

@app.route('/user/<username>')
def show_user_profile(username):
    # show the user profile for that user
    return 'User %s' % username

@app.route('/post/<int:post_id>')
def show_post(post_id):
    # show the post with the given id, the id is an integer
    return 'Post %d' % post_id

tasks = [
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

@app.route('/todo/api/v1.0/tasks', methods=['GET'])
def get_tasks():
    json_body = json.dumps({'tasks': tasks})
    return Response(response=json_body, status=201, mimetype='application/json')


@app.route('/todo/api/v1.0/tasks/<int:task_id>', methods=['GET'])
def get_task(task_id):
    task = [task for task in tasks if task['id'] == task_id]
    if len(task) == 0:
        abort(404)
    json_body = json.dumps({'task': task[0]})
    return Response(response=json_body, status=201, mimetype='application/json')


@app.route('/todo/api/v1.0/tasks', methods=['POST'])
def create_task():
    if not request.json or 'title' not in request.json:
        abort(400)
    task = {
        'id': tasks[-1]['id'] + 1,
        'title': request.json['title'],
        'description': request.json.get('description', ""),
        'done': False
    }
    tasks.append(task)
    json_body = json.dumps({'task': task})
    return Response(response=json_body, status=201, mimetype='application/json')


@app.route('/users/<id>', methods=['POST'])
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
    json_body = json.dumps({'user_id': id, 'update_users': 'success'})
    return Response(response=json_body, status=201, mimetype='application/json')


@app.route('/companies/<id>', methods=['POST'])
def update_companies(id):
    app.wsgi_app.update_company({
        'company_id': id,
        'company_domain': 'acmeinc.com',
        # If domain is set, Moesif will enrich your profiles with publicly available info
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
    json_body = json.dumps({'company_id': id, 'update_companies': 'success'})
    return Response(response=json_body, status=201, mimetype='application/json')


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
    html_body = """
        <!DOCTYPE html>
        <html>
        <body>

        <h1>My First Heading</h1>

        <p>My first paragraph.</p>

        </body>
        </html>
        """
    return Response(response=html_body, status=200, mimetype='text/html')


@app.route('/test/xml_response', methods=['GET'])
def xml_response():
    xml_body = """
        <note>
        <to>Tove</to>
        <from>Jani</from>
        <heading>Reminder</heading>
        <body>Don't forget me this weekend!</body>
        </note>
        """
    return Response(response=xml_body, status=200, mimetype='application/xml')


@app.route('/test/json_response', methods=['GET'])
def json_response():
    json_body = json.dumps({'response': response})
    return Response(response=json_body, status=201, mimetype='application/json')


# Handle posted data
@app.route('/test/gzip_response', methods=['POST'])
def post_gzip():
    content = [{'a': 1, 'b': 2}, {'c': 3, 'd': 4}]
    content = gzip.compress(json.dumps(content).encode('utf-8'), 5)
    response = make_response(content, 201)
    response.headers['Content-Length'] = len(content)
    response.headers['Content-Encoding'] = 'gzip'
    return response


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)

if __name__ == '__main__':
    app.run(debug=True)
