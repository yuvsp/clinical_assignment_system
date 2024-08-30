import os
import platform

class Config:
    # Determine the operating system
    if platform.system() == 'Windows':
        # Windows: Use a relative path or a Windows-specific absolute path
        BASE_DIR = os.path.abspath(os.path.dirname(__file__))
        SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', f'sqlite:///{os.path.join(BASE_DIR, "clinical_assignment.db")}')
    else:
        # Linux/Unix: Use the absolute path suitable for production
        SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:////data/clinical_assignment.db')

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.urandom(24)
