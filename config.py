# config.py
import os

class Config:
    # Use the absolute path for the database file in the Render.com environment
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:////data/clinical_assignment.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.urandom(24)
