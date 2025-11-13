# Configuración de Gunicorn para Home Control Backend
# Para Raspberry Pi con Django

import multiprocessing
import os

# Configuración básica
bind = "0.0.0.0:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100

# Timeouts
timeout = 30
keepalive = 2

# Logging
accesslog = "/home/manu/personalcode/home_control_adv/logs/gunicorn-access.log"
errorlog = "/home/manu/personalcode/home_control_adv/logs/gunicorn-error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Process naming
proc_name = "home_control_backend"

# Daemon configuration
user = "manu"
group = "manu"
tmp_upload_dir = None

# Restart workers periodically
max_requests = 1000
preload_app = True

# Security
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190