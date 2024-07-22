# __init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os

db = SQLAlchemy()
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')

    db.init_app(app)
    migrate.init_app(app, db)

    from .models import ClinicalInstructor, Student, Assignment  # Import your models here

    from .routes import bp as main_bp  # Import and register the blueprint
    app.register_blueprint(main_bp)

    return app
