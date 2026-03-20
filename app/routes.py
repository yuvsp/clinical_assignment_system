from flask import Blueprint, render_template, request, redirect, url_for, send_file, jsonify, flash, current_app, session
from werkzeug.utils import secure_filename
from app import db
from app.models import ClinicalInstructor, Student, Assignment, Field, ArchivedSnapshot, ArchivedAssignment, AppSetting
from app.email_utils import get_student_email_html
from app.student_email_utils import generate_unique_student_email, is_legacy_placeholder_email
from app.gmail_oauth import (
    build_gmail_flow,
    clear_gmail_credentials,
    gmail_oauth_configured,
    get_gmail_connection_status,
    get_gmail_profile_email,
    new_gmail_oauth_code_verifier,
    revoke_gmail_credentials,
    send_gmail_message,
    store_gmail_credentials,
    set_gmail_account_email,
)
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
    instructors = ClinicalInstructor.query.options(
        db.joinedload(ClinicalInstructor.assignments).joinedload(Assignment.student)
    ).all()
    for inst in instructors:
        sem = (inst.relevant_semesters or 'א').strip()
        inst._sem_display = sem if sem in ('א', 'ב') else 'א'
    instructors.sort(key=lambda i: (not (i.assignments and len(i.assignments) > 0), (i.name or '').lower()))
    fields = Field.query.all()
    return render_template('instructors.html', instructors=instructors, fields=fields)


@bp.route('/instructors/<int:instructor_id>/update_field', methods=['POST'])
def instructor_update_field(instructor_id):
    instructor = ClinicalInstructor.query.get(instructor_id)
    if not instructor:
        return jsonify({'success': False, 'error': 'Instructor not found'}), 404
    data = request.get_json()
    if not data or 'field' not in data:
        return jsonify({'success': False, 'error': 'Missing field or body'}), 400
    field = data.get('field')
    value = data.get('value')

    # Text / number fields
    if field == 'name':
        instructor.name = (value or '').strip() or instructor.name
    elif field == 'practice_location':
        instructor.practice_location = (value or '').strip() or instructor.practice_location
    elif field == 'city':
        instructor.city = (value or '').strip() or instructor.city
    elif field == 'address':
        instructor.address = (value or '').strip() or instructor.address
    elif field == 'phone':
        instructor.phone = (value or '').strip() or instructor.phone
    elif field == 'available_days_to_assign':
        instructor.available_days_to_assign = (value or '').strip() or instructor.available_days_to_assign
    elif field == 'years_of_experience':
        try:
            n = int(value)
            if n < 0:
                return jsonify({'success': False, 'error': 'Years of experience must be non-negative'}), 400
            instructor.years_of_experience = n
        except (TypeError, ValueError):
            return jsonify({'success': False, 'error': 'Invalid number for years of experience'}), 400
    elif field == 'relevant_semesters':
        v = (value or '').strip()
        if v not in ('א', 'ב'):
            return jsonify({'success': False, 'error': 'Semester must be א or ב'}), 400
        instructor.relevant_semesters = v
    elif field == 'email':
        v = (value or '').strip()
        if not v or not ('.' in v and '@' in v):
            return jsonify({'success': False, 'error': 'Invalid email format'}), 400
        instructor.email = v
    elif field == 'max_students_per_day':
        try:
            n = int(value)
            if n < 0:
                return jsonify({'success': False, 'error': 'Max students per day must be non-negative'}), 400
            instructor.max_students_per_day = n
        except (TypeError, ValueError):
            return jsonify({'success': False, 'error': 'Invalid number for max students per day'}), 400
    elif field == 'color':
        v = (value or '').strip()
        if not v or len(v) != 7 or v[0] != '#' or not all(c in '0123456789abcdefABCDEF' for c in v[1:]):
            return jsonify({'success': False, 'error': 'Color must be #RRGGBB'}), 400
        instructor.color = v
    elif field == 'area_of_expertise':
        name = (value or '').strip()
        f = Field.query.filter_by(name=name).first()
        if not f:
            return jsonify({'success': False, 'error': 'Field not found'}), 400
        instructor.area_of_expertise_id = f.id
    elif field == 'has_contract':
        instructor.has_contract = bool(value)
    elif field == 'is_active':
        instructor.is_active = bool(value)
    elif field == 'single_assignment':
        old_single = instructor.single_assignment
        instructor.single_assignment = bool(value)
        if old_single and not instructor.single_assignment:
            original_days = [d.replace('-לא-זמין', '').strip() for d in instructor.available_days_to_assign.split(',')]
            instructor.available_days_to_assign = ','.join(original_days)
    else:
        return jsonify({'success': False, 'error': 'Unknown field'}), 400

    db.session.add(instructor)
    db.session.commit()
    return jsonify({'success': True, 'field': field, 'value': value})


