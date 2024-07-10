from flask import Blueprint, render_template, request, redirect, url_for, send_file, jsonify, flash
from werkzeug.utils import secure_filename
from app import db
from app.models import ClinicalInstructor, Student, Assignment
import pandas as pd
import io
import os
from datetime import datetime

bp = Blueprint('main', __name__)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'xlsx'} 

if not os.path.exists(UPLOAD_FOLDER): 
    os.makedirs(UPLOAD_FOLDER)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@bp.route('/')
def main_view():
    return redirect(url_for('main.current_assignments'))  # Redirect home to current assignments

@bp.route('/current_assignments')
def current_assignments():
    students = Student.query.all()
    assignments = Assignment.query.all()
    student_assignments = {}

    for student in students:
        student_assignments[student.id] = {
            'name': student.name,
            'preferred_fields': student.preferred_fields.split(','),
            'assignments': [None, None, None]  # Placeholder for three assignments
        }

    for assignment in assignments:
        student_id = assignment.student_id
        student_data = student_assignments[student_id]
        for i, preferred_field in enumerate(student_data['preferred_fields']):
            if len(student_data['assignments']) > i and student_data['assignments'][i] is None:
                student_data['assignments'][i] = assignment
                break

    return render_template('current_assignments.html', student_assignments=student_assignments)

@bp.route('/instructors')
def instructors_view():
    instructors = ClinicalInstructor.query.all()
    return render_template('instructors.html', instructors=instructors)

@bp.route('/students')
def students_view():
    students = Student.query.all()
    return render_template('students.html', students=students)

@bp.route('/add_instructor', methods=['GET', 'POST'])
def add_instructor():
    if request.method == 'POST':
        available_days = request.form.getlist('available_days_to_assign')
        available_days_str = ','.join(available_days)

        new_instructor = ClinicalInstructor(
            name=request.form['name'],
            practice_location=request.form['practice_location'],
            area_of_expertise=request.form['area_of_expertise'],
            city=request.form['city'],
            address=request.form['address'],
            phone=request.form['phone'],
            email=request.form['email'],
            relevant_semesters=request.form['relevant_semesters'],
            years_of_experience=request.form['years_of_experience'],
            available_days_to_assign=available_days_str,
            max_students_per_day=request.form['max_students_per_day']
        )
        db.session.add(new_instructor)
        db.session.commit()
        return redirect(url_for('main.instructors_view'))
    return render_template('add_instructor.html')

@bp.route('/add_student', methods=['GET', 'POST'])
def add_student():
    if request.method == 'POST':
        new_student = Student(
            name=request.form['name'],
            preferred_fields=','.join([
                request.form['preferred_fields_1'],
                request.form['preferred_fields_2'],
                request.form['preferred_fields_3']
            ]),
            preferred_practice_area=request.form['preferred_practice_area']
        )
        db.session.add(new_student)
        db.session.commit()
        return redirect(url_for('main.students_view'))
    return render_template('add_student.html')

