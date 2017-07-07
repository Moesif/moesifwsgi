import bottle
from bottle import route, run, post, get, request, response
from moesifwsgi import MoesifMiddleware

app = application = bottle.Bottle()

@app.route('/hello')
def hello():
    return "Hello World!"


def check_login(user, psword):
    if user == 'xing' and psword == 'blah':
        return True
    else:
        return False

@app.get('/login') # or @route('/login')
def login():
    return '''
        <form action="/login" method="post">
            Username: <input name="username" type="text" />
            Password: <input name="password" type="password" />
            <input value="Login" type="submit" />
        </form>
    '''

@app.post('/login') # or @route('/login', method='POST')
def do_login():
    username = request.forms.get('username')
    password = request.forms.get('password')
    if check_login(username, password):
        return "<p>Your login information was correct.</p>"
    else:
        return "<p>Login failed.</p>"


@app.route('/iso')
def get_iso():
    response.charset = 'ISO-8859-15'
    return u'This will be sent with ISO-8859-15 encoding.'

@app.route('/latin9')
def get_latin():
    response.content_type = 'text/html; charset=latin9'
    return u'ISO-8859-15 is also known as latin9.'


moesif_settings = {
    'APPLICATION_ID': 'your application id',
    'DEBUG': False
}


#run(host='localhost', port=6080, debug=True)
if __name__ == '__main__':
    bottle.run(app=MoesifMiddleware(app, moesif_settings),
        host='localhost',
        debug=True,
        port=6080)
