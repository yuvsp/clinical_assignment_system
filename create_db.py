# create_db.py
from app import create_app, db
from app.models import Field, ClinicalInstructor, Student, Assignment

app = create_app()

with app.app_context():
    db.drop_all()  # Drop all tables
    db.create_all()  # Create all tables
