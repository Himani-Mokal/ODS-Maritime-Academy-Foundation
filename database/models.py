from database.db import get_connection
from datetime import datetime


# ======================================
# COURSE FUNCTIONS
# ======================================

def get_all_courses():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM courses ORDER BY course_date DESC")
    courses = cursor.fetchall()
    conn.close()
    return courses


def get_course_by_id(course_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM courses WHERE id=?", (course_id,))
    course = cursor.fetchone()
    conn.close()
    return course


def create_course(course_name, course_date, organizer, venue, description, template_name, status, template_id=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO courses(course_name, course_date, organizer, venue, description, template_name, status, template_id)
        VALUES(?,?,?,?,?,?,?,?)
    """, (course_name, course_date, organizer, venue, description, template_name, status, template_id))
    conn.commit()
    conn.close()


def update_course(course_id, course_name, course_date, organizer, venue, description, template_name, status, template_id=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE courses SET course_name=?, course_date=?, organizer=?, venue=?,
        description=?, template_name=?, status=?, template_id=? WHERE id=?
    """, (course_name, course_date, organizer, venue, description, template_name, status, template_id, course_id))
    conn.commit()
    conn.close()


def get_courses_by_template(template_id):
    """All courses currently assigned to a given template."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, course_name FROM courses WHERE template_id=?", (template_id,))
    courses = cursor.fetchall()
    conn.close()
    return courses


def delete_course(course_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM courses WHERE id=?", (course_id,))
    conn.commit()
    conn.close()


def search_courses(keyword):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM courses
        WHERE course_name LIKE ? OR organizer LIKE ? OR venue LIKE ?
        ORDER BY course_date DESC
    """, (f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"))
    courses = cursor.fetchall()
    conn.close()
    return courses


# ======================================
# CERTIFICATE TEMPLATE FUNCTIONS
# ======================================

def create_template(template_name, file_name, uploaded_at, status,
                     template_type="svg", description=""):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO certificate_templates
            (template_name, file_name, uploaded_at, status, template_type, description, updated_at)
        VALUES(?,?,?,?,?,?,?)
    """, (template_name, file_name, uploaded_at, status, template_type, description, uploaded_at))
    conn.commit()
    template_id = cursor.lastrowid
    conn.close()
    return template_id


def get_all_templates(search=None, status=None, template_type=None):
    conn = get_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM certificate_templates WHERE 1=1"
    params = []

    if search:
        query += " AND (template_name LIKE ? OR description LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])

    if status:
        query += " AND status = ?"
        params.append(status)

    if template_type:
        query += " AND template_type = ?"
        params.append(template_type)

    query += " ORDER BY uploaded_at DESC"

    cursor.execute(query, params)
    templates = cursor.fetchall()
    conn.close()
    return templates


def get_template_by_id(template_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM certificate_templates WHERE id=?", (template_id,))
    template = cursor.fetchone()
    conn.close()
    return template


def get_template_by_name(template_name):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM certificate_templates WHERE template_name=?", (template_name,))
    template = cursor.fetchone()
    conn.close()
    return template


def update_template(template_id, template_name, description, status,
                     updated_at, file_name=None):
    conn = get_connection()
    cursor = conn.cursor()

    if file_name:
        cursor.execute("""
            UPDATE certificate_templates
            SET template_name=?, description=?, status=?, file_name=?, updated_at=?
            WHERE id=?
        """, (template_name, description, status, file_name, updated_at, template_id))
    else:
        cursor.execute("""
            UPDATE certificate_templates
            SET template_name=?, description=?, status=?, updated_at=?
            WHERE id=?
        """, (template_name, description, status, updated_at, template_id))

    conn.commit()
    conn.close()


def delete_template(template_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM certificate_templates WHERE id=?", (template_id,))
    conn.commit()
    conn.close()


# ======================================
# TEMPLATE FIELD POSITION FUNCTIONS
# ======================================

def get_field_positions_for_template(template_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM template_field_positions WHERE template_id=? ORDER BY id",
        (template_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def save_field_position(template_id, field_key, x, y, width, height,
                         font_size=20, font_family="Arial, Helvetica, sans-serif",
                         color="#111111", align="left", bold=False, italic=False,
                         underline=False, is_rich=False):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO template_field_positions
            (template_id, field_key, x, y, width, height, font_size, font_family,
             color, align, bold, italic, underline, is_rich)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(template_id, field_key) DO UPDATE SET
            x=excluded.x, y=excluded.y, width=excluded.width, height=excluded.height,
            font_size=excluded.font_size, font_family=excluded.font_family,
            color=excluded.color, align=excluded.align, bold=excluded.bold,
            italic=excluded.italic, underline=excluded.underline, is_rich=excluded.is_rich
    """, (
        template_id, field_key, x, y, width, height, font_size, font_family,
        color, align, int(bool(bold)), int(bool(italic)), int(bool(underline)), int(bool(is_rich))
    ))
    conn.commit()
    conn.close()


def delete_field_positions_for_template(template_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM template_field_positions WHERE template_id=?", (template_id,))
    conn.commit()
    conn.close()


# ======================================
# PARTICIPANT FUNCTIONS
# ======================================

def create_participant(course_id, name, email, college, department, position, created_at,
                       contact_no="", certificate_no="", date_of_birth="", cdc_no="",
                       passport_no="", competency_grade="", competency_no="", indos_no="",
                       held_from="", held_to="", issue_day_month="", issue_year="",
                       course_name_text="", description_below="", qr_label=""):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO participants(
            course_id, name, email, college, department, position, created_at,
            contact_no, certificate_no, date_of_birth, cdc_no, passport_no,
            competency_grade, competency_no, indos_no, held_from, held_to,
            issue_day_month, issue_year, course_name_text, description_below, qr_label
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        course_id, name, email, college or "", department or "", position or "", created_at,
        contact_no or "", certificate_no or "", date_of_birth or "", cdc_no or "",
        passport_no or "", competency_grade or "", competency_no or "", indos_no or "",
        held_from or "", held_to or "", issue_day_month or "", issue_year or "",
        course_name_text or "", description_below or "", qr_label or "",
    ))
    conn.commit()
    pid = cursor.lastrowid
    conn.close()
    return pid


def update_participant(participant_id, **fields):
    """Update any subset of participant columns."""
    allowed = {
        "course_id", "name", "email", "college", "department", "position", "contact_no",
        "certificate_no", "date_of_birth", "cdc_no", "passport_no", "competency_grade",
        "competency_no", "indos_no", "held_from", "held_to", "issue_day_month", "issue_year",
        "course_name_text", "description_below", "qr_label",
    }
    updates = []
    params = []
    for k, v in fields.items():
        if k in allowed:
            updates.append(f"{k}=?")
            params.append(v if v is not None else "")
    if not updates:
        return
    params.append(participant_id)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"UPDATE participants SET {', '.join(updates)} WHERE id=?", params)
    conn.commit()
    conn.close()


