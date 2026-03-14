web: flask db upgrade && gunicorn -w 1 -b 0.0.0.0:${PORT:-5000} wsgi:application
