from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
import os

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    
    # Set the login view for unauthorized access
    login_manager.login_view = 'main.login'
    login_manager.login_message = "Please log in to access this page."

    from .models import ClinicalInstructor, Student, Assignment, User  # Import your models here

    from .routes import bp as main_bp  # Import and register the blueprint
    app.register_blueprint(main_bp)

    return app

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))  # Function to load user by ID
