from flask import Blueprint, render_template, request, redirect, url_for, send_file, jsonify, flash
from werkzeug.utils import secure_filename
from app import db
from app.models import ClinicalInstructor, Student, Assignment, Field
import pandas as pd
import io
import os
from datetime import datetime
from collections import defaultdict
import random
import base64

# def generate_color():
#     r = lambda: random.randint(0, 255)
#     return f'#{r():02X}{r():02X}{r():02X}'

def generate_color():
    return "#{:06x}".format(random.randint(0, 0xFFFFFF))

# FIXED_COLORS = {
#     'אדלר': '#CB2267',
#     'תדהר': '#34a853',
#     'המרכז הרפואי': '#4285f4',
#     'בניין אור': '#fbbc05',
#     'בית חולים': '#ea4335'
# }


bp = Blueprint('main', __name__)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'xlsx'} 

if not os.path.exists(UPLOAD_FOLDER): 
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/')
def main_view():
    return redirect(url_for('main.current_assignments_table'))  # Redirect home to current assignments

@bp.route('/current_assignments')
def current_assignments():
    semester = request.args.get('semester', 'א')  # Default to semester 'א'
    students = Student.query.filter_by(semester=semester).all()
    assignments = Assignment.query.all()
    student_assignments = {}

    for student in students:
        student_assignments[student.id] = {
            'name': student.name,
            'preferred_fields': [
                student.preferred_field_1.name if student.preferred_field_1 else '',
                student.preferred_field_2.name if student.preferred_field_2 else '',
                student.preferred_field_3.name if student.preferred_field_3 else ''
            ],
            'assignments': [None, None, None]  # Placeholder for three assignments
        }

    for assignment in assignments:
        student_id = assignment.student_id
        student_data = student_assignments.get(student_id)
        if student_data:
            for i, preferred_field in enumerate(student_data['preferred_fields']):
                if len(student_data['assignments']) > i and student_data['assignments'][i] is None:
                    student_data['assignments'][i] = assignment
                    break

    return render_template('current_assignments.html', student_assignments=student_assignments, semester=semester)

@bp.route('/instructors')
def instructors_view():
    instructors = ClinicalInstructor.query.all()
    return render_template('instructors.html', instructors=instructors)

@bp.route('/students')
def students_view():
    students = Student.query.all()
    return render_template('students.html', students=students)

@bp.route('/fields')
def fields_view():
    fields = Field.query.all()
    return render_template('fields.html', fields=fields)

@bp.route('/add_field', methods=['GET', 'POST'])
def add_field():
    if request.method == 'POST':
        name = request.form['name']
        color = generate_color()
        new_field = Field(name=name, color=color)
        db.session.add(new_field)
        db.session.commit()
        return redirect(url_for('main.fields_view'))
    return render_template('add_field.html')

@bp.route('/add_instructor', methods=['GET', 'POST'])
def add_instructor():
    fields = Field.query.all()
    if request.method == 'POST':
        name = request.form['name']
        practice_location = request.form['practice_location']
        area_of_expertise_id = request.form['area_of_expertise']
        city = request.form['city']
        address = request.form['address']
        phone = request.form['phone']
        email = request.form['email']
        relevant_semesters = request.form['relevant_semesters']
        years_of_experience = request.form['years_of_experience']
        available_days_to_assign = ','.join(request.form.getlist('available_days_to_assign'))
        max_students_per_day = request.form['max_students_per_day']
        color = request.form['color']  # Add this line

        new_instructor = ClinicalInstructor(
            name=name,
            practice_location=practice_location,
            area_of_expertise_id=area_of_expertise_id,
            city=city,
            address=address,
            phone=phone,
            email=email,
            relevant_semesters=relevant_semesters,
            years_of_experience=years_of_experience,
            available_days_to_assign=available_days_to_assign,
            max_students_per_day=max_students_per_day,
            color=color  # Add this line
        )

        db.session.add(new_instructor)
        db.session.commit()

        return redirect(url_for('main.instructors_view'))

    return render_template('add_instructor.html', fields=fields)