def get_all_participants():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT participants.*, courses.course_name, courses.template_name
        FROM participants
        JOIN courses ON participants.course_id = courses.id
        ORDER BY participants.id DESC
    """)
    participants = cursor.fetchall()
    conn.close()
    return participants


def get_participant_by_id(participant_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT participants.*, courses.course_name, courses.template_name
        FROM participants
        JOIN courses ON participants.course_id = courses.id
        WHERE participants.id=?
    """, (participant_id,))
    participant = cursor.fetchone()
    conn.close()
    return participant


def get_participants_by_course(course_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT participants.*, courses.course_name, courses.template_name
        FROM participants
        JOIN courses ON participants.course_id = courses.id
        WHERE participants.course_id = ?
    """, (course_id,))
    participants = cursor.fetchall()
    conn.close()
    return participants


def delete_participant(participant_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM participants WHERE id=?", (participant_id,))
    conn.commit()
    conn.close()


# ======================================
# CERTIFICATE FUNCTIONS
# ======================================

def create_certificate(participant_id, certificate_id, file_name, issue_date, status,
                        qr_code=None, details=None):
    details = details or {}
    detail_keys = [
        "student_name", "captain_name", "organization_name",
        "description_above", "description_below", "date_of_birth",
        "held_from", "held_to", "passport_no", "cdc_no", "indos_no",
        "competency_grade", "course_name_snapshot"
    ]

    conn = get_connection()
    cursor = conn.cursor()
    columns = ["participant_id", "certificate_id", "file_name", "issue_date", "status", "qr_code"] + detail_keys
    values = [participant_id, certificate_id, file_name, issue_date, status, qr_code] + [details.get(k) for k in detail_keys]
    placeholders = ",".join(["?"] * len(columns))
    cursor.execute(
        f"INSERT INTO certificates({','.join(columns)}) VALUES({placeholders})",
        values
    )
    conn.commit()
    cert_row_id = cursor.lastrowid
    conn.close()
    return cert_row_id


def certificate_id_exists(certificate_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM certificates WHERE certificate_id=?", (certificate_id,))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists


def count_certificates_for_year(year_str):
    """Count certificates whose ID ends with /YYYY (for sequence numbers)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM certificates WHERE certificate_id LIKE ?",
        (f"%/{year_str}",)
    )
    count = cursor.fetchone()[0]
    conn.close()
    return count


