"""
Participants + entry point for certificate generation.
"""
from datetime import datetime
from flask import (
    Blueprint, render_template, request, redirect, url_for, current_app, jsonify,
)
from modules.auth_decorators import login_required
from modules.file_cleanup import delete_certificate_files
from database.models import (
    get_all_participants,
    get_all_courses,
    create_participant,
    update_participant,
    delete_participant,
    get_participant_by_id,
    get_certificates_by_participant,
    delete_certificates_by_participant,
)

participants_bp = Blueprint("participants", __name__)


def _cascade_delete_participant(participant_id):
    certs = get_certificates_by_participant(participant_id)
    for cert in certs:
        delete_certificate_files(
            current_app.config,
            cert["file_name"],
            cert["qr_code"],
            cert["svg_file_name"] if "svg_file_name" in cert.keys() else None,
            cert["png_file_name"] if "png_file_name" in cert.keys() else None,
        )
    delete_certificates_by_participant(participant_id)
    delete_participant(participant_id)


def _form_to_participant_kwargs(form):
    return dict(
        course_id=form.get("course_id"),
        name=form.get("name", "").strip(),
        email=form.get("email", "").strip(),
        college=form.get("college", ""),
        department=form.get("department", ""),
        position=form.get("position", ""),
        contact_no=form.get("contact_no", ""),
        certificate_no=form.get("certificate_no", ""),
        date_of_birth=form.get("date_of_birth", ""),
        cdc_no=form.get("cdc_no", ""),
        passport_no=form.get("passport_no", ""),
        competency_grade=form.get("competency_grade", ""),
        competency_no=form.get("competency_no", ""),
        indos_no=form.get("indos_no", ""),
        held_from=form.get("held_from", ""),
        held_to=form.get("held_to", ""),
        issue_day_month=form.get("issue_day_month", ""),
        issue_year=form.get("issue_year", ""),
        course_name_text=form.get("course_name", ""),
        description_below=form.get("description_below", ""),
        qr_label=form.get("qr_label", ""),
    )


@participants_bp.route("/participants")
@login_required
def participants_list():
    participants = get_all_participants()
    courses = get_all_courses()
    return render_template(
        "participants.html",
        participants=participants,
        total_participants=len(participants),
        total_courses=len(courses),
    )


@participants_bp.route("/participants/add", methods=["GET", "POST"])
@login_required
def add_participant():
    courses = get_all_courses()
    if request.method == "POST":
        data = _form_to_participant_kwargs(request.form)
        if not data["course_id"] or not data["name"]:
            return render_template(
                "add_participant.html", courses=courses, error="Course and Name are required.", form=request.form,
            )
        if not data["email"]:
            data["email"] = f"{data['name'].lower().replace(' ', '.')}@placeholder.local"
        create_participant(
            data["course_id"], data["name"], data["email"],
            data["college"], data["department"], data["position"],
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            data["contact_no"], data["certificate_no"], data["date_of_birth"],
            data["cdc_no"], data["passport_no"], data["competency_grade"],
            data["competency_no"], data["indos_no"], data["held_from"], data["held_to"],
            data["issue_day_month"], data["issue_year"], data["course_name_text"],
            data["description_below"], data["qr_label"],
        )
        return redirect(url_for("participants.participants_list"))
    return render_template("add_participant.html", courses=courses, error=None, form={})


@participants_bp.route("/participants/<int:participant_id>/edit", methods=["GET", "POST"])
@login_required
def edit_participant(participant_id):
    p = get_participant_by_id(participant_id)
    if p is None:
        return redirect(url_for("participants.participants_list"))
    courses = get_all_courses()
    if request.method == "POST":
        data = _form_to_participant_kwargs(request.form)
        update_participant(participant_id, **{k: v for k, v in data.items() if k != "course_id" or v})
        # allow course_id update
        update_participant(participant_id, **data)
        return redirect(url_for("participants.participants_list"))
    # map DB row to form-like dict
    form = {
        "course_id": str(p["course_id"]),
        "name": p["name"] or "",
        "email": p["email"] or "",
        "contact_no": p["contact_no"] if "contact_no" in p.keys() else "",
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
    }
    return render_template("add_participant.html", courses=courses, error=None, form=form, editing=True, participant_id=participant_id)


@participants_bp.route("/participants/delete/<int:participant_id>")
@login_required
def delete_participant_route(participant_id):
    _cascade_delete_participant(participant_id)
    return redirect(url_for("participants.participants_list", deleted="1"))


@participants_bp.route("/api/participants/delete-selected", methods=["POST"])
@login_required
def api_delete_selected():
    data = request.get_json(silent=True) or {}
    ids = data.get("ids") or []
    try:
        for pid in ids:
            _cascade_delete_participant(int(pid))
        return jsonify({"success": True, "message": f"Deleted {len(ids)} participant(s)."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500