import os
from dotenv import load_dotenv

load_dotenv()

# Absolute path to the project's root folder
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Where uploaded certificate templates get stored
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads", "templates")

# Only these file types are allowed to be uploaded
ALLOWED_EXTENSIONS = {"svg", "png", "jpg", "jpeg", "pdf", "docx", "pptx"}

# Max upload size: 5 MB (in bytes)
MAX_CONTENT_LENGTH = 5 * 1024 * 1024

# Default text positions on a certificate template (x, y) in pixels.
# Open your template file in an image editor (e.g. Paint, Photoshop) and
# hover your mouse over where you want each text to appear to find these values.
CERTIFICATE_TEXT_POSITIONS = {
    "name": {
        "cover_box": (120, 160, 410, 222),
        "text_position": (135, 178)
    },
    "event": {
        "cover_box": (55, 222, 480, 270),
        "text_position": (65, 235)
    },
    "date": {
        "cover_box": (65, 285, 230, 332),
        "text_position": (65, 300)
    },
    "certificate_id": {
        "cover_box": (335, 335, 480, 368),
        "text_position": (340, 345)
    },
}

CERTIFICATE_FONT_SIZE = 15

QR_CODE_POSITION = (440, 20)   # top-right corner-ish; adjust after previewing
QR_CODE_SIZE = 80

GENERATED_FOLDER = os.path.join(BASE_DIR, "generated_certificates")
GENERATED_SVG_FOLDER = os.path.join(BASE_DIR, "generated_certificates", "svg")
GENERATED_PNG_FOLDER = os.path.join(BASE_DIR, "generated_certificates", "png")

SECRET_KEY = os.environ.get("SECRET_KEY")

SITE_BASE_URL = "https://your-real-domain.com"

# Printed Certificate No is typed by admin.
# certificate_id stays auto for QR /verify/<id>

CERT_ID_ORG_CODE = "ODS"
CERT_ID_TYPE_CODE = "STCW"

# Default field boxes for the standard ODS blank (tune in Templates → Positions)
# Keys match field_data / Positions editor.
# Each dict mimics a DB row: field_key, x, y, width, height, font_size, font_family, color, align, bold, italic, underline
DEFAULT_ODS_FIELD_POSITIONS = [
    {"field_key": "certificate_no", "x": 900, "y": 55, "width": 220, "height": 28, "font_size": 14, "font_family": "Arial", "color": "#111111", "align": "right", "bold": 1, "italic": 0, "underline": 0},
    {"field_key": "student_name", "x": 220, "y": 320, "width": 420, "height": 30, "font_size": 16, "font_family": "Arial", "color": "#111111", "align": "left", "bold": 1, "italic": 0, "underline": 0},
    {"field_key": "date_of_birth", "x": 920, "y": 320, "width": 160, "height": 28, "font_size": 14, "font_family": "Arial", "color": "#111111", "align": "left", "bold": 0, "italic": 0, "underline": 0},
    {"field_key": "cdc_no", "x": 220, "y": 360, "width": 280, "height": 28, "font_size": 14, "font_family": "Arial", "color": "#111111", "align": "left", "bold": 0, "italic": 0, "underline": 0},
    {"field_key": "passport_no", "x": 700, "y": 360, "width": 220, "height": 28, "font_size": 14, "font_family": "Arial", "color": "#111111", "align": "left", "bold": 0, "italic": 0, "underline": 0},
    {"field_key": "competency_grade", "x": 320, "y": 400, "width": 200, "height": 28, "font_size": 14, "font_family": "Arial", "color": "#111111", "align": "left", "bold": 0, "italic": 0, "underline": 0},
    {"field_key": "competency_no", "x": 700, "y": 400, "width": 180, "height": 28, "font_size": 14, "font_family": "Arial", "color": "#111111", "align": "left", "bold": 0, "italic": 0, "underline": 0},
    {"field_key": "indos_no", "x": 320, "y": 440, "width": 220, "height": 28, "font_size": 14, "font_family": "Arial", "color": "#111111", "align": "left", "bold": 0, "italic": 0, "underline": 0},
    {"field_key": "course_name", "x": 180, "y": 520, "width": 840, "height": 100, "font_size": 15, "font_family": "Arial", "color": "#111111", "align": "center", "bold": 1, "italic": 0, "underline": 0},
    {"field_key": "held_from", "x": 180, "y": 640, "width": 140, "height": 28, "font_size": 13, "font_family": "Arial", "color": "#111111", "align": "left", "bold": 0, "italic": 0, "underline": 0},
    {"field_key": "held_to", "x": 380, "y": 640, "width": 140, "height": 28, "font_size": 13, "font_family": "Arial", "color": "#111111", "align": "left", "bold": 0, "italic": 0, "underline": 0},
    {"field_key": "description_below", "x": 100, "y": 700, "width": 1000, "height": 120, "font_size": 11, "font_family": "Arial", "color": "#222222", "align": "left", "bold": 0, "italic": 0, "underline": 0},
    {"field_key": "issue_date", "x": 100, "y": 1450, "width": 160, "height": 28, "font_size": 13, "font_family": "Arial", "color": "#111111", "align": "left", "bold": 0, "italic": 0, "underline": 0},
]

QR_FOLDER = os.path.join(BASE_DIR, "generated_certificates", "qr_codes")