@bp.route('/add_student', methods=['GET', 'POST'])
def add_student():
    fields = Field.query.all()
    if request.method == 'POST':
        new_student = Student(
            name=request.form['name'],
            preferred_field_id_1=request.form['preferred_fields_1'],
            preferred_field_id_2=request.form['preferred_fields_2'],
            preferred_field_id_3=request.form['preferred_fields_3'],
            preferred_practice_area=request.form['preferred_practice_area'],
            semester=request.form['semester']  # Add semester to the form processing
        )
        db.session.add(new_student)
        db.session.commit()
        return redirect(url_for('main.students_view'))
    return render_template('add_student.html', fields=fields)

@bp.route('/assign/<int:student_id>', methods=['GET', 'POST'])
def assign_instructor(student_id):
    student = Student.query.get(student_id)
    if request.method == 'POST':
        if 'cancel_assignment_id' in request.form:
            assignment_id = request.form['cancel_assignment_id']
            assignment = Assignment.query.get(assignment_id)
            if assignment:
                instructor = assignment.instructor
                db.session.delete(assignment)
                db.session.commit()

                # Restore availability if all assignments are canceled
                if instructor and instructor.single_assignment:
                    remaining_assignments = Assignment.query.filter_by(instructor_id=instructor.id).count()
                    if remaining_assignments == 0:
                        original_days = [day.replace('-לא-זמין', '') for day in instructor.available_days_to_assign.split(',')]
                        instructor.available_days_to_assign = ','.join(original_days)
                        db.session.add(instructor)
                        db.session.commit()

            return redirect(url_for('main.assign_instructor', student_id=student_id))

        instructor_id = request.form['instructor_id']
        assigned_day = request.form['assigned_day']
        allocation = request.form.get('allocation', 'שפה')

        if allocation == 'אודיו ושיקום':
            # Remove all existing "שפה" assignments
            Assignment.query.filter_by(student_id=student_id, allocation='שפה').delete()

            # Add the "אודיו ושיקום" assignment if it doesn't already exist
            existing_assignment = Assignment.query.filter_by(student_id=student_id, allocation='אודיו ושיקום').first()
            if not existing_assignment:
                assignment = Assignment(
                    student_id=student.id,
                    instructor_id=501,  # Set the instructor_id to 501 for "אודיו ושיקום"
                    assigned_day='ראשון',  # Set the assigned day to "ראשון"
                    allocation='אודיו ושיקום'
                )
                db.session.add(assignment)
        elif allocation == 'שפה':
            # Remove any existing "אודיו ושיקום" assignments
            Assignment.query.filter_by(student_id=student_id, allocation='אודיו ושיקום').delete()

            # Add the new "שפה" assignment
            assignment = Assignment(student_id=student.id, instructor_id=instructor_id, assigned_day=assigned_day, allocation=allocation)
            db.session.add(assignment)

            instructor = ClinicalInstructor.query.get(instructor_id)
            if instructor and instructor.single_assignment:
                # Mark other days as unavailable without removing them
                available_days = instructor.available_days_to_assign.split(',')
                available_days_with_suffix = [day if day == assigned_day else day + '-לא-זמין' for day in available_days]
                instructor.available_days_to_assign = ','.join(available_days_with_suffix)
                db.session.add(instructor)

        db.session.commit()
        return redirect(url_for('main.assign_instructor', student_id=student_id))

    preferred_fields = [
        student.preferred_field_1.name if student.preferred_field_1 else '',
        student.preferred_field_2.name if student.preferred_field_2 else '',
        student.preferred_field_3.name if student.preferred_field_3 else ''
    ]
    all_instructors = ClinicalInstructor.query.all()
    relevant_instructors = []
    irrelevant_instructors = []

    # Get all assignments for the student
    student_assignments = Assignment.query.filter_by(student_id=student_id).all()
    student_assigned_days = [assignment.assigned_day for assignment in student_assignments]

    for instructor in all_instructors:
        available_days = instructor.available_days_to_assign.split(',')
        for day in available_days:
            if 'לא-זמין' in day:
                continue
            assigned_count = Assignment.query.filter_by(instructor_id=instructor.id, assigned_day=day).count()
            if day in student_assigned_days:
                student_already_assigned_to_instructor = any(assignment.instructor_id == instructor.id for assignment in student_assignments)
                if student_already_assigned_to_instructor:
                    assignment = next((assignment for assignment in student_assignments if assignment.instructor_id == instructor.id and assignment.assigned_day == day), None)
                    relevant_instructors.append((instructor, day, assignment, True))
                else:
                    irrelevant_instructors.append((instructor, day, "הסטודנטית כבר משובצת ביום זה"))
            elif assigned_count < instructor.max_students_per_day:
                if instructor.area_of_expertise.name in preferred_fields:
                    relevant_instructors.append((instructor, day, None, False))
                else:
                    irrelevant_instructors.append((instructor, day, "תחום לא מועדף של הסטודנטית"))
            else:
                irrelevant_instructors.append((instructor, day, "הקלינאית תפוסה ביום זה"))

    # Sort relevant instructors by preferred fields order
    relevant_instructors.sort(key=lambda x: preferred_fields.index(x[0].area_of_expertise.name) if x[0].area_of_expertise.name in preferred_fields else len(preferred_fields))
    irrelevant_instructors.sort(key=lambda x: preferred_fields.index(x[0].area_of_expertise.name) if x[0].area_of_expertise.name in preferred_fields else len(preferred_fields))

    return render_template('assign.html', student=student, relevant_instructor_days=relevant_instructors, irrelevant_instructors=irrelevant_instructors, student_assigned_days=student_assigned_days, preferred_fields=preferred_fields)

