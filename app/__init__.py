from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import xlsxwriter

db = SQLAlchemy()
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///your_database.db'  # Update with your database URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    migrate.init_app(app, db)

    from .models import ClinicalInstructor, Student, Assignment  # Import your models here

    from .routes import bp as main_bp  # Import and register the blueprint
    app.register_blueprint(main_bp)

    return app