@bp.route('/students')
def students_view():
    students = Student.query.all()
    assigned_ids = db.session.query(Assignment.student_id).distinct().all()
    student_ids_with_assignments = {row[0] for row in assigned_ids}
    return render_template(
        'students.html',
        students=students,
        student_ids_with_assignments=student_ids_with_assignments,
    )

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
        raw_email = (request.form.get("email") or "").strip()
        if not raw_email or is_legacy_placeholder_email(raw_email):
            email = generate_unique_student_email()
        else:
            email = raw_email
            if Student.query.filter(
                db.func.lower(db.func.trim(Student.email)) == email.lower()
            ).first():
                flash("כתובת האימייל כבר קיימת במערכת.", "danger")
                return render_template("add_student.html", fields=fields)
        new_student = Student(
            name=request.form['name'],
            email=email,
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


@bp.route('/students/<int:student_id>/remove', methods=['POST'])
def remove_student(student_id):
    student = Student.query.get_or_404(student_id)
    try:
        if Assignment.query.filter_by(student_id=student_id).count() > 0:
            flash('לא ניתן למחוק סטודנטית עם שיבוצים קיימים.', 'danger')
            return redirect(url_for('main.students_view'))
        name = student.name
        db.session.delete(student)
        db.session.commit()
        flash(f'הסטודנטית {name} נמחקה מהמערכת.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(str(e), 'danger')
    return redirect(url_for('main.students_view'))


@bp.route('/assign/<int:student_id>', methods=['GET', 'POST'])
def assign_instructor(student_id):
    student = Student.query.get(student_id)

    # Determine allocation based on semester
    allocation = 'שפה' if student.semester == 'א' else 'אודיו ושיקום'

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

        if allocation == 'אודיו ושיקום':
            # Remove all existing "שפה" assignments for this student
            Assignment.query.filter_by(student_id=student_id).delete()

            # Add the "אודיו ושיקום" assignment if it doesn't already exist
            existing_assignment = Assignment.query.filter_by(student_id=student_id, instructor_id=501, assigned_day='ראשון').first()
            if not existing_assignment:
                assignment = Assignment(
                    student_id=student.id,
                    instructor_id=501,  # Assuming instructor_id 501 is for "אודיו ושיקום"
                    assigned_day='ראשון'  # Assigning to Sunday
                )
                db.session.add(assignment)
        elif allocation == 'שפה':
            # Remove any existing "אודיו ושיקום" assignments for this student
            Assignment.query.filter_by(student_id=student_id, instructor_id=501, assigned_day='ראשון').delete()

            # Add the new "שפה" assignment
            assignment = Assignment(student_id=student.id, instructor_id=instructor_id, assigned_day=assigned_day)
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
    all_instructors = ClinicalInstructor.query.filter_by(is_active=True).all()
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


def _can_assign_instructor_to_student_day(instructor_id, student_id, day):
    """Return (valid: bool, reason: str|None). Reuses same rules as relevant_instructors."""
    student = Student.query.get(student_id)
    if not student:
        return False, 'סטודנטית לא נמצאה'
    instructor = ClinicalInstructor.query.get(instructor_id)
    if not instructor:
        return False, 'קלינאית לא נמצאה'
    if not getattr(instructor, 'is_active', True):
        return False, 'הקלינאית אינה פעילה'
    preferred_fields = [
        student.preferred_field_1.name if student.preferred_field_1 else '',
        student.preferred_field_2.name if student.preferred_field_2 else '',
        student.preferred_field_3.name if student.preferred_field_3 else '',
    ]
    student_assignments = Assignment.query.filter_by(student_id=student_id).all()
    if len(student_assignments) >= 3:
        return False, 'לסטודנטית כבר יש שלושה שיבוצים'
    student_assigned_days = [a.assigned_day for a in student_assignments]
    if day in student_assigned_days:
        return False, 'לסטודנטית כבר יש שיבוץ באותו יום'
    available_days = instructor.available_days_to_assign.split(',')
    day_available = day in available_days
    if not day_available:
        return False, 'הקלינאית תפוסה ביום זה'
    assigned_count = Assignment.query.filter_by(instructor_id=instructor_id, assigned_day=day).count()
    if assigned_count >= instructor.max_students_per_day:
        return False, 'הקלינאית תפוסה ביום זה'
    if instructor.area_of_expertise.name not in preferred_fields:
        return False, 'תחום לא מועדף של הסטודנטית'
    return True, None


@bp.route('/can_assign')
def can_assign():
    """GET ?instructor_id=&student_id=&day= -> { valid: bool, reason?: str }"""
    instructor_id = request.args.get('instructor_id', type=int)
    student_id = request.args.get('student_id', type=int)
    day = request.args.get('day')
    if not instructor_id or not student_id or not day:
        return jsonify({'valid': False, 'reason': 'חסרים פרמטרים'}), 400
    valid, reason = _can_assign_instructor_to_student_day(instructor_id, student_id, day)
    if valid:
        return jsonify({'valid': True})
    return jsonify({'valid': False, 'reason': reason or 'לא ניתן לשיבוץ'})


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

    all_instructors = ClinicalInstructor.query.filter_by(is_active=True).all()
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
                            'id': instructor.id,
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


def _build_relevant_instructors_bulk(assignments_list, student_assignments_dict, active_instructors):
    """Build relevant/irrelevant instructors per assignable student using in-memory counts (no N+1)."""
    # (instructor_id, assigned_day) -> count
    count_map = defaultdict(int)
    for a in assignments_list:
        if a.instructor_id is None:
            continue
        count_map[(a.instructor_id, a.assigned_day)] += 1

    result = {}
    for student_id, student_data in student_assignments_dict.items():
        if student_data['allocation'] != 'שפה':
            continue
        assign_list = student_data['assignments']
        non_none = [x for x in assign_list if x is not None]
        if len(non_none) >= 3:
            continue
        student_assigned_days = [a.assigned_day for a in non_none]
        preferred_fields = student_data['preferred_fields']
        relevant_instructors = []
        irrelevant_instructors = []

        for instructor in active_instructors:
            area = instructor.area_of_expertise.name if instructor.area_of_expertise else ''
            available_days = instructor.available_days_to_assign.split(',')
            for day in available_days:
                assigned_count = count_map.get((instructor.id, day), 0)
                if assigned_count >= instructor.max_students_per_day:
                    irrelevant_instructors.append({
                        'name': instructor.name,
                        'area_of_expertise': area,
                        'day': day,
                        'reason': 'הקלינאית תפוסה ביום זה'
                    })
                else:
                    if area in preferred_fields:
                        if day not in student_assigned_days:
                            relevant_instructors.append({
                                'id': instructor.id,
                                'name': instructor.name,
                                'area_of_expertise': area,
                                'day': day
                            })
                        else:
                            irrelevant_instructors.append({
                                'name': instructor.name,
                                'area_of_expertise': area,
                                'day': day,
                                'reason': 'לסטודנטית כבר יש שיבוץ באותו יום'
                            })
                    else:
                        irrelevant_instructors.append({
                            'name': instructor.name,
                            'area_of_expertise': area,
                            'day': day,
                            'reason': 'תחום לא מועדף של הסטודנטית'
                        })

        result[str(student_id)] = {
            'relevant_instructors': relevant_instructors,
            'irrelevant_instructors': irrelevant_instructors
        }
    return result


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
        'Single Assignment': instructor.single_assignment,
        'Has Contract': instructor.has_contract,
        'Is Active': getattr(instructor, 'is_active', True)
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
            'Email': student.email,  # Include email in the export
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

def _upload_row_has_real_email(row) -> bool:
    """True if Email column has a non-empty value other than the legacy shared placeholder."""
    v = row.get("Email")
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return False
    s = str(v).strip()
    if not s:
        return False
    return not is_legacy_placeholder_email(s)


def _resolve_student_id_from_upload_row(row, id_col, students_by_id, all_students):
    """Match by Id, else by email (unique), else by name when email empty/legacy."""
    if id_col is not None:
        raw = row[id_col]
        if pd.notna(raw) and raw is not None and str(raw).strip() != "":
            try:
                sid = int(float(raw))
                if sid in students_by_id:
                    return sid
            except (ValueError, TypeError):
                pass
    if _upload_row_has_real_email(row):
        em = str(row["Email"]).strip().lower()
        for s in all_students:
            if s.email.strip().lower() == em:
                return s.id
        return None
    name = str(row["Name"]).strip() if pd.notna(row["Name"]) else ""
    if not name:
        return None
    for s in all_students:
        if s.name.strip() == name:
            return s.id
    return None


def _student_row_semester(row):
    sem = row.get("Semester", "א")
    if sem is None or (isinstance(sem, float) and pd.isna(sem)):
        return "א"
    s = str(sem).strip()
    return (s[:1] if s else "א") or "א"


def process_student_file(filepath):
    try:
        df = pd.read_excel(filepath)
        if len(df) == 0:
            raise ValueError("הקובץ ריק.")

        required_columns = [
            "Name",
            "Email",
            "Preferred Field 1",
            "Preferred Field 2",
            "Preferred Field 3",
            "Preferred Practice Area",
            "Semester",
        ]
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"Missing column: {col}")

        id_col = None
        for c in df.columns:
            if str(c).strip().lower() == "id":
                id_col = c
                break

        all_students = Student.query.all()
        students_by_id = {s.id: s for s in all_students}

        rows_list = list(df.iterrows())
        resolutions = []
        for _, row in rows_list:
            resolutions.append(
                _resolve_student_id_from_upload_row(row, id_col, students_by_id, all_students)
            )

        seen_matched_ids = set()
        for sid in resolutions:
            if sid is not None:
                if sid in seen_matched_ids:
                    raise ValueError(
                        "שורות כפולות באקסל מפנות לאותה סטודנטית (אותו מזהה, אימייל או שם). "
                        "נא למזג או להסיר כפילות."
                    )
                seen_matched_ids.add(sid)

        new_row_keys = set()
        for (_, row), sid in zip(rows_list, resolutions):
            if sid is not None:
                continue
            if _upload_row_has_real_email(row):
                key = ("email", str(row["Email"]).strip().lower())
            else:
                key = ("name", str(row["Name"]).strip() if pd.notna(row["Name"]) else "")
            if not key[1]:
                raise ValueError("שורה ללא שם; לסטודנטית חדשה ללא אימייל מלא — נא למלא שם ייחודי או אימייל.")
            if key in new_row_keys:
                raise ValueError(
                    "שורות כפולות לסטודנטית חדשה (אותו אימייל, או אותו שם כשאין אימייל מלא בעמודה)."
                )
            new_row_keys.add(key)

        matched_ids = set()

        for (_, row), sid in zip(rows_list, resolutions):
            f1 = Field.query.filter_by(name=row["Preferred Field 1"]).first()
            f2 = Field.query.filter_by(name=row["Preferred Field 2"]).first()
            f3 = Field.query.filter_by(name=row["Preferred Field 3"]).first()
            for label, f, col in (
                ("תחום מועדף 1", f1, "Preferred Field 1"),
                ("תחום מועדף 2", f2, "Preferred Field 2"),
                ("תחום מועדף 3", f3, "Preferred Field 3"),
            ):
                if f is None:
                    raise ValueError(f'{label} לא נמצא במערכת: "{row[col]}"')

            name_cell = str(row["Name"]).strip() if pd.notna(row["Name"]) else ""
            if not name_cell:
                raise ValueError("יש שורה ללא שם.")
            sem = _student_row_semester(row)
            ppa = (
                str(row["Preferred Practice Area"]).strip()
                if pd.notna(row["Preferred Practice Area"])
                else ""
            )
            if not ppa:
                raise ValueError(f'חסר אזור התמחות מועדף בשורה של "{name_cell}".')

            if sid is not None:
                st = Student.query.get(sid)
                st.name = name_cell
                if _upload_row_has_real_email(row):
                    new_em = str(row["Email"]).strip()
                    taken = (
                        Student.query.filter(
                            db.func.lower(db.func.trim(Student.email))
                            == new_em.lower(),
                            Student.id != st.id,
                        ).first()
                    )
                    if taken:
                        raise ValueError(
                            f'האימייל "{new_em}" כבר שייך לסטודנטית אחרת.'
                        )
                    st.email = new_em
                st.preferred_field_id_1 = f1.id
                st.preferred_field_id_2 = f2.id
                st.preferred_field_id_3 = f3.id
                st.preferred_practice_area = ppa
                st.semester = sem
                matched_ids.add(sid)
            else:
                if _upload_row_has_real_email(row):
                    new_em = str(row["Email"]).strip()
                    if Student.query.filter(
                        db.func.lower(db.func.trim(Student.email)) == new_em.lower()
                    ).first():
                        raise ValueError(
                            f'האימייל "{new_em}" כבר קיים — ייתכן שורה כפולה או סטודנטית קיימת.'
                        )
                    ins_email = new_em
                else:
                    ins_email = generate_unique_student_email()
                st = Student(
                    name=name_cell,
                    email=ins_email,
                    preferred_field_1=f1,
                    preferred_field_2=f2,
                    preferred_field_3=f3,
                    preferred_practice_area=ppa,
                    semester=sem,
                )
                db.session.add(st)
                db.session.flush()
                matched_ids.add(st.id)
                all_students.append(st)
                students_by_id[st.id] = st

        for s in list(Student.query.all()):
            if s.id not in matched_ids:
                Assignment.query.filter_by(student_id=s.id).delete()
                db.session.delete(s)

        db.session.commit()
    except Exception as e:
        flash(str(e), "danger")
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
        
        required_columns = ['Name', 'Practice Location', 'Area of Expertise', 'City', 'Address', 'Phone', 'Email', 'Relevant Semesters', 'Years of Experience', 'Available Days to Assign', 'Max Students Per Day', 'Color', 'Single Assignment', 'Has Contract']
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
                single_assignment=row['Single Assignment'] if 'Single Assignment' in row and not pd.isnull(row['Single Assignment']) else False,
                has_contract=row['Has Contract'] if 'Has Contract' in row and not pd.isnull(row['Has Contract']) else False,
                is_active=row['Is Active'] if 'Is Active' in row and not pd.isnull(row['Is Active']) else True
            )
            db.session.add(new_instructor)
        db.session.commit()
    
    except Exception as e:
        flash(str(e), 'danger')
        db.session.rollback()