@bp.route('/relevant_instructors/<int:student_id>')       
def relevant_instructors(student_id):
    student = Student.query.get(student_id)
    if not student:
        return jsonify({'error': 'Student not found'}), 404

    preferred_fields = [
        student.preferred_field_1.name if student.preferred_field_1 else '',
        student.preferred_field_2.name if student.preferred_field_2 else '',
        student.preferred_field_3.name if student.preferred_field_3 else ''
    ]

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
                if instructor.area_of_expertise.name in preferred_fields:
                    if day not in student_assigned_days:
                        relevant_instructors.append({
                            'name': instructor.name,
                            'area_of_expertise': instructor.area_of_expertise.name,
                            'day': day
                        })
                    else:
                        irrelevant_instructors.append({
                            'name': instructor.name,
                            'area_of_expertise': instructor.area_of_expertise.name,
                            'day': day,
                            'reason': "לסטודנטית כבר יש שיבוץ באותו יום"
                        })
                else:
                    irrelevant_instructors.append({
                        'name': instructor.name,
                        'area_of_expertise': instructor.area_of_expertise.name,
                        'day': day,
                        'reason': "תחום לא מועדף של הסטודנטית"
                    })
            else:
                irrelevant_instructors.append({
                    'name': instructor.name,
                    'area_of_expertise': instructor.area_of_expertise.name,
                    'day': day,
                    'reason': "הקלינאית תפוסה ביום זה"
                })

    return jsonify({'relevant_instructors': relevant_instructors, 'irrelevant_instructors': irrelevant_instructors})

