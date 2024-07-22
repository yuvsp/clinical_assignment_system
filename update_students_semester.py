from app import create_app, db
from app.models import Student

app = create_app()
with app.app_context():
    students = Student.query.all()
    for student in students:
        student.semester = 'א'
    db.session.commit()