@bp.route('/remove_assignment/<int:assignment_id>', methods=['POST']) 
def remove_assignment(assignment_id):
    assignment = Assignment.query.get_or_404(assignment_id)
    instructor = assignment.instructor
    db.session.delete(assignment)
    if instructor and instructor.single_assignment:
        remaining = Assignment.query.filter_by(instructor_id=instructor.id).count()
        if remaining == 0:
            available_days = instructor.available_days_to_assign.split(',')
            restored = [d.replace('-לא-זמין', '').strip() for d in available_days]
            instructor.available_days_to_assign = ','.join(restored)
            db.session.add(instructor)
    db.session.commit()
    return redirect(url_for('main.current_assignments_table'))


@bp.route('/move_assignment', methods=['POST'])
def move_assignment():
    """Move an assignment to another student/day. Body: assignment_id, new_student_id, new_day."""
    assignment_id = request.form.get('assignment_id', type=int)
    new_student_id = request.form.get('new_student_id', type=int)
    new_day = request.form.get('new_day')
    if not assignment_id or not new_student_id or not new_day:
        flash('חסרים פרמטרים להעברה', 'danger')
        return redirect(url_for('main.current_assignments_table'))
    assignment = Assignment.query.get_or_404(assignment_id)
    instructor_id = assignment.instructor_id
    old_student_id = assignment.student_id
    old_day = assignment.assigned_day
    if old_student_id == new_student_id and old_day == new_day:
        return redirect(url_for('main.current_assignments_table'))
    valid, reason = _can_assign_instructor_to_student_day(instructor_id, new_student_id, new_day)
    if not valid:
        flash(reason or 'לא ניתן להעביר לשיבוץ זה', 'danger')
        return redirect(url_for('main.current_assignments_table'))
    instructor = assignment.instructor
    db.session.delete(assignment)
    if instructor and instructor.single_assignment:
        remaining = Assignment.query.filter_by(instructor_id=instructor.id).count()
        if remaining == 0:
            available_days = instructor.available_days_to_assign.split(',')
            restored = [d.replace('-לא-זמין', '').strip() for d in available_days]
            instructor.available_days_to_assign = ','.join(restored)
            db.session.add(instructor)
    new_student = Student.query.get(new_student_id)
    allocation = 'שפה' if new_student.semester == 'א' else 'אודיו ושיקום'
    if allocation == 'אודיו ושיקום':
        Assignment.query.filter_by(student_id=new_student_id).delete()
        existing = Assignment.query.filter_by(student_id=new_student_id, instructor_id=501, assigned_day='ראשון').first()
        if not existing:
            db.session.add(Assignment(student_id=new_student_id, instructor_id=501, assigned_day='ראשון'))
    else:
        Assignment.query.filter_by(student_id=new_student_id, instructor_id=501, assigned_day='ראשון').delete()
        db.session.add(Assignment(student_id=new_student_id, instructor_id=instructor_id, assigned_day=new_day))
        if instructor and instructor.single_assignment:
            available_days = instructor.available_days_to_assign.split(',')
            base_days = [d.replace('-לא-זמין', '').strip() for d in available_days]
            with_suffix = [d if d == new_day else d + '-לא-זמין' for d in base_days]
            instructor.available_days_to_assign = ','.join(with_suffix)
            db.session.add(instructor)
    db.session.commit()
    return redirect(url_for('main.current_assignments_table'))