@bp.route('/download_instructors')
def download_instructors():
    timestamp = datetime.now().strftime("%d_%m_%y_%H_%M")
    filename = f"instructors_{timestamp}.xlsx"

    instructors = ClinicalInstructor.query.all()
    data = [{
        'Name': instructor.name,
        'Practice Location': instructor.practice_location,
        'Area of Expertise': instructor.area_of_expertise.name,
        'City': instructor.city,
        'Address': instructor.address,
        'Phone': instructor.phone,
        'Email': instructor.email,
        'Relevant Semesters': instructor.relevant_semesters,
        'Years of Experience': instructor.years_of_experience,
        'Available Days to Assign': instructor.available_days_to_assign,
        'Max Students Per Day': instructor.max_students_per_day,
        'Color': instructor.color,
        'Single Assignment': instructor.single_assignment  # Include single_assignment in the data
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

    # Prepare data for the Excel file
    data = []
    for student in students:
        row = {
            'Name': student.name,
            'Preferred Field 1': student.preferred_field_1.name if student.preferred_field_1 else '',
            'Preferred Field 2': student.preferred_field_2.name if student.preferred_field_2 else '',
            'Preferred Field 3': student.preferred_field_3.name if student.preferred_field_3 else '',
            'Preferred Practice Area': student.preferred_practice_area,
            'Semester': student.semester  # Include semester in the data
        }
        data.append(row)

    # Create a DataFrame
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
                    'Student Name': f"{student.name} #{i + 1} [ {', '.join([student.preferred_field_1.name if student.preferred_field_1 else '', student.preferred_field_2.name if student.preferred_field_2 else '', student.preferred_field_3.name if student.preferred_field_3 else ''])} ]",
                    'Assigned Instructor': assignment.instructor.name,
                    'Instructor Field': assignment.instructor.area_of_expertise.name,
                    'Assigned Day': assignment.assigned_day
                }
            else:
                row = {
                    'Student Name': f"{student.name} #{i + 1} [ {', '.join([student.preferred_field_1.name if student.preferred_field_1 else '', student.preferred_field_2.name if student.preferred_field_2 else '', student.preferred_field_3.name if student.preferred_field_3 else ''])} ]",
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
            flash('No file part', 'danger')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)
            try:
                process_student_file(filepath)
            except Exception as e:
                flash(f"Error processing file: {e}", 'danger')
            return redirect(url_for('main.students_view'))
    return render_template('upload_students.html')

def process_student_file(filepath):
    try:
        df = pd.read_excel(filepath)
        
        # Check for required columns
        required_columns = ['Name', 'Preferred Field 1', 'Preferred Field 2', 'Preferred Field 3', 'Preferred Practice Area', 'Semester']
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"Missing column: {col}")
        
        # Clear existing records
        Student.query.delete()
        db.session.commit()

        # Add new records from the Excel file
        for _, row in df.iterrows():
            new_student = Student(
                name=row['Name'],
                preferred_field_1=Field.query.filter_by(name=row['Preferred Field 1']).first(),
                preferred_field_2=Field.query.filter_by(name=row['Preferred Field 2']).first(),
                preferred_field_3=Field.query.filter_by(name=row['Preferred Field 3']).first(),
                preferred_practice_area=row['Preferred Practice Area'],
                semester=row.get('Semester', 'א')  # Default to 'א' if the semester field is missing
            )
            db.session.add(new_student)
        db.session.commit()
    
    except Exception as e:
        flash(str(e), 'danger')
        db.session.rollback()


@bp.route('/upload_instructors', methods=['GET', 'POST'])
def upload_instructors():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)
            try:
                process_instructor_file(filepath)
            except Exception as e:
                flash(f"Error processing file: {e}", 'danger')
            return redirect(url_for('main.instructors_view'))
    return render_template('upload_instructors.html')

def process_instructor_file(filepath):
    try:
        df = pd.read_excel(filepath)
        
        required_columns = ['Name', 'Practice Location', 'Area of Expertise', 'City', 'Address', 'Phone', 'Email', 'Relevant Semesters', 'Years of Experience', 'Available Days to Assign', 'Max Students Per Day', 'Color', 'Single Assignment']
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"Missing column: {col}")
        
        # Clear existing records
        ClinicalInstructor.query.delete()
        db.session.commit()

        # Add new records from the Excel file
        for _, row in df.iterrows():
            color = row.get('Color')
            if not color or not isinstance(color, str) or len(color) != 7 or not color.startswith('#'):
                color = generate_color()
            new_instructor = ClinicalInstructor(
                name=row['Name'],
                practice_location=row['Practice Location'],
                area_of_expertise_id=Field.query.filter_by(name=row['Area of Expertise']).first().id,
                city=row['City'],
                address=row['Address'],
                phone=row['Phone'],
                email=row['Email'],
                relevant_semesters=row['Relevant Semesters'],
                years_of_experience=row['Years of Experience'],
                available_days_to_assign=row['Available Days to Assign'],
                max_students_per_day=row['Max Students Per Day'],
                color=color,
                single_assignment=row['Single Assignment'] if 'Single Assignment' in row and not pd.isnull(row['Single Assignment']) else False  # Include single_assignment
            )
            db.session.add(new_instructor)
        db.session.commit()
    
    except Exception as e:
        flash(str(e), 'danger')
        db.session.rollback()

