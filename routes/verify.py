"""
Public certificate verification (no login required).

  GET/POST /verify              → search by Certificate ID + DOB
  GET      /verify/<id>         → QR scan / direct link
  GET      /verify/qr/<file>    → serve QR image for download
"""
import os
from flask import (
    Blueprint,
    render_template,
    request,
    current_app,
    send_from_directory,
    abort,
)
from database.models import (
    get_certificate_by_certificate_id,
    get_certificate_by_certificate_id_and_dob,
    get_certificate_by_id_or_no,  # add this line
)

verify_bp = Blueprint("verify", __name__)


def _row_get(row, key, default=""):
    if row is None:
        return default
    try:
        if hasattr(row, "keys") and key in row.keys():
            val = row[key]
            return default if val is None else val
    except Exception:
        pass
    if isinstance(row, dict):
        return row.get(key, default) or default
    return default


def _normalize_dob(value):
    """Accept DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD → compare loosely."""
    if not value:
        return ""
    v = value.strip().replace("-", "/").replace(".", "/")
    return v


def _dob_matches(stored, entered):
    if not entered:
        return True
    s = _normalize_dob(stored)
    e = _normalize_dob(entered)
    if s == e:
        return True
    # also try swapping day/month ambiguity if needed
    return s.replace("/", "") == e.replace("/", "")


def _cert_view(certificate):
    if certificate is None:
        return None
    student = (
        _row_get(certificate, "student_name")
        or _row_get(certificate, "name")
        or ""
    )
    course = (
        _row_get(certificate, "course_name_snapshot")
        or _row_get(certificate, "course_name")
        or ""
    )
    contact = (
        _row_get(certificate, "contact_no")
        or ""
    )
    return {
        "certificate_id": _row_get(certificate, "certificate_id"),
        "student_name": student,
        "email": _row_get(certificate, "email", ""),
        "date_of_birth": _row_get(certificate, "date_of_birth", ""),
        "contact": contact,
        "course_name": course,
        "organization_name": _row_get(certificate, "organization_name", "ODS Maritime Academy Foundation"),
        "held_from": _row_get(certificate, "held_from", ""),
        "held_to": _row_get(certificate, "held_to", ""),
        "issue_date": _row_get(certificate, "issue_date", ""),
        "passport_no": _row_get(certificate, "passport_no", ""),
        "cdc_no": _row_get(certificate, "cdc_no", ""),
        "indos_no": _row_get(certificate, "indos_no", ""),
        "status": _row_get(certificate, "status", "Generated"),
        "qr_code": _row_get(certificate, "qr_code", ""),
        "captain_name": _row_get(certificate, "captain_name", ""),
    }


@verify_bp.route("/verify", methods=["GET", "POST"])
def verify_search():
    error = None
    cert = None

    if request.method == "POST":
        certificate_id = request.form.get("certificate_id", "").strip()
        date_of_birth = request.form.get("date_of_birth", "").strip()

        if not certificate_id:
            error = "Please enter a Certificate ID."
            return render_template("verify_search.html", error=error, cert=None)

        row = get_certificate_by_id_or_no(certificate_id)
        if row is None:
            error = "No certificate found for that Certificate ID / Certificate No."
            return render_template("verify_search.html", error=error, cert=None)

        if date_of_birth:
            stored_dob = _row_get(row, "date_of_birth", "")
            if not _dob_matches(stored_dob, date_of_birth):
                error = "No certificate found for that Certificate ID and Date of Birth."
                return render_template("verify_search.html", error=error, cert=None)

        cert = _cert_view(row)
        return render_template("verify_search.html", error=None, cert=cert)
    return render_template("verify_search.html", error=None, cert=None)


@verify_bp.route("/verify/<path:certificate_id>")
def verify_certificate(certificate_id):
    """Opened when QR is scanned (or direct link)."""
    row = get_certificate_by_certificate_id(certificate_id)
    cert = _cert_view(row)
    return render_template(
        "verify_result.html",
        certificate=cert,
        certificate_id=certificate_id,
        found=cert is not None,
    )


@verify_bp.route("/verify/qr/<path:filename>")
def qr_image(filename):
    folder = current_app.config.get("QR_FOLDER") or current_app.config.get(
        "GENERATED_FOLDER", ""
    )
    path = os.path.join(folder, filename)
    if not os.path.exists(path):
        abort(404)
    return send_from_directory(folder, filename)