@bp.route('/assign_direct', methods=['POST'])
def assign_direct():
    """Create an assignment from student_id, instructor_id, assigned_day (e.g. from tooltip one-click)."""
    student_id = request.form.get('student_id', type=int)
    instructor_id = request.form.get('instructor_id', type=int)
    assigned_day = request.form.get('assigned_day')
    if not student_id or not instructor_id or not assigned_day:
        flash('חסרים פרמטרים לשיבוץ', 'danger')
        return redirect(url_for('main.current_assignments_table'))
    student = Student.query.get(student_id)
    if not student:
        flash('סטודנטית לא נמצאה', 'danger')
        return redirect(url_for('main.current_assignments_table'))
    allocation = 'שפה' if student.semester == 'א' else 'אודיו ושיקום'
    if allocation == 'אודיו ושיקום':
        Assignment.query.filter_by(student_id=student_id).delete()
        existing = Assignment.query.filter_by(student_id=student_id, instructor_id=501, assigned_day='ראשון').first()
        if not existing:
            db.session.add(Assignment(student_id=student.id, instructor_id=501, assigned_day='ראשון'))
    elif allocation == 'שפה':
        Assignment.query.filter_by(student_id=student_id, instructor_id=501, assigned_day='ראשון').delete()
        db.session.add(Assignment(student_id=student.id, instructor_id=instructor_id, assigned_day=assigned_day))
        instructor = ClinicalInstructor.query.get(instructor_id)
        if instructor and instructor.single_assignment:
            available_days = instructor.available_days_to_assign.split(',')
            available_days_with_suffix = [d if d == assigned_day else d + '-לא-זמין' for d in available_days]
            instructor.available_days_to_assign = ','.join(available_days_with_suffix)
            db.session.add(instructor)
    db.session.commit()
    return redirect(url_for('main.current_assignments_table'))


