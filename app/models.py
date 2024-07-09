from app import db

class ClinicalInstructor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    practice_location = db.Column(db.String(128), nullable=False)
    area_of_expertise = db.Column(db.String(128), nullable=False)
    city = db.Column(db.String(128), nullable=False)
    address = db.Column(db.String(128), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(128), nullable=False)
    relevant_semesters = db.Column(db.String(128), nullable=False)
    years_of_experience = db.Column(db.Integer, nullable=False)
    available_days_to_assign = db.Column(db.String(128), nullable=False)
    max_students_per_day = db.Column(db.Integer, nullable=False, default=1)  # New field
    assignments = db.relationship('Assignment', backref='instructor', lazy=True)

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    preferred_fields = db.Column(db.String(128), nullable=False)
    preferred_practice_area = db.Column(db.String(128), nullable=False)
    assignments = db.relationship('Assignment', backref='student', lazy=True)

class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    instructor_id = db.Column(db.Integer, db.ForeignKey('clinical_instructor.id'), nullable=False)
    assigned_day = db.Column(db.String(128), nullable=False)
