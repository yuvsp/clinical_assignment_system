"""
Rich HTML email builder for student assignment emails.
RTL-aligned, table and header/footer images (base64), matching PDF look.
"""
import base64
import os
from flask import current_app

from app.pdf_utils import format_phone_number, get_student_email_body


def _logos_dir():
    """Project root dir where logos/ lives (same as pdf_utils)."""
    app_dir = current_app.root_path
    return os.path.join(os.path.dirname(app_dir), "logos")


def _image_base64(path):
    """Read image file and return data URI for use in img src."""
    if not os.path.isfile(path):
        return ""
    with open(path, "rb") as f:
        data = f.read()
    b64 = base64.b64encode(data).decode("ascii")
    ext = os.path.splitext(path)[1].lower()
    mime = "image/png" if ext == ".png" else "image/jpeg"
    return f"data:{mime};base64,{b64}"


def get_student_email_html(student):
    """
    Build rich HTML email body for a student: RTL, header/footer images (base64),
    table with same columns as PDF, modern styling.
    Returns (html_string, plain_text_string) for multipart/alternative.
    """
    logos = _logos_dir()
    header_b64 = _image_base64(os.path.join(logos, "header.png"))
    footer_b64 = _image_base64(os.path.join(logos, "footer.png"))

    name_parts = student.name.strip().split()
    first_name = name_parts[-1] if name_parts else student.name

    # Table rows: header + one row per assignment (RTL-friendly visual order)
    header_row = """
    <tr style="background-color:#182738;color:#f5f5f5;">
      <th style="padding:12px 8px;text-align:center;font-size:14px;border:1px solid #333;">יום התנסות</th>
      <th style="padding:12px 8px;text-align:center;font-size:14px;border:1px solid #333;">מקום התנסות</th>
      <th style="padding:12px 8px;text-align:center;font-size:14px;border:1px solid #333;">קלינאית מדריכה</th>
      <th style="padding:12px 8px;text-align:center;font-size:14px;border:1px solid #333;">פרטי התקשרות</th>
    </tr>"""

    data_rows = []
    for i, assignment in enumerate(student.assignments or []):
        instructor = assignment.instructor
        contact = format_phone_number(instructor.phone) if instructor else ""
        instructor_name = instructor.name if instructor else ""
        place = instructor.practice_location if instructor else ""
        day = assignment.assigned_day or ""
        # Alternating: row 0,2 -> #ffc151; row 1 -> #ffcd73
        bg = "#ffc151" if i % 2 == 0 else "#ffcd73"
        data_rows.append(
            f"""
    <tr style="background-color:{bg};">
      <td style="padding:10px 8px;text-align:center;border:1px solid #333;">{_h(day)}</td>
      <td style="padding:10px 8px;text-align:center;border:1px solid #333;">{_h(place)}</td>
      <td style="padding:10px 8px;text-align:center;border:1px solid #333;">{_h(instructor_name)}</td>
      <td style="padding:10px 8px;text-align:center;border:1px solid #333;">{_h(contact)}</td>
    </tr>"""
        )

    table_body = header_row + "\n".join(data_rows)
    if not data_rows:
        table_body += """
    <tr><td colspan="4" style="padding:12px;text-align:center;border:1px solid #333;">אין שיבוצים כרגע.</td></tr>"""

    header_img = ""
    if header_b64:
        header_img = f'<img src="{header_b64}" alt="" style="max-width:100%;height:auto;display:block;" />'
    footer_img = ""
    if footer_b64:
        footer_img = f'<img src="{footer_b64}" alt="" style="max-width:65%;height:auto;display:block;margin-top:24px;" />'

    html = f"""<!DOCTYPE html>
<html dir="rtl" lang="he">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
</head>
<body style="margin:0;padding:20px;font-family:Arial,sans-serif;font-size:14px;direction:rtl;text-align:right;max-width:600px;">
  <div style="max-width:100%;">
    {header_img}
    <div style="margin-top:24px;">
      <h2 style="margin:0 0 6px 0;font-size:18px;">שיבוץ התנסות מעשית בשפה ודיבור</h2>
    </div>
    <p style="margin:16px 0 8px 0;">שלום {_h(first_name)},</p>
    <table style="width:100%;border-collapse:collapse;margin:24px 0;">
      {table_body}
    </table>
    <p style="margin:24px 0 8px 0;">13 ימי התנסות בכל מקום. בכל אחד מהמקומות יש ליצור קשר טלפוני עם הקלינאית המדריכה כשבוע לפני מועד ההתחלה, לשם קבלת מידע ראשוני לגבי ההתנסות.</p>
    <p style="margin:0 0 8px 0;">שיהיה בהצלחה,<br />רון</p>
    {footer_img}
  </div>
</body>
</html>"""

    plain = get_student_email_body(student)
    return html, plain


def _h(s):
    """Escape for HTML text content."""
    if s is None:
        return ""
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
