# Gunicorn configuration for rdgen / AcilBir-Generator
bind = "0.0.0.0:8000"

workers = 4
threads = 4
worker_class = "gthread"

timeout = 120
graceful_timeout = 30
keepalive = 5

max_requests = 1000
max_requests_jitter = 50

preload_app = False

# Path to Django WSGI application
wsgi_app = "rdgen.wsgi.application"
