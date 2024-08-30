from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Image, Spacer
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.units import inch
import io
import re

# Register the font
pdfmetrics.registerFont(TTFont('FreeSans', 'fonts/FreeSans.ttf'))

def reverse_text(text):
    """Reverse the text for proper RTL display, but not for numbers."""
    return text[::-1]

def format_phone_number(phone):
    """Ensure the phone number has a hyphen after the first three digits."""
    if re.match(r'^\d{3}-\d{7}$', phone):
        return phone
    elif re.match(r'^\d{10}$', phone):
        return f"{phone[:3]}-{phone[3:]}"
    else:
        return phone  # Return the original if it doesn't match expected formats

def generate_student_pdf(student):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=A4,
        title=f"שיבוצים שפה ודיבור{student.name}",
        author="רון דאר",
        subject="שיבוצים שפה ודיבור"
    )

    elements = []
    styles = getSampleStyleSheet()

    # Define a Hebrew paragraph style using the registered font
    hebrew_style = ParagraphStyle('hebrew', fontName='FreeSans', fontSize=12, alignment=1)

    # Page width in points
    page_width = A4[0]

    # Header Image - 80% of the page's width
    header = Image("logos/header.png")
    header_width = 0.8 * page_width
    header_height = header_width * header.imageHeight / header.imageWidth  # Maintain aspect ratio
    header.drawWidth = header_width
    header.drawHeight = header_height
    elements.append(header)

    # Spacer between header and title
    elements.append(Spacer(1, 40))

    # Title
    title = Paragraph(reverse_text("שיבוץ התנסות מעשית בשפה ודיבור"), hebrew_style)
    student_name = Paragraph(reverse_text(f"{student.name}"), hebrew_style)
    elements.append(title)
    elements.append(Spacer(1, 6))
    elements.append(student_name)

    # Spacer between title and table
    elements.append(Spacer(1, 40))

    # Table Data - headers with correct RTL display
    data = [
        [reverse_text("פרטי התקשרות"), reverse_text("קלינאית מדריכה"), reverse_text("מקום התנסות"), reverse_text("תאריך התחלה"), reverse_text("יום התנסות")],
    ]

    # Populating table with student's assignment data
    for assignment in student.assignments:
        instructor = assignment.instructor
        instructor_name = reverse_text(instructor.name) if instructor else ""
        contact_info = format_phone_number(instructor.phone) if instructor else ""  # Format the phone number
        place = reverse_text(instructor.practice_location) if instructor else ""
        start_date = reverse_text(assignment.assigned_day)
        day = reverse_text(assignment.assigned_day)

        data.append([contact_info, instructor_name, place, start_date, day])

    # Creating the table with the data
    table = Table(data, colWidths=[100, 100, 100, 100, 100])
    table.setStyle(TableStyle([
        # Header background color
        ('BACKGROUND', (0, 0), (-1, 0), colors.Color(red=63/255, green=64/255, blue=66/255, alpha=1.0)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'FreeSans'),  # Ensure the font is set for the entire table
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        # Row background colors alternating - 1st and 3rd rows the same
        ('BACKGROUND', (0, 1), (-1, 1), colors.Color(red=100/255, green=206/255, blue=221/255, alpha=1.0)),
        ('BACKGROUND', (0, 2), (-1, 2), colors.Color(red=242/255, green=250/255, blue=250/255, alpha=1.0)),
        ('BACKGROUND', (0, 3), (-1, 3), colors.Color(red=100/255, green=206/255, blue=221/255, alpha=1.0)),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))

    elements.append(table)

    # Spacer between table and footer
    elements.append(Spacer(1, 200))

    # Footer Image - 65% of the page's width
    footer = Image("logos/footer.png")
    footer_width = 0.65 * page_width
    footer_height = footer_width * footer.imageHeight / footer.imageWidth  # Maintain aspect ratio
    footer.drawWidth = footer_width
    footer.drawHeight = footer_height
    elements.append(footer)

    # Build the PDF document
    doc.build(elements)
    buffer.seek(0)
    return buffer
