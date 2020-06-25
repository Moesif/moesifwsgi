# Moesifwsgi Example

[WSGI](https://wsgi.readthedocs.io/en/latest/) is a specification that describes
how a web server communicates with web applications. It is a Python standard
described in PEP 3333. Many python web app frameworks (Bottle, Flask, Pyramid, etc)
are built on top of WSGI.

[Moesif](https://www.moesif.com) is an API analyatics platform. [moesifwsgi](https://github.com/Moesif/moesifwsgi)
is a middleware that makes integration with Moesif easy for wsgi based apps and frameworks.

This section have examples for Bottle and Flask two of more popular frameworks
that are based on WSGI.

## Flask Example

The example is under `/examples/flask`

moesifwsgi's [github readme](https://github.com/Moesif/moesifwsgi) already documented
the steps for setup Moesif. But this is instructions to run this example.

1. Optional: Setup [virtual env](https://virtualenv.pypa.io/en/stable/) if needed.
Start the virtual env by `virtualenv benv` & `source benv/bin/activate`

2. Inside `examples/flask/`, Install dependencies in the environment by `pip install -r requirements.txt`

3. Be sure to edit the `examples/flask/hello.py` to include your own application id.

```
moesif_settings = {
    'APPLICATION_ID': 'Your application id'
}
```

4. Inside, `examples/flask/` folder. Run `$ export FLASK_APP=hello.py` and then `$ flask run`

To verify: send few request to the local server such as 'http://127.0.0.1:5000/todo/api/v1.0/tasks' and
check in your moesif account that events are captured.


## Bottle Example:

The example is under `/examples/bottle`

1. Optional: Setup [virtual env](https://virtualenv.pypa.io/en/stable/).
Start the virtual env by `virtualenv benv` & `source benv/bin/activate`

2. Inside `examples/bottle/`, Install dependencies in the environment by `pip install -r requirements.txt`

3. Be sure to edit the `examples/bottle/hello.py` to include your own application id in `moesif_settings`.

4. Inside, `examples/bottle/` folder. Run `python hello.py`

To verify: send few request to the local server such as 'http://localhost:6080/hello' and
check in your moesif account that events are captured.


## Falcon Example:

The example is under `examples/falcon`

1. Optional: Setup [virtual env](https://virtualenv.pypa.io/en/stable/).
Start the virtual env by `virtualenv benv` & `source benv/bin/activate`

2. Inside `examples/falcon/`, Install dependencies in the environment by `pip install -r requirements.txt`

3. Be sure to edit the `examples/falcon/hello.py` to include your own application id.

```python
app = MoesifMiddleware(app, {
    'APPLICATION_ID': 'Your Moesif Application Id',
})
```

4. Inside, `examples/falcon/` folder. Start the server `gunicorn hello:app`

To verify: send few request to the local server such as 'http://localhost:8000/hello' and
check in your moesif account that events are captured.