@bp.route('/remove_assignment/<int:assignment_id>', methods=['POST']) 
def remove_assignment(assignment_id):
    assignment = Assignment.query.get_or_404(assignment_id)
    db.session.delete(assignment)
    db.session.commit()
    return redirect(url_for('main.current_assignments_table'))

@bp.route('/assignments_view')
def assignments_view():
    semester = request.args.get('semester', 'א')  # Default to semester 'א'
    students = Student.query.filter_by(semester=semester).all()
    days_of_week = ['ראשון', 'שני', 'שלישי', 'רביעי', 'חמישי']
    
    # Create a dictionary for assignments data
    assignments_data = {student.name: {day: None for day in days_of_week} for student in students}
    instructor_colors = {instructor.name: instructor.color for instructor in ClinicalInstructor.query.all()}
    
    assignments = Assignment.query.all()
    
    for assignment in assignments:
        student_name = assignment.student.name
        if student_name in assignments_data:  # Ensure the student is in the filtered students list
            day = assignment.assigned_day
            if assignment.instructor:
                instructor_name = assignment.instructor.name
                practice_location = assignment.instructor.practice_location
                area_of_expertise = assignment.instructor.area_of_expertise.name
                color_class = f"color-{instructor_name.replace(' ', '-').replace('.', '').lower()}"
                assignments_data[student_name][day] = {
                    'text': f"{instructor_name} - {practice_location} - {area_of_expertise}",
                    'color_class': color_class
                }
            else:
                assignments_data[student_name][day] = {
                    'text': 'N/A',
                    'color_class': 'color-none'
                }

    student_assignments_count = {student.name: 0 for student in students}
    for assignment in assignments:
        student_name = assignment.student.name
        if student_name in student_assignments_count:  # Ensure the student is in the filtered students list
            student_assignments_count[student_name] += 1

    student_assignments_status = {}
    for student in students:
        assignments_count = student_assignments_count[student.name]
        if assignments_count >= 3:
            student_assignments_status[student.name] = f"✅ {student.name}"
        else:
            student_assignments_status[student.name] = f"❌ {student.name}"
    
    return render_template('assignments_view.html', assignments_data=assignments_data, days_of_week=days_of_week, instructor_colors=instructor_colors, student_assignments_status=student_assignments_status, students=students, semester=semester)

@bp.route('/download_fields')
def download_fields():
    timestamp = datetime.now().strftime("%d_%m_%y_%H_%M")
    filename = f"fields_{timestamp}.xlsx"

    fields = Field.query.all()
    data = [{'Name': field.name, 'Color': field.color} for field in fields]

    df = pd.DataFrame(data)
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='Fields')
    writer.close()
    output.seek(0)

    return send_file(output, download_name=filename, as_attachment=True)

@bp.route('/upload_fields', methods=['POST'])
def upload_fields():
    if 'file' not in request.files:
        return redirect(url_for('main.fields_view'))
    file = request.files['file']
    if file.filename == '':
        return redirect(url_for('main.fields_view'))
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        process_fields_file(filepath)
        return redirect(url_for('main.fields_view'))
    return redirect(url_for('main.fields_view'))

def process_fields_file(filepath):
    data = pd.read_excel(filepath)
    
    # Clear existing records
    Field.query.delete()
    db.session.commit()
    
    for index, row in data.iterrows():
        field_name = row['Name']
        field_color = row.get('Color', None)
        if not field_color or not isinstance(field_color, str) or len(field_color) != 7 or not field_color.startswith('#'):
            field_color = generate_color()
        new_field = Field(name=field_name, color=field_color)
        db.session.add(new_field)
    db.session.commit()

import pandas as pd
import io
from flask import send_file
from datetime import datetime