@bp.route('/assignments_view')
def assignments_view():
    semester = request.args.get('semester', 'א')  # Default to semester 'א'
    students = Student.query.filter_by(semester=semester).all()
    days_of_week = ['ראשון', 'שני', 'שלישי', 'רביעי', 'חמישי', 'שישי']
    
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
    days_of_week = ['ראשון', 'שני', 'שלישי', 'רביעי', 'חמישי', 'שישי']

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
                    
                    # New has_contract field update
                    instructor.has_contract = instructor_data.get('has_contract', False)  # Default to False if not provided

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
    
    # Fetch students and assignments
    students = Student.query.all()
    assignments = Assignment.query.all()
    
    # Prepare instructor colors dictionary (assuming each instructor has a color field)
    instructors = ClinicalInstructor.query.all()
    instructor_colors = {instructor.name: instructor.color for instructor in instructors}  # Adjust according to your model
    
    student_assignments = {}

    for student in students:
        # Determine allocation based on the student's semester
        allocation = 'שפה' if student.semester == 'א' else 'אודיו ושיקום'
        
        student_assignments[student.id] = {
            'id': student.id,  # Include student_id
            'name': student.name,
            'email': student.email,  # Include the student's email
            'preferred_fields': [
                student.preferred_field_1.name if student.preferred_field_1 else '',
                student.preferred_field_2.name if student.preferred_field_2 else '',
                student.preferred_field_3.name if student.preferred_field_3 else ''
            ],
            'allocation': allocation,
            'assignments': [None, None, None] if allocation == 'שפה' else []
        }

    for assignment in assignments:
        student_id = assignment.student_id
        student_data = student_assignments.get(student_id)
        if student_data and student_data['allocation'] == 'שפה':
            for i, _ in enumerate(student_data['assignments']):
                if student_data['assignments'][i] is None:
                    student_data['assignments'][i] = assignment
                    break

    # Convert dictionary to a list and sort it
    sorted_students = sorted(student_assignments.values(), key=lambda x: (
        x['allocation'] != 'שפה',
        x['allocation'] != 'אודיו ושיקום'
    ))

    # Precompute relevant/irrelevant instructors for all assignable students (one batch, no N+1)
    active_instructors = ClinicalInstructor.query.filter_by(is_active=True).options(
        db.joinedload(ClinicalInstructor.area_of_expertise)
    ).all()
    relevant_instructors_bulk = _build_relevant_instructors_bulk(
        assignments, student_assignments, active_instructors
    )

    return render_template(
        'current_assignments_table.html',
        student_assignments=sorted_students,
        semester=semester,
        instructor_colors=instructor_colors,
        relevant_instructors_bulk=relevant_instructors_bulk,
        gmail_connection=get_gmail_connection_status(),
    )