@bp.route('/assign/<int:student_id>', methods=['GET', 'POST'])
def assign_instructor(student_id):
    student = Student.query.get(student_id)
    if request.method == 'POST':
        if 'cancel_assignment_id' in request.form:
            assignment_id = request.form['cancel_assignment_id']
            assignment = Assignment.query.get(assignment_id)
            if assignment:
                db.session.delete(assignment)
                db.session.commit()
            return redirect(url_for('main.current_assignments'))

        instructor_id = request.form['instructor_id']
        assigned_day = request.form['assigned_day']

        # Check if the student already has an assignment on the selected day
        existing_assignment = Assignment.query.filter_by(student_id=student.id, assigned_day=assigned_day).first()
        if existing_assignment:
            return redirect(url_for('main.current_assignments'))  # Redirect if already assigned

        assignment = Assignment(student_id=student.id, instructor_id=instructor_id, assigned_day=assigned_day)
        db.session.add(assignment)
        db.session.commit()
        return redirect(url_for('main.current_assignments'))

    preferred_fields = student.preferred_fields.split(',')
    all_instructors = ClinicalInstructor.query.all()
    relevant_instructors = []
    irrelevant_instructors = []

    # Get all assignments for the student
    student_assignments = Assignment.query.filter_by(student_id=student_id).all()
    student_assigned_days = [assignment.assigned_day for assignment in student_assignments]

    for instructor in all_instructors:
        available_days = instructor.available_days_to_assign.split(',')
        for day in available_days:
            assigned_count = Assignment.query.filter_by(instructor_id=instructor.id, assigned_day=day).count()
            if day in student_assigned_days:
                student_already_assigned_to_instructor = any(assignment.instructor_id == instructor.id for assignment in student_assignments)
                if student_already_assigned_to_instructor:
                    assignment = next(assignment for assignment in student_assignments if assignment.instructor_id == instructor.id and assignment.assigned_day == day)
                    relevant_instructors.append((instructor, day, assignment, True))
                else:
                    irrelevant_instructors.append((instructor, day, "Student already has assignment at this day"))
            elif assigned_count < instructor.max_students_per_day:
                if instructor.area_of_expertise in preferred_fields:
                    relevant_instructors.append((instructor, day, None, False))
                else:
                    irrelevant_instructors.append((instructor, day, "Field is not relevant"))
            else:
                irrelevant_instructors.append((instructor, day, "Instructor is booked for the selected day"))

    return render_template('assign.html', student=student, relevant_instructor_days=relevant_instructors, irrelevant_instructors=irrelevant_instructors, student_assigned_days=student_assigned_days)

@bp.route('/relevant_instructors/<int:student_id>')
def relevant_instructors(student_id):
    student = Student.query.get(student_id)
    if not student:
        return jsonify({'error': 'Student not found'}), 404

    preferred_fields = student.preferred_fields.split(',')
    all_instructors = ClinicalInstructor.query.all()
    relevant_instructors = []
    irrelevant_instructors = []

    # Get all assignments for the student
    student_assignments = Assignment.query.filter_by(student_id=student_id).all()
    student_assigned_days = [assignment.assigned_day for assignment in student_assignments]

    for instructor in all_instructors:
        available_days = instructor.available_days_to_assign.split(',')
        for day in available_days:
            assigned_count = Assignment.query.filter_by(instructor_id=instructor.id, assigned_day=day).count()
            if assigned_count < instructor.max_students_per_day:
                if instructor.area_of_expertise in preferred_fields:
                    if day not in student_assigned_days:
                        relevant_instructors.append({'name': instructor.name, 'area_of_expertise': instructor.area_of_expertise, 'day': day})
                    else:
                        irrelevant_instructors.append({'name': instructor.name, 'area_of_expertise': instructor.area_of_expertise, 'day': day, 'reason': "Student already has an instructor assigned for this day"})
                else:
                    irrelevant_instructors.append({'name': instructor.name, 'area_of_expertise': instructor.area_of_expertise, 'day': day, 'reason': "Field is not relevant"})
            else:
                irrelevant_instructors.append({'name': instructor.name, 'area_of_expertise': instructor.area_of_expertise, 'day': day, 'reason': "Instructor is booked for the selected day"})

    return jsonify({'relevant_instructors': relevant_instructors, 'irrelevant_instructors': irrelevant_instructors})

@bp.route('/download_instructors')
def download_instructors():
    timestamp = datetime.now().strftime("%d_%m_%y_%H_%M")
    filename = f"instructors_{timestamp}.xlsx"

    instructors = ClinicalInstructor.query.all()
    data = [{
        'Name': instructor.name,
        'Practice Location': instructor.practice_location,
        'Area of Expertise': instructor.area_of_expertise,
        'City': instructor.city,
        'Address': instructor.address,
        'Phone': instructor.phone,
        'Email': instructor.email,
        'Relevant Semesters': instructor.relevant_semesters,
        'Years of Experience': instructor.years_of_experience,
        'Available Days to Assign': instructor.available_days_to_assign,
        'Max Students per Day': instructor.max_students_per_day
    } for instructor in instructors]

    df = pd.DataFrame(data)
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='Instructors')
    writer.close()
    output.seek(0)

    return send_file(output, download_name=filename, as_attachment=True)

