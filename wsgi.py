"""WSGI entry point for gunicorn and other production servers."""
from app import create_app

application = create_app()