def determine_allocation(student):
    if student.semester == 'א':
        return 'שפה'
    elif student.semester == 'ב':
        return 'אודיו ושיקום'
    else:
        return None  # Handle unexpected cases if necessary


@bp.route('/api/gmail/connect')
def gmail_connect():
    if not gmail_oauth_configured():
        flash('Gmail OAuth לא מוגדר עדיין. יש להגדיר GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET ו-GOOGLE_REDIRECT_URI.', 'danger')
        return redirect(url_for('main.current_assignments_table'))

    next_url = request.args.get('next') or url_for('main.current_assignments_table')
    if not next_url.startswith('/'):
        next_url = url_for('main.current_assignments_table')
    session['gmail_oauth_next'] = next_url
    redirect_uri = current_app.config.get('GOOGLE_REDIRECT_URI') or url_for('main.gmail_oauth_callback', _external=True)
    code_verifier = new_gmail_oauth_code_verifier()
    session['gmail_oauth_code_verifier'] = code_verifier
    flow = build_gmail_flow(redirect_uri=redirect_uri, code_verifier=code_verifier)
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent',
    )
    session['gmail_oauth_state'] = state
    return redirect(authorization_url)


@bp.route('/api/gmail/callback')
def gmail_oauth_callback():
    expected_state = session.get('gmail_oauth_state')
    received_state = request.args.get('state')
    if not expected_state or expected_state != received_state:
        session.pop('gmail_oauth_code_verifier', None)
        flash('אימות Gmail נכשל. יש לנסות להתחבר מחדש.', 'danger')
        return redirect(url_for('main.current_assignments_table'))

    code_verifier = session.pop('gmail_oauth_code_verifier', None)
    if not code_verifier:
        flash(
            'חסר נתוני אימות OAuth (PKCE). יש ללחוץ שוב על חיבור Gmail.',
            'danger',
        )
        return redirect(url_for('main.current_assignments_table'))

    redirect_uri = current_app.config.get('GOOGLE_REDIRECT_URI') or url_for('main.gmail_oauth_callback', _external=True)
    flow = build_gmail_flow(
        redirect_uri=redirect_uri,
        state=expected_state,
        code_verifier=code_verifier,
    )

    try:
        flow.fetch_token(authorization_response=request.url)
        credentials = flow.credentials
        store_gmail_credentials(credentials)
        account_email = get_gmail_profile_email()
        set_gmail_account_email(account_email)
    except Exception as exc:
        flash(f'לא הצלחנו לחבר את Gmail: {exc}', 'danger')
        return redirect(url_for('main.current_assignments_table'))
    finally:
        session.pop('gmail_oauth_state', None)
        session.pop('gmail_oauth_code_verifier', None)

    next_url = session.pop('gmail_oauth_next', None) or url_for('main.current_assignments_table')
    if not next_url.startswith('/'):
        next_url = url_for('main.current_assignments_table')
    flash('Gmail חובר בהצלחה.', 'success')
    return redirect(next_url)


