import os

# Gunicorn configuration optimized for Docker container memory limits
bind = "0.0.0.0:8000"
workers = 2
threads = 4
worker_class = "gthread"
timeout = 120
keepalive = 5

# Path to Django WSGI application
wsgi_app = "rdgen.wsgi.application"