@bp.route('/download_assignments_view')
def download_assignments_view():
    students = Student.query.all()
    days_of_week = ['ראשון', 'שני', 'שלישי', 'רביעי', 'חמישי']

    assignments_data = {student.name: {day: None for day in days_of_week} for student in students}
    instructor_colors = {instructor.name: instructor.color for instructor in ClinicalInstructor.query.all()}

    assignments = Assignment.query.all()

    for assignment in assignments:
        student_name = assignment.student.name
        day = assignment.assigned_day
        instructor_name = assignment.instructor.name
        practice_location = assignment.instructor.practice_location
        area_of_expertise = assignment.instructor.area_of_expertise.name
        color_class = f"color-{instructor_name.replace(' ', '-').replace('.', '').lower()}"
        assignments_data[student_name][day] = {
            'text': f"{instructor_name} - {practice_location} - {area_of_expertise}",
            'color_class': color_class,
            'color': instructor_colors[instructor_name]
        }

    # Create a DataFrame
    data = []
    for student_name, days in assignments_data.items():
        row = [student_name]
        for day in days_of_week:
            if days[day]:
                row.append({
                    'text': days[day]['text'],
                    'color': days[day]['color']
                })
            else:
                row.append(None)
        data.append(row)

    df = pd.DataFrame(data, columns=['Student Name'] + days_of_week)

    # Create an Excel file with colors
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='Assignments View')

    workbook = writer.book
    worksheet = writer.sheets['Assignments View']

    # Set column widths and RTL direction
    worksheet.set_column('A:F', 22)  
    worksheet.right_to_left()

    # Apply colors to cells
    for row_num, row in enumerate(data, start=1):
        for col_num, cell in enumerate(row[1:], start=1):
            if cell:
                cell_format = workbook.add_format({'bg_color': cell['color']})
                worksheet.write(row_num, col_num, cell['text'], cell_format)
            else:
                worksheet.write(row_num, col_num, '')

    writer.close()
    output.seek(0)

    timestamp = datetime.now().strftime("%d_%m_%y_%H_%M")
    filename = f"assignments_view_{timestamp}.xlsx"

    return send_file(output, download_name=filename, as_attachment=True)

@bp.route('/export_backup_excel')
def export_backup_excel():
    timestamp = datetime.now().strftime("%d_%m_%y_%H_%M")
    filename = f"assignments_backup_{timestamp}.xlsx"

    assignments = Assignment.query.all()
    data = [{
        'Student Name': assignment.student.name,
        'Instructor Name': assignment.instructor.name,
        'Assigned Day': assignment.assigned_day,
        'Instructor Field': assignment.instructor.area_of_expertise.name,
        'Practice Location': assignment.instructor.practice_location
    } for assignment in assignments]

    df = pd.DataFrame(data)
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='Assignments')
    writer.close()
    output.seek(0)

    return send_file(output, download_name=filename, as_attachment=True)