@bp.route('/api/gmail/disconnect', methods=['POST'])
def gmail_disconnect():
    try:
        revoke_gmail_credentials()
    except Exception:
        clear_gmail_credentials()
    session.pop('gmail_oauth_state', None)
    session.pop('gmail_oauth_code_verifier', None)
    session.pop('gmail_oauth_next', None)
    flash('החיבור ל-Gmail נותק.', 'info')
    return redirect(url_for('main.current_assignments_table'))


@bp.route('/api/send_student_email', methods=['POST'])
def send_student_email():
    """Send rich HTML assignment email to student (RTL, table, header/footer images)."""
    if not gmail_oauth_configured():
        return jsonify({
            'success': False,
            'error': 'Gmail OAuth לא מוגדר. יש להגדיר GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET ו-GOOGLE_REDIRECT_URI.',
        }), 503

    connection = get_gmail_connection_status()
    if not connection.get('connected'):
        return jsonify({
            'success': False,
            'error': 'Gmail עדיין לא מחובר. יש ללחוץ על "חיבור Gmail" ולתת הרשאה.',
            'connect_url': url_for('main.gmail_connect', next=url_for('main.current_assignments_table')),
        }), 503

    data = request.get_json(force=True, silent=True) or {}
    student_id = data.get('student_id')
    if student_id is None:
        return jsonify({'success': False, 'error': 'חסר student_id'}), 400
    student = Student.query.get(student_id)
    if not student:
        return jsonify({'success': False, 'error': 'סטודנט לא נמצא'}), 404
    try:
        html_body, plain_body = get_student_email_html(student)
        subject = f"שיבוץ שפה ודיבור - {student.name}"
        response = send_gmail_message(subject, student.email, plain_body, html_body)
    except RuntimeError as exc:
        message = str(exc)
        status_code = 503 if 'not connected' in message.lower() else 500
        return jsonify({'success': False, 'error': message}), status_code
    except Exception as exc:
        return jsonify({'success': False, 'error': str(exc)}), 500

    return jsonify({
        'success': True,
        'message_id': response.get('id'),
    })


INSTRUCTOR_EMAIL_TEMPLATE_START_KEY = 'instructor_email_template_start'
INSTRUCTOR_EMAIL_TEMPLATE_END_KEY = 'instructor_email_template_end'


def _get_setting(key, default=''):
    row = AppSetting.query.get(key)
    return (row.value if row and row.value is not None else default) or default


def _set_setting(key, value):
    row = AppSetting.query.get(key)
    if row:
        row.value = value
    else:
        db.session.add(AppSetting(key=key, value=value))
    db.session.commit()


