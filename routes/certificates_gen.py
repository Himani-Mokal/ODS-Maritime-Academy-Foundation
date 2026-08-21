"""
Certificate generation – PyMuPDF stamping with Template Designer / ODS_ABS_LAYOUT positions.
"""
import os
import re
from datetime import datetime
from flask import (
    Blueprint,
    redirect,
    url_for,
    current_app,
    send_from_directory,
    render_template,
    jsonify,
    request,
)
from modules.auth_decorators import login_required
from database.models import (
    get_participants_by_course,
    create_certificate,
    get_all_certificates,
    get_certificate_by_id,
    delete_certificate_row,
    delete_all_certificate_rows,
    update_certificate_export_files,
    get_course_by_id,
    get_template_by_id,
    get_all_courses,
    get_next_certificate_id,
    create_participant,
)
from modules.qr_generator import generate_qr_code
from modules.file_cleanup import delete_certificate_files
from modules.certificate_renderer import (
    get_positions_for_template,
    render_certificate_to_pdf,
)

certificates_gen_bp = Blueprint("certificates_gen", __name__)


def _safe_filename_part(text):
    text = (text or "certificate").strip()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"\s+", "_", text)[:40] or "certificate"


def _collect_form(form):
    return {
        "course_id": form.get("course_id", "").strip(),
        "certificate_no": form.get("certificate_no", "").strip(),
        "student_name": form.get("student_name", "").strip(),
        "date_of_birth": form.get("date_of_birth", "").strip(),
        "cdc_no": form.get("cdc_no", "").strip(),
        "passport_no": form.get("passport_no", "").strip(),
        "competency_grade": form.get("competency_grade", "").strip(),
        "competency_no": form.get("competency_no", "").strip(),
        "indos_no": form.get("indos_no", "").strip(),
        "held_from": form.get("held_from", "").strip(),
        "held_to": form.get("held_to", "").strip(),
        "issue_day_month": form.get("issue_day_month", "").strip(),
        "issue_year": form.get("issue_year", "").strip(),
        "issue_date": form.get("issue_date", "").strip() or form.get("held_to", "").strip(),
        "course_name": form.get("course_name", "").strip(),
        "description_below": form.get("description_below", "").strip(),
        "qr_label": form.get("qr_label", "").strip(),
    }


@certificates_gen_bp.route("/certificates")
@login_required
def certificates_list():
    certs = get_all_certificates()
    courses = get_all_courses()
    total = len(certs)
    generated = sum(1 for c in certs if c["status"] == "Generated")
    return render_template(
        "certificates.html",
        certs=certs,
        courses=courses,
        total_certs=total,
        generated_count=generated,
    )