def get_next_certificate_id():
    """Builds next ID like ODS/STCW/0118/2026."""
    import os
    year = datetime.now().strftime("%Y")
    seq = count_certificates_for_year(year) + 1
    org = os.environ.get("CERT_ID_ORG_CODE", "ODS")
    typ = os.environ.get("CERT_ID_TYPE_CODE", "STCW")
    try:
        from flask import current_app
        org = current_app.config.get("CERT_ID_ORG_CODE", org)
        typ = current_app.config.get("CERT_ID_TYPE_CODE", typ)
    except Exception:
        pass
    return f"{org}/{typ}/{seq:04d}/{year}"


def get_certificate_by_certificate_id_and_dob(certificate_id, date_of_birth):
    """Student verification: Certificate ID + Date of Birth."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            certificates.*,
            participants.name,
            participants.email,
            participants.contact_no,       
            courses.course_name,
            courses.organizer
        FROM certificates
        JOIN participants ON certificates.participant_id = participants.id
        JOIN courses ON participants.course_id = courses.id
        WHERE certificates.certificate_id = ? AND certificates.date_of_birth = ?
    """, (certificate_id, date_of_birth))
    certificate = cursor.fetchone()
    conn.close()
    return certificate


def get_all_certificates():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT certificates.*, participants.name, participants.email
        FROM certificates
        JOIN participants ON certificates.participant_id = participants.id
        ORDER BY certificates.id DESC
    """)
    certs = cursor.fetchall()
    conn.close()
    return certs


def get_certificate_by_certificate_id(certificate_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            certificates.*,
            participants.name,
            participants.email,
            participants.contact_no,       
            participants.college,
            participants.department,
            participants.position,
            courses.course_name,
            courses.organizer,
            courses.course_date
        FROM certificates
        JOIN participants ON certificates.participant_id = participants.id
        JOIN courses ON participants.course_id = courses.id
        WHERE certificates.certificate_id = ?
    """, (certificate_id,))
    certificate = cursor.fetchone()
    conn.close()
    return certificate


def update_certificate_status(certificate_id, status):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE certificates SET status=? WHERE certificate_id=?", (status, certificate_id))
    conn.commit()
    conn.close()


def update_certificate_export_files(certificate_id, svg_file_name=None, png_file_name=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE certificates SET svg_file_name=?, png_file_name=? WHERE certificate_id=?",
        (svg_file_name, png_file_name, certificate_id)
    )
    conn.commit()
    conn.close()


