"""
Courses section (previously called Events).
URL paths: /courses, /courses/add, /courses/edit/<id>, etc.
"""
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, current_app, jsonify
from modules.auth_decorators import login_required
from modules.file_cleanup import delete_certificate_files

from database.models import (
    get_all_courses,
    get_course_by_id,
    create_course,
    update_course,
    delete_course,
    get_all_templates,
    get_template_by_id,
    get_participants_by_course,
    get_certificates_by_participant,
    delete_certificates_by_participant,
    delete_participant,
)

courses_bp = Blueprint("courses", __name__)


def _cascade_delete_course(course_id):
    """Delete a course and everything under it (participants + their certificates)."""
    participants = get_participants_by_course(course_id)

    for participant in participants:
        certs = get_certificates_by_participant(participant["id"])
        for cert in certs:
            delete_certificate_files(
                current_app.config,
                cert["file_name"],
                cert["qr_code"],
                cert["svg_file_name"] if "svg_file_name" in cert.keys() else None,
                cert["png_file_name"] if "png_file_name" in cert.keys() else None,
            )
        delete_certificates_by_participant(participant["id"])
        delete_participant(participant["id"])

    delete_course(course_id)


@courses_bp.route("/courses")
@login_required
def courses():
    course_list = get_all_courses()
    today_str = datetime.now().strftime("%Y-%m-%d")
    upcoming_count = sum(
        1 for c in course_list
        if c["course_date"] and c["course_date"] >= today_str
    )
    return render_template(
        "courses.html",
        courses=course_list,
        total_courses=len(course_list),
        upcoming_count=upcoming_count,
    )


@courses_bp.route("/courses/add", methods=["GET", "POST"])
@login_required
def add_course():
    if request.method == "POST":
        course_name = request.form["course_name"]
        course_date = request.form["course_date"]
        organizer = request.form["organizer"]
        venue = request.form.get("venue", "")
        description = request.form.get("description", "")
        template_id = request.form.get("template_id") or None
        status = "Active"

        template = get_template_by_id(int(template_id)) if template_id else None
        template_name = template["template_name"] if template else None

        create_course(
            course_name, course_date, organizer,
            venue, description, template_name, status,
            template_id=template_id,
        )
        return redirect(url_for("courses.courses"))

    templates = get_all_templates(status="Active")
    return render_template("add_course.html", templates=templates)


@courses_bp.route("/courses/edit/<int:course_id>", methods=["GET", "POST"])
@login_required
def edit_course(course_id):
    course = get_course_by_id(course_id)
    if course is None:
        return redirect(url_for("courses.courses"))

    if request.method == "POST":
        template_id = request.form.get("template_id") or None
        template = get_template_by_id(int(template_id)) if template_id else None
        template_name = template["template_name"] if template else None

        update_course(
            course_id,
            request.form["course_name"],
            request.form["course_date"],
            request.form["organizer"],
            request.form.get("venue", ""),
            request.form.get("description", ""),
            template_name,
            course["status"],
            template_id=template_id,
        )
        return redirect(url_for("courses.courses"))

    templates = get_all_templates(status="Active")
    return render_template("edit_course.html", course=course, templates=templates)


@courses_bp.route("/courses/delete/<int:course_id>")
@login_required
def delete_course_route(course_id):
    _cascade_delete_course(course_id)
    return redirect(url_for("courses.courses", deleted="1"))


@courses_bp.route("/api/courses/<int:course_id>", methods=["DELETE"])
@login_required
def api_delete_course(course_id):
    course = get_course_by_id(course_id)
    if course is None:
        return jsonify({"success": False, "message": "Course not found."}), 404
    try:
        _cascade_delete_course(course_id)
        return jsonify({"success": True, "message": "Course and all its data deleted."})
    except Exception:
        return jsonify({"success": False, "message": "Failed to delete course."}), 500


@courses_bp.route("/api/courses", methods=["DELETE"])
@login_required
def api_delete_all_courses():
    try:
        for course in get_all_courses():
            _cascade_delete_course(course["id"])
        return jsonify({"success": True, "message": "All courses deleted."})
    except Exception:
        return jsonify({"success": False, "message": "Failed to delete courses."}), 500