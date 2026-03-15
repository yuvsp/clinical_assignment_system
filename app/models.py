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
    has_contract = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False, default="add_email@gmail.com")  # New email field
    preferred_field_id_1 = db.Column(db.Integer, db.ForeignKey('field.id'), nullable=False)
    preferred_field_1 = db.relationship('Field', foreign_keys=[preferred_field_id_1], backref='students_1')
    preferred_field_id_2 = db.Column(db.Integer, db.ForeignKey('field.id'), nullable=False)
    preferred_field_2 = db.relationship('Field', foreign_keys=[preferred_field_id_2], backref='students_2')
    preferred_field_id_3 = db.Column(db.Integer, db.ForeignKey('field.id'), nullable=False)
    preferred_field_3 = db.relationship('Field', foreign_keys=[preferred_field_id_3], backref='students_3')
    preferred_practice_area = db.Column(db.String(100), nullable=False)
    semester = db.Column(db.String(1), nullable=False, default='א')  # Renamed field

class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    instructor_id = db.Column(db.Integer, db.ForeignKey('clinical_instructor.id'), nullable=True)
    assigned_day = db.Column(db.String(20), nullable=False)
    instructor = db.relationship('ClinicalInstructor', backref='assignments')
    student = db.relationship('Student', backref='assignments')

class Field(db.Model):
    __tablename__ = 'field'
    __table_args__ = {'extend_existing': True}  # Add this line

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    color = db.Column(db.String(7), nullable=False, default='#FFFFFF')  # Default to white


class AppSetting(db.Model):
    """Key-value store for app-wide settings (e.g. instructor email template)."""
    __tablename__ = 'app_setting'
    key = db.Column(db.String(100), primary_key=True)
    value = db.Column(db.Text, nullable=True)


############################################################################
class ArchivedSnapshot(db.Model):
    __tablename__ = 'archived_snapshot'
    id = db.Column(db.Integer, primary_key=True)
    snapshot_name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False)

    assignments = db.relationship('ArchivedAssignment', backref='snapshot', lazy=True)

class ArchivedAssignment(db.Model):
    __tablename__ = 'archived_assignment'
    id = db.Column(db.Integer, primary_key=True)

    snapshot_id = db.Column(db.Integer, db.ForeignKey('archived_snapshot.id'), nullable=False)
    
    assigned_day = db.Column(db.String(20), nullable=False)
    # year_semester = db.Column(db.String(10), nullable=False)
    
    student_name = db.Column(db.String(100), nullable=False)
    student_email = db.Column(db.String(100), nullable=False)
    preferred_practice_area = db.Column(db.String(100))

    instructor_name = db.Column(db.String(100), nullable=False)
    instructor_practice_location = db.Column(db.String(100), nullable=False)
    instructor_field_name = db.Column(db.String(100))
