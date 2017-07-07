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
the steps for setup Moesif. But this is instructions to runt this example.

1. Optional: Setup [virtual env](https://virtualenv.pypa.io/en/stable/) if needed.
Start the virtual env by `virtualenv benv` & `source benv/bin/activate`

2. Install moesifwsgi in the environment by `pip install moesifwsgi`

3. Install Rest Framework by, `pip install Flask`

4. Be sure to edit the `examples/flask/hello.py` to include your own application id.

```
moesif_settings = {
    'APPLICATION_ID': 'Your application id'
}
```

5. Inside, `examples/flask/` folder. Run `$ export FLASK_APP=hello.py` and then `$ flask run`

To verify: send few request to the local server such as 'http://127.0.0.1:5000/todo/api/v1.0/tasks' and
check in your moesif account that events are captured.


## Bottle Example:

The example is under `/examples/bottle`

1. Optional: Setup [virtual env](https://virtualenv.pypa.io/en/stable/).
Start the virtual env by `virtualenv benv` & `source benv/bin/activate`

2. Install moesifwsgi in the environment by `pip install moesifwsgi`

3. Install Rest Framework by, `pip install bottle`

4. Be sure to edit the `examples/bottle/hello.py` to include your own application id in `moesif_settings`.

5. Inside, `examples/bottle/` folder. Run `python hello.py`

To verify: send few request to the local server such as 'http://localhost:6080/hello' and
check in your moesif account that events are captured.