@certificates_gen_bp.route("/certificates/generate", methods=["GET", "POST"])
@login_required
def generate_manual():
    courses = get_all_courses()
    form = {}
    participant_id = request.args.get("participant_id") or request.form.get("participant_id")

    # Prefill from participant when opened from Participants list
    if request.method == "GET" and participant_id:
        from database.models import get_participant_by_id
        p = get_participant_by_id(int(participant_id))
        if p:
            form = {
                "course_id": str(p["course_id"]),
                "student_name": p["name"] or "",
                "certificate_no": p["certificate_no"] if "certificate_no" in p.keys() else "",
                "date_of_birth": p["date_of_birth"] if "date_of_birth" in p.keys() else "",
                "cdc_no": p["cdc_no"] if "cdc_no" in p.keys() else "",
                "passport_no": p["passport_no"] if "passport_no" in p.keys() else "",
                "competency_grade": p["competency_grade"] if "competency_grade" in p.keys() else "",
                "competency_no": p["competency_no"] if "competency_no" in p.keys() else "",
                "indos_no": p["indos_no"] if "indos_no" in p.keys() else "",
                "held_from": p["held_from"] if "held_from" in p.keys() else "",
                "held_to": p["held_to"] if "held_to" in p.keys() else "",
                "issue_day_month": p["issue_day_month"] if "issue_day_month" in p.keys() else "",
                "issue_year": p["issue_year"] if "issue_year" in p.keys() else "",
                "course_name": p["course_name_text"] if "course_name_text" in p.keys() else "",
                "description_below": p["description_below"] if "description_below" in p.keys() else "",
                "qr_label": p["qr_label"] if "qr_label" in p.keys() else "",
                "participant_id": str(p["id"]),
            }

    if request.method == "GET":
        return render_template(
            "generate_certificate.html", courses=courses, error=None, form=form
        )

    # ----- existing POST logic stays below this line (do not delete) -----
    data = _collect_form(request.form)
    

    if not data["student_name"]:
        return render_template(
            "generate_certificate.html",
            courses=courses,
            error="Student Name is required.",
            form=data,
        )
    if not data["certificate_no"]:
        return render_template(
            "generate_certificate.html",
            courses=courses,
            error="Certificate No is required.",
            form=data,
        )
    if not data["course_id"]:
        return render_template(
            "generate_certificate.html",
            courses=courses,
            error="Please select a course.",
            form=data,
        )

    course = get_course_by_id(int(data["course_id"]))
    if not course or not course["template_id"]:
        return render_template(
            "generate_certificate.html",
            courses=courses,
            error="Course must have a template assigned.",
            form=data,
        )

    template = get_template_by_id(course["template_id"])
    if not template:
        return render_template(
            "generate_certificate.html",
            courses=courses,
            error="Template not found.",
            form=data,
        )

    if not data["course_name"]:
        data["course_name"] = course["course_name"] or ""

    # Positions: DB (designer) if saved, else ODS_ABS_LAYOUT
    positions = get_positions_for_template(template["id"])

    certificate_id = get_next_certificate_id()

    # QR
       # QR — plain text details (no website redirect when scanned)
    qr_folder = current_app.config["QR_FOLDER"]
    os.makedirs(qr_folder, exist_ok=True)
    qr_safe_id = certificate_id.replace("/", "-")
    qr_filename = f"{qr_safe_id}.png"
    qr_output_path = os.path.join(qr_folder, qr_filename)

    # Same style as phone scan result:
    # ODS/STCW/0118/2026 MANDIP SINGH ODS MARITIME ACADEMY FOUNDATION 1993-12-09 2026-06-03 2026-06-15
    cert_no = (data.get("certificate_no") or certificate_id or "").strip()
    student_name = (data.get("student_name") or "").strip()
    organization = (data.get("organization_name") or "ODS MARITIME ACADEMY FOUNDATION").strip()
    dob = (data.get("date_of_birth") or "").strip()
    held_from = (data.get("held_from") or "").strip()
    held_to = (data.get("held_to") or "").strip()

    qr_text = " ".join(
        part for part in [cert_no, student_name, organization, dob, held_from, held_to] if part
    )
    generate_qr_code(qr_text, qr_output_path)

    template_path = os.path.join(
        current_app.config["UPLOAD_FOLDER"], template["file_name"]
    )
    if not os.path.exists(template_path):
        return render_template(
            "generate_certificate.html",
            courses=courses,
            error="Template file missing on disk. Re-upload the template.",
            form=data,
        )

    field_data = {
        "certificate_no": data["certificate_no"],
        "certificate_id": certificate_id,
        "student_name": data["student_name"],
        "date_of_birth": data["date_of_birth"],
        "cdc_no": data["cdc_no"],
        "passport_no": data["passport_no"],
        "competency_grade": data["competency_grade"],
        "competency_no": data["competency_no"],
        "indos_no": data["indos_no"],
        "course_name": data["course_name"],
        "held_from": data["held_from"],
        "held_to": data["held_to"],
        "issue_day_month": data["issue_day_month"],
        "issue_year": data["issue_year"],
        "qr_label": data.get("qr_label", ""),
        "description_below": data["description_below"],
    }

    base_name = f"{_safe_filename_part(data['student_name'])}_{qr_safe_id}"
    pdf_folder = current_app.config["GENERATED_FOLDER"]
    png_folder = current_app.config.get("GENERATED_PNG_FOLDER", pdf_folder)
    os.makedirs(pdf_folder, exist_ok=True)
    os.makedirs(png_folder, exist_ok=True)

    output_filename = f"{base_name}.pdf"
    output_path = os.path.join(pdf_folder, output_filename)
    png_filename = f"{base_name}.png"

    try:
        render_certificate_to_pdf(
            template_path,
            field_data,
            positions,
            qr_code_path=qr_output_path,
            output_pdf_path=output_path,
        )
    except Exception as e:
        return render_template(
            "generate_certificate.html",
            courses=courses,
            error=f"PDF generation failed: {e}",
            form=data,
        )

    # Optional PNG preview
    try:
        from modules.svg_certificate_gen import pdf_to_png
        pdf_to_png(output_path, os.path.join(png_folder, png_filename))
    except Exception:
        png_filename = None

    create_participant(
    course["id"],
    data["student_name"],
    f"{_safe_filename_part(data['student_name']).lower()}@placeholder.local",
    "",
    "",
    "",
    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "",  # contact_no
)
    parts = get_participants_by_course(course["id"])
    participant_id = parts[0]["id"] if parts else None

    details = {
        "student_name": data["student_name"],
        "organization_name": "ODS Maritime Academy Foundation",
        "description_below": data["description_below"],
        "date_of_birth": data["date_of_birth"],
        "held_from": data["held_from"],
        "held_to": data["held_to"],
        "passport_no": data["passport_no"],
        "cdc_no": data["cdc_no"],
        "indos_no": data["indos_no"],
        "competency_grade": data["competency_grade"],
        "course_name_snapshot": data["course_name"],
        "captain_name": data["certificate_no"],
    }

    try:
        create_certificate(
            participant_id,
            certificate_id,
            output_filename,
            data["issue_date"] or data["held_to"],
            "Generated",
            qr_code=qr_filename,
            details=details,
        )
    except Exception:
        certificate_id = get_next_certificate_id()
        create_certificate(
            participant_id,
            certificate_id,
            output_filename,
            data["issue_date"] or data["held_to"],
            "Generated",
            qr_code=qr_filename,
            details=details,
        )

    try:
        update_certificate_export_files(certificate_id, None, png_filename)
    except Exception:
        pass

    return redirect(
        url_for(
            "certificates_gen.certificate_preview",
            filename=output_filename,
            cert_id=certificate_id,
        )
    )