@bp.route('/download_students')
def download_students():
    timestamp = datetime.now().strftime("%d_%m_%y_%H_%M")
    filename = f"students_{timestamp}.xlsx"

    students = Student.query.all()
    data = [{
        'Name': student.name,
        'Preferred Fields': student.preferred_fields,
        'Preferred Practice Area': student.preferred_practice_area
    } for student in students]

    df = pd.DataFrame(data)
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='Students')
    writer.close()
    output.seek(0)

    return send_file(output, download_name=filename, as_attachment=True)

@bp.route('/download_assignments')
def download_assignments():
    timestamp = datetime.now().strftime("%d_%m_%y_%H_%M")
    filename = f"assignments_{timestamp}.xlsx"

    students = Student.query.all()
    assignments = Assignment.query.all()
    
    # Prepare data for the Excel file
    data = []
    for student in students:
        student_assignments = [assignment for assignment in assignments if assignment.student_id == student.id]
        for i in range(3):
            if i < len(student_assignments):
                assignment = student_assignments[i]
                row = {
                    'Student Name': f"{student.name} #{i + 1} [ {student.preferred_fields} ]",
                    'Assigned Instructor': assignment.instructor.name,
                    'Instructor Field': assignment.instructor.area_of_expertise,
                    'Assigned Day': assignment.assigned_day
                }
            else:
                row = {
                    'Student Name': f"{student.name} #{i + 1} [ {student.preferred_fields} ]",
                    'Assigned Instructor': "Not assigned yet",
                    'Instructor Field': "",
                    'Assigned Day': ""
                }
            data.append(row)

    # Create a DataFrame
    df = pd.DataFrame(data)
    
    # Reorder the columns as required
    df = df[['Student Name', 'Assigned Instructor', 'Instructor Field', 'Assigned Day']]
    
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='Assignments')
    writer.close()
    output.seek(0)

    return send_file(output, download_name=filename, as_attachment=True)

@bp.route('/upload_students', methods=['GET', 'POST'])
def upload_students():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)
            process_student_file(filepath)
            return redirect(url_for('main.students_view'))
    return render_template('upload_students.html')

def process_student_file(filepath):
    df = pd.read_excel(filepath)
    # Clear existing records
    Student.query.delete()
    db.session.commit()

    # Add new records from the Excel file
    for _, row in df.iterrows():
        new_student = Student(
            name=row['Name'],
            preferred_fields=row['Preferred Fields'],
            preferred_practice_area=row['Preferred Practice Area']
        )
        db.session.add(new_student)
    db.session.commit()

@bp.route('/upload_instructors', methods=['GET', 'POST'])
def upload_instructors():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)
            process_instructor_file(filepath)
            return redirect(url_for('main.instructors_view'))
    return render_template('upload_instructors.html')

def process_instructor_file(filepath):
    df = pd.read_excel(filepath)
    # Clear existing records
    ClinicalInstructor.query.delete()
    db.session.commit()

    # Add new records from the Excel file
    for _, row in df.iterrows():
        new_instructor = ClinicalInstructor(
            name=row['Name'],
            practice_location=row['Practice Location'],
            area_of_expertise=row['Area of Expertise'],
            city=row['City'],
            address=row['Address'],
            phone=row['Phone'],
            email=row['Email'],
            relevant_semesters=row['Relevant Semesters'],
            years_of_experience=row['Years of Experience'],
            available_days_to_assign=row['Available Days to Assign'],
            max_students_per_day=row['Max Students per Day']
        )
        db.session.add(new_instructor)
    db.session.commit()

@bp.route('/remove_assignment/<int:assignment_id>', methods=['POST']) 
def remove_assignment(assignment_id):
    assignment = Assignment.query.get_or_404(assignment_id)
    db.session.delete(assignment)
    db.session.commit()
    return redirect(url_for('main.current_assignments'))
