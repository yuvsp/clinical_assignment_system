# create_db.py
import os
import logging
from app import create_app, db
from app.models import Field, ClinicalInstructor, Student, Assignment

# Setup logging
logging.basicConfig(level=logging.DEBUG)

# Get the database path from environment variable or default
db_path = os.getenv('DATABASE_URL', 'sqlite:////data/clinical_assignment.db')
if db_path.startswith('sqlite:///'):
    db_path = db_path.replace('sqlite:///', '')

db_dir = os.path.dirname(db_path)

logging.debug(f"Database path: {db_path}")
logging.debug(f"Database directory: {db_dir}")

if not os.path.exists(db_dir):
    logging.debug("Directory does not exist. Creating now...")
    os.makedirs(db_dir)
    os.chmod(db_dir, 0o777)  # Set full permissions for the directory
    logging.debug("Directory created and permissions set.")

app = create_app()

with app.app_context():
    logging.debug("Dropping all tables...")
    db.drop_all()  # Drop all tables
    logging.debug("Creating all tables...")
    db.create_all()  # Create all tables
    logging.debug("Database setup complete.")
