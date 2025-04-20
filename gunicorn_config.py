# PythonAnywhere doesn't use gunicorn by default, but we'll keep this file
# in case you want to use it with a custom setup
bind = "0.0.0.0:10000"
workers = 2  # Reduced for PythonAnywhere's resource limits
threads = 2
timeout = 120