@certificates_gen_bp.route("/certificates/preview")
@login_required
def certificate_preview():
    return render_template(
        "certificate_preview.html",
        filename=request.args.get("filename", ""),
        certificate_id=request.args.get("cert_id", ""),
    )


@certificates_gen_bp.route("/certificates/download/<path:filename>")
@login_required
def download_certificate(filename):
    return send_from_directory(
        current_app.config["GENERATED_FOLDER"], filename, as_attachment=True
    )


@certificates_gen_bp.route("/certificates/view/<path:filename>")
@login_required
def view_certificate(filename):
    return send_from_directory(
        current_app.config["GENERATED_FOLDER"], filename, as_attachment=False
    )


@certificates_gen_bp.route("/certificates/download/svg/<path:filename>")
@login_required
def download_certificate_svg(filename):
    folder = current_app.config.get("GENERATED_SVG_FOLDER", current_app.config["GENERATED_FOLDER"])
    return send_from_directory(folder, filename, as_attachment=True)


@certificates_gen_bp.route("/certificates/download/png/<path:filename>")
@login_required
def download_certificate_png(filename):
    folder = current_app.config.get("GENERATED_PNG_FOLDER", current_app.config["GENERATED_FOLDER"])
    return send_from_directory(folder, filename, as_attachment=True)


@certificates_gen_bp.route("/api/certificates/<int:cert_id>", methods=["DELETE"])
@login_required
def api_delete_certificate(cert_id):
    cert = get_certificate_by_id(cert_id)
    if cert is None:
        return jsonify({"success": False, "message": "Certificate not found."}), 404
    try:
        file_errors = delete_certificate_files(
            current_app.config,
            cert["file_name"],
            cert["qr_code"],
            cert["svg_file_name"] if "svg_file_name" in cert.keys() else None,
            cert["png_file_name"] if "png_file_name" in cert.keys() else None,
        )
        if file_errors:
            return jsonify({"success": False, "message": " ".join(file_errors)}), 500
        delete_certificate_row(cert_id)
        return jsonify({"success": True, "message": "Certificate deleted."})
    except Exception:
        return jsonify({"success": False, "message": "Failed to delete certificate."}), 500


@certificates_gen_bp.route("/api/certificates", methods=["DELETE"])
@login_required
def api_delete_all_certificates():
    try:
        for cert in get_all_certificates():
            delete_certificate_files(
                current_app.config,
                cert["file_name"],
                cert["qr_code"],
                cert["svg_file_name"] if "svg_file_name" in cert.keys() else None,
                cert["png_file_name"] if "png_file_name" in cert.keys() else None,
            )
        delete_all_certificate_rows()
        return jsonify({"success": True, "message": "All certificates deleted."})
    except Exception:
        return jsonify({"success": False, "message": "Failed to delete certificates."}), 500