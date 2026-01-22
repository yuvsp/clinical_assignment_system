
from app import create_app, db
import os
print("DATABASE_URL =", os.getenv("DATABASE_URL"))

app = create_app()

with app.app_context():
    db.create_all()
    print("✅ Tables created")