@bp.route('/api/instructor_email_template', methods=['GET', 'POST'])
def api_instructor_email_template():
    if request.method == 'GET':
        start = _get_setting(INSTRUCTOR_EMAIL_TEMPLATE_START_KEY)
        end = _get_setting(INSTRUCTOR_EMAIL_TEMPLATE_END_KEY)
        return jsonify({'start': start, 'end': end})
    # POST
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Missing JSON body'}), 400
    start = data.get('start')
    end = data.get('end')
    if start is None and end is None:
        return jsonify({'success': False, 'error': 'Missing start or end'}), 400
    if start is not None:
        _set_setting(INSTRUCTOR_EMAIL_TEMPLATE_START_KEY, str(start))
    if end is not None:
        _set_setting(INSTRUCTOR_EMAIL_TEMPLATE_END_KEY, str(end))
    return jsonify({'success': True})


#########################################
@bp.route('/archive_assignments', methods=['POST'])
def archive_assignments():
    user_snapshot_name = request.form['snapshot_name'].strip()
    if not user_snapshot_name:
        flash("Snapshot name cannot be empty.", "danger")
        return redirect(url_for('main.current_assignments_table'))

    now_str = datetime.now().strftime("%d_%m_%y_%H_%M")
    snapshot_full_name = f"{user_snapshot_name}"#_{now_str}"

    # Create a new ArchivedSnapshot
    snapshot = ArchivedSnapshot(
        snapshot_name=snapshot_full_name,
        created_at=datetime.now()
    )
    db.session.add(snapshot)
    db.session.commit()  # get snapshot.id

    # Gather current assignments (customize as needed if you want to filter)
    students = Student.query.all()
    student_ids = [s.id for s in students]
    assignments = Assignment.query.filter(Assignment.student_id.in_(student_ids)).all()

    # For each current assignment, create an ArchivedAssignment row
    for assignment in assignments:
        student = assignment.student
        instructor = assignment.instructor

        field_name = ""
        if instructor and instructor.area_of_expertise:
            field_name = instructor.area_of_expertise.name

        archived_row = ArchivedAssignment(
            snapshot_id=snapshot.id,
            assigned_day=assignment.assigned_day,
            
            # We removed 'year_semester' references entirely.
            # If your ArchivedAssignment still has a year_semester column, 
            # you can set it to a default or remove the column from the model.

            student_name=student.name,
            student_email=student.email,
            preferred_practice_area=student.preferred_practice_area,

            instructor_name=instructor.name if instructor else "N/A",
            instructor_practice_location=instructor.practice_location if instructor else "N/A",
            instructor_field_name=field_name
        )
        db.session.add(archived_row)

    db.session.commit()

    flash(f"Archived {len(assignments)} assignments under '{snapshot_full_name}'.", "success")
    return redirect(url_for('main.current_assignments_table'))


@bp.route('/clear_assignments', methods=['POST'])
def clear_assignments():
    try:
        Assignment.query.delete()
        db.session.commit()
        flash("כל השיבוצים נמחקו מהמערכת.", "success")
    except Exception:
        db.session.rollback()
        flash("ארעה שגיאה בעת מחיקת השיבוצים.", "danger")
    return redirect(url_for('main.current_assignments_table'))


@bp.route('/historic_assignments')
def historic_assignments():
    snapshots = ArchivedSnapshot.query.order_by(ArchivedSnapshot.created_at.desc()).all()
    
    snapshot_id = request.args.get('snapshot_id')
    selected_snapshot = None
    archived_assignments = []
    
    if snapshot_id:
        selected_snapshot = ArchivedSnapshot.query.get(snapshot_id)
        if selected_snapshot:
            archived_assignments = selected_snapshot.assignments
        else:
            flash("Snapshot not found.", "danger")
    
    grouped_by_student = {}

    for arch in archived_assignments:
        sname = arch.student_name
        if sname not in grouped_by_student:
            # We can skip the "allocation" logic since we removed year_semester
            # or just default to 'שפה' or something generic:
            allocation = "שפה"
            
            grouped_by_student[sname] = {
                'name': arch.student_name,
                'email': arch.student_email,
                'preferred_fields': ["?", "?", "?"],  # or omit entirely
                'allocation': allocation,
                'assignments': []
            }
        
        # Attempt to find the current instructor by name
        instructor_obj = None
        if arch.instructor_name:
            instructor_obj = ClinicalInstructor.query.filter_by(name=arch.instructor_name).first()
        
        color_to_use = instructor_obj.color if instructor_obj else "gray"

        grouped_by_student[sname]['assignments'].append({
            'assigned_day': arch.assigned_day,
            'instructor': {
                'name': arch.instructor_name,
                'practice_location': arch.instructor_practice_location,
                'color': color_to_use
            }
        })
    
    archived_student_assignments = list(grouped_by_student.values())
    archived_student_assignments.sort(
    key=lambda student: student['name'].split()[0]
)

    return render_template(
        'historic_assignments_table.html',
        snapshots=snapshots,
        selected_snapshot=selected_snapshot,
        archived_student_assignments=archived_student_assignments
    )
