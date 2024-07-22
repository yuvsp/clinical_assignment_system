from . import db


class ClinicalInstructor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    practice_location = db.Column(db.String(100), nullable=False)
    area_of_expertise_id = db.Column(db.Integer, db.ForeignKey('field.id'), nullable=False)
    area_of_expertise = db.relationship('Field', backref='instructors')
    city = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    relevant_semesters = db.Column(db.String(100), nullable=False)
    years_of_experience = db.Column(db.Integer, nullable=False)
    available_days_to_assign = db.Column(db.String(100), nullable=False)
    max_students_per_day = db.Column(db.Integer, nullable=False)
    color = db.Column(db.String(7), nullable=False, default='#FFFFFF')  # Default to white
    single_assignment = db.Column(db.Boolean, default=False)  # New field

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    preferred_field_id_1 = db.Column(db.Integer, db.ForeignKey('field.id'), nullable=False)
    preferred_field_1 = db.relationship('Field', foreign_keys=[preferred_field_id_1], backref='students_1')
    preferred_field_id_2 = db.Column(db.Integer, db.ForeignKey('field.id'), nullable=False)
    preferred_field_2 = db.relationship('Field', foreign_keys=[preferred_field_id_2], backref='students_2')
    preferred_field_id_3 = db.Column(db.Integer, db.ForeignKey('field.id'), nullable=False)
    preferred_field_3 = db.relationship('Field', foreign_keys=[preferred_field_id_3], backref='students_3')
    preferred_practice_area = db.Column(db.String(100), nullable=False)
    semester = db.Column(db.String(1), nullable=False, default='א')  # New field for semester

class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    instructor_id = db.Column(db.Integer, db.ForeignKey('clinical_instructor.id'), nullable=False)
    assigned_day = db.Column(db.String(20), nullable=False)
    instructor = db.relationship('ClinicalInstructor', backref='assignments')
    student = db.relationship('Student', backref='assignments')

class Field(db.Model):
    __tablename__ = 'field'
    __table_args__ = {'extend_existing': True}  # Add this line

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    color = db.Column(db.String(7), nullable=False, default='#FFFFFF')  # Default to white