def get_certificate_by_id(cert_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM certificates WHERE id=?", (cert_id,))
    cert = cursor.fetchone()
    conn.close()
    return cert


def get_certificates_by_participant(participant_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM certificates WHERE participant_id=?", (participant_id,))
    certs = cursor.fetchall()
    conn.close()
    return certs


def delete_certificate_row(cert_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM certificates WHERE id=?", (cert_id,))
    conn.commit()
    conn.close()


def delete_certificates_by_participant(participant_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM certificates WHERE participant_id=?", (participant_id,))
    conn.commit()
    conn.close()


def delete_all_certificate_rows():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM certificates")
    conn.commit()
    conn.close()

def get_certificate_by_id_or_no(certificate_id_or_no):
    """Find by auto certificate_id OR printed certificate no (stored in captain_name)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            certificates.*,
            participants.name,
            participants.email,
            participants.contact_no,
            courses.course_name,
            courses.organizer
        FROM certificates
        LEFT JOIN participants ON certificates.participant_id = participants.id
        LEFT JOIN courses ON participants.course_id = courses.id
        WHERE certificates.certificate_id = ?
           OR certificates.captain_name = ?
        LIMIT 1
    """, (certificate_id_or_no, certificate_id_or_no))
    row = cursor.fetchone()
    conn.close()
    return row

# ======================================
# DASHBOARD / REPORTING FUNCTIONS
# ======================================

def get_dashboard_stats():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM participants")
    total_participants = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM certificates")
    total_certificates = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM certificates WHERE status = 'Generated'")
    generated_count = cursor.fetchone()[0]

    conn.close()

    return {
        "total_participants": total_participants,
        "total_certificates": total_certificates,
        "generated_count": generated_count
    }


def get_course_reports():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM courses ORDER BY course_date DESC")
    course_list = cursor.fetchall()

    reports = []
    for course in course_list:
        cursor.execute("SELECT COUNT(*) FROM participants WHERE course_id=?", (course["id"],))
        participant_count = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*) FROM certificates
            JOIN participants ON certificates.participant_id = participants.id
            WHERE participants.course_id=?
        """, (course["id"],))
        certificate_count = cursor.fetchone()[0]

        reports.append({
            "course_name": course["course_name"],
            "course_date": course["course_date"],
            "participant_count": participant_count,
            "certificate_count": certificate_count
        })

    conn.close()
    return reports


def get_recent_certificates(limit=5):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT certificates.*, participants.name, participants.email
        FROM certificates
        JOIN participants ON certificates.participant_id = participants.id
        ORDER BY certificates.id DESC
        LIMIT ?
    """, (limit,))
    certs = cursor.fetchall()
    conn.close()
    return certs


# ======================================
# ADMIN FUNCTIONS
# ======================================

def get_admin_by_username(username):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM admins WHERE username = ?", (username,))
    admin = cursor.fetchone()
    conn.close()
    return admin


def get_admin_by_id(admin_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM admins WHERE id=?", (admin_id,))
    admin = cursor.fetchone()
    conn.close()
    return admin


def create_admin(username, email, password_hash, created_at):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO admins(username, email, password, created_at) VALUES(?,?,?,?)",
        (username, email, password_hash, created_at),
    )
    conn.commit()
    conn.close()


def update_admin_password(admin_id, new_password_hash):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE admins SET password=? WHERE id=?", (new_password_hash, admin_id))
    conn.commit()
    conn.close()


def update_admin_profile(admin_id, username=None, email=None, profile_pic=None):
    """Update admin profile (username, email, or profile picture)."""
    conn = get_connection()
    cursor = conn.cursor()

    updates = []
    params = []

    if username is not None:
        updates.append("username = ?")
        params.append(str(username).strip())
    if email is not None:
        updates.append("email = ?")
        params.append(str(email).strip())
    if profile_pic is not None:
        updates.append("profile_pic = ?")
        params.append(profile_pic)

    if updates:
        query = f"UPDATE admins SET {', '.join(updates)} WHERE id = ?"
        params.append(admin_id)
        cursor.execute(query, params)
        conn.commit()

    conn.close()