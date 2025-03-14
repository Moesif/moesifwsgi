import os



# specify the python code to run

wsgi_app = f"hello:app"


# how gunicorn communicates with Nginx

bind = "0.0.0.0:5050"



# permissions so we don't run as root

# (there is no "wsgi" user defined, so borrow the standard www-data user)


workers = 5

threads = 2

# worker_class = "gthread"

timeout = 120

# preload_app = True



pidfile = "gunicorn.pid"



# forward app_id headers to Flask app

# (SCRIPT_NAME,PATH_INFO are here to preserve gunicorn defaults)

forwarded_allow_ips = "*"

forwarder_headers = "APP_ID,SCRIPT_NAME,PATH_INFO"