@bp.route('/import_backup_excel', methods=['POST'])
def import_backup_excel():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(url_for('main.current_assignments_table'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No selected file')
        return redirect(url_for('main.current_assignments_table'))
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join('uploads', filename)
        file.save(filepath)
        process_backup_file(filepath)
        return redirect(url_for('main.current_assignments_table'))

    flash('Invalid file format')
    return redirect(url_for('main.current_assignments_table'))

def process_backup_file(filepath):
    df = pd.read_excel(filepath)

    # Clear existing assignments
    Assignment.query.delete()
    db.session.commit()

    # Add new assignments from the Excel file
    for _, row in df.iterrows():
        student = Student.query.filter_by(name=row['Student Name']).first()
        instructor = ClinicalInstructor.query.filter_by(name=row['Instructor Name']).first()
        if student and instructor:
            new_assignment = Assignment(
                student_id=student.id,
                instructor_id=instructor.id,
                assigned_day=row['Assigned Day']
            )
            db.session.add(new_assignment)
    db.session.commit()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'xlsx'}


@bp.route('/editable_instructors', methods=['GET', 'POST'])
def editable_instructors():
    if request.method == 'POST':
        data = request.get_json()
        if data:
            for instructor_data in data:
                instructor = ClinicalInstructor.query.get(instructor_data['id'])
                if instructor:
                    instructor.name = instructor_data['name']
                    instructor.practice_location = instructor_data['practice_location']
                    instructor.area_of_expertise_id = Field.query.filter_by(name=instructor_data['area_of_expertise']).first().id
                    instructor.city = instructor_data['city']
                    instructor.address = instructor_data['address']
                    instructor.phone = instructor_data['phone']
                    instructor.email = instructor_data['email']
                    instructor.relevant_semesters = instructor_data['relevant_semesters']
                    instructor.years_of_experience = instructor_data['years_of_experience']
                    instructor.available_days_to_assign = instructor_data['available_days_to_assign']
                    instructor.max_students_per_day = instructor_data['max_students_per_day']
                    instructor.color = instructor_data['color']
                    old_single_assignment = instructor.single_assignment
                    instructor.single_assignment = instructor_data['single_assignment']
                    
                    # If single_assignment changed from True to False, clear the suffix
                    if old_single_assignment and not instructor.single_assignment:
                        original_days = [day.replace('-לא-זמין', '') for day in instructor.available_days_to_assign.split(',')]
                        instructor.available_days_to_assign = ','.join(original_days)
                    
            db.session.commit()
            return jsonify({'success': True}), 200
        return jsonify({'success': False}), 400
    
    instructors = ClinicalInstructor.query.all()
    fields = Field.query.all()
    return render_template('editable_instructors.html', instructors=instructors, fields=fields)

@bp.route('/current_assignments_table')
def current_assignments_table():
    semester = request.args.get('semester', 'א')
    students = Student.query.all()  # Get all students
    assignments = Assignment.query.all()

    student_assignments = {}

    for student in students:
        student_assignments[student.id] = {
            'id': student.id,  # Include student_id
            'name': student.name,
            'preferred_fields': [
                student.preferred_field_1.name if student.preferred_field_1 else '',
                student.preferred_field_2.name if student.preferred_field_2 else '',
                student.preferred_field_3.name if student.preferred_field_3 else ''
            ],
            'allocation': 'שפה',  # Default to שפה
            'assignments': [None, None, None]
        }

    for assignment in assignments:
        student_id = assignment.student_id
        student_data = student_assignments.get(student_id)
        if student_data:
            if assignment.allocation:
                student_data['allocation'] = assignment.allocation

            for i, _ in enumerate(student_data['assignments']):
                if student_data['assignments'][i] is None:
                    student_data['assignments'][i] = assignment
                    break

    # Convert dictionary to a list and sort it
    sorted_students = sorted(student_assignments.values(), key=lambda x: (
        x['allocation'] != 'שפה',
        x['allocation'] != 'אודיו ושיקום'
    ))

    return render_template('current_assignments_table.html', student_assignments=sorted_students, semester=semester)

@bp.route('/update_allocation/<int:student_id>', methods=['POST'])
def update_allocation(student_id):
    data = request.get_json()
    allocation = data.get('allocation')

    if allocation not in ['שפה', 'אודיו ושיקום']:
        return jsonify({'success': False, 'error': 'Invalid allocation value'}), 400

    student = Student.query.get(student_id)
    if not student:
        return jsonify({'success': False, 'error': 'Student not found'}), 404

    if allocation == 'אודיו ושיקום':
        # Remove all existing "שפה" assignments
        Assignment.query.filter_by(student_id=student_id, allocation='שפה').delete()

        # Add the "אודיו ושיקום" assignment if it doesn't already exist
        existing_assignment = Assignment.query.filter_by(student_id=student_id, allocation='אודיו ושיקום').first()
        if not existing_assignment:
            new_assignment = Assignment(
                student_id=student_id,
                instructor_id=501,  # Set the instructor_id to 501 for "אודיו ושיקום"
                assigned_day='ראשון',  # Set the assigned day to "ראשון"
                allocation='אודיו ושיקום'
            )
            db.session.add(new_assignment)
    elif allocation == 'שפה':
        # Remove any existing "אודיו ושיקום" assignments
        Assignment.query.filter_by(student_id=student_id, allocation='אודיו ושיקום').delete()

    db.session.commit()
    return jsonify({'success': True}), 200
