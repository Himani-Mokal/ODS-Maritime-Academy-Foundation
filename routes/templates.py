import os
import shutil
import json
from datetime import datetime
from werkzeug.utils import secure_filename
from modules.template_converter import convert_uploaded_template, TemplateConversionError
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    current_app,
    send_from_directory,
    jsonify,
    abort,
)
from modules.auth_decorators import login_required

from database.models import (
    get_all_templates,
    get_template_by_id,
    create_template,
    update_template,
    delete_template,
    get_courses_by_template,
    get_field_positions_for_template,
    save_field_position,
)
from modules.certificate_field_renderer import load_background_svg

DETAILED_CERTIFICATE_FIELDS = [
    ("certificate_id", "Certificate No."),
    ("student_name", "Student Name"),
    ("captain_name", "Captain Name"),
    ("organization_name", "Organization Name"),
    ("course_name", "Course / Training Name"),
    ("description_above", "Description (above)"),
    ("description_below", "Description (below)"),
    ("date_of_birth", "Date of Birth"),
    ("held_from", "Held From"),
    ("held_to", "Held To"),
    ("issue_date", "Issue Date"),
    ("passport_no", "Passport Number"),
    ("cdc_no", "CDC Number"),
    ("competency_grade", "Competency Grade"),
    ("indos_no", "INDOS Number"),
]

templates_bp = Blueprint("templates", __name__)


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in current_app.config["ALLOWED_EXTENSIONS"]
    )


def _extension_of(filename):
    return filename.rsplit(".", 1)[1].lower() if "." in filename else ""


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@templates_bp.route("/templates")
@login_required
def templates_list():
    search = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    template_type = request.args.get("type", "").strip()

    templates = get_all_templates(
        search=search or None,
        status=status or None,
        template_type=template_type or None,
    )

    templates_with_events = []
    for template in templates:
        assigned_events = get_courses_by_template(template["id"])
        templates_with_events.append({
            "template": template,
            "assigned_events": assigned_events,
        })

    return render_template(
        "templates_list.html",
        templates_with_events=templates_with_events,
        search=search,
        status=status,
        template_type=template_type,
        total_templates=len(templates),
    )


@templates_bp.route("/templates/upload", methods=["GET", "POST"])
@login_required
def upload_template():
    if request.method == "POST":
        template_name = request.form.get("template_name", "").strip()
        description = request.form.get("description", "").strip()
        file = request.files.get("template_file")

        if not template_name:
            return render_template(
                "upload_template.html",
                error="Template name is required.",
            ), 400

        if not file or file.filename == "":
            return render_template(
                "upload_template.html",
                error="Please choose a template file to upload.",
            ), 400

        if not allowed_file(file.filename):
            return render_template(
                "upload_template.html",
                error="Unsupported file type. Please upload an SVG, PDF, DOCX, PPTX, PNG, or JPG file.",
            ), 400

        safe_name = secure_filename(file.filename)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        temp_filename = f"{timestamp}_{safe_name}"

        upload_folder = current_app.config["UPLOAD_FOLDER"]
        os.makedirs(upload_folder, exist_ok=True)

        temp_path = os.path.join(upload_folder, temp_filename)
        file.save(temp_path)

        extension = _extension_of(safe_name)

        try:
            svg_source, warning = convert_uploaded_template(temp_path, extension)
        except TemplateConversionError as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return render_template("upload_template.html", error=str(e)), 400

        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass

        base = secure_filename(template_name) or safe_name.rsplit(".", 1)[0]
        svg_filename = f"{timestamp}_{base}.svg"
        svg_path = os.path.join(upload_folder, svg_filename)

        with open(svg_path, "w", encoding="utf-8") as f:
            f.write(svg_source)

        create_template(
            template_name,
            svg_filename,
            _now(),
            "Active",
            template_type="svg",
            description=description,
        )

        return redirect(url_for("templates.templates_list", converted_warning=warning or ""))

    return render_template("upload_template.html")


@templates_bp.route("/templates/edit/<int:template_id>", methods=["GET", "POST"])
@login_required
def edit_template(template_id):
    template = get_template_by_id(template_id)
    if template is None:
        abort(404)

    if request.method == "POST":
        template_name = request.form.get("template_name", "").strip()
        description = request.form.get("description", "").strip()
        status = request.form.get("status", "Active")
        file = request.files.get("template_file")

        if not template_name:
            return render_template(
                "edit_template.html",
                template=template,
                error="Template name is required.",
            ), 400

        new_filename = None

        if file and file.filename != "":
            if not allowed_file(file.filename):
                return render_template(
                    "edit_template.html",
                    template=template,
                    error="Unsupported file type.",
                ), 400

            safe_name = secure_filename(file.filename)
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            temp_filename = f"{timestamp}_{safe_name}"

            upload_folder = current_app.config["UPLOAD_FOLDER"]
            os.makedirs(upload_folder, exist_ok=True)

            temp_path = os.path.join(upload_folder, temp_filename)
            file.save(temp_path)

            extension = _extension_of(safe_name)

            try:
                svg_source, warning = convert_uploaded_template(temp_path, extension)
            except TemplateConversionError as e:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                return render_template(
                    "edit_template.html",
                    template=template,
                    error=str(e),
                ), 400

            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass

            base = secure_filename(template_name) or safe_name.rsplit(".", 1)[0]
            new_filename = f"{timestamp}_{base}.svg"
            svg_path = os.path.join(upload_folder, new_filename)

            with open(svg_path, "w", encoding="utf-8") as f:
                f.write(svg_source)

        update_template(
            template_id,
            template_name,
            description,
            status,
            _now(),
            file_name=new_filename,
        )

        return redirect(url_for("templates.templates_list"))

    return render_template("edit_template.html", template=template)


@templates_bp.route("/templates/duplicate/<int:template_id>")
@login_required
def duplicate_template(template_id):
    template = get_template_by_id(template_id)
    if template is None:
        abort(404)

    upload_folder = current_app.config["UPLOAD_FOLDER"]
    original_path = os.path.join(upload_folder, template["file_name"])

    extension = _extension_of(template["file_name"])
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    new_filename = f"{timestamp}_copy.{extension}" if extension else f"{timestamp}_copy"

    if os.path.exists(original_path):
        shutil.copyfile(original_path, os.path.join(upload_folder, new_filename))
    else:
        new_filename = template["file_name"]

    create_template(
        f"{template['template_name']} (Copy)",
        new_filename,
        _now(),
        "Inactive",
        template_type=template["template_type"] or "svg",
        description=template["description"] or "",
    )

    return redirect(url_for("templates.templates_list"))


@templates_bp.route("/templates/delete/<int:template_id>")
@login_required
def delete_template_route(template_id):
    template = get_template_by_id(template_id)

    if template is not None:
        upload_folder = current_app.config["UPLOAD_FOLDER"]
        file_path = os.path.join(upload_folder, template["file_name"])
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass

    delete_template(template_id)
    return redirect(url_for("templates.templates_list"))


@templates_bp.route("/templates/<int:template_id>/positions", methods=["GET", "POST"])
@login_required
def template_positions(template_id):
    template = get_template_by_id(template_id)
    if template is None:
        abort(404)

    if request.method == "POST":
        for field_key, _label in DETAILED_CERTIFICATE_FIELDS:
            if request.form.get(f"{field_key}__enabled") != "on":
                continue
            try:
                x = float(request.form.get(f"{field_key}__x", 0))
                y = float(request.form.get(f"{field_key}__y", 0))
                width = float(request.form.get(f"{field_key}__width", 200))
                height = float(request.form.get(f"{field_key}__height", 40))
                font_size = float(request.form.get(f"{field_key}__font_size", 20))
            except ValueError:
                continue

            save_field_position(
                template_id, field_key, x, y, width, height,
                font_size=font_size,
                color=request.form.get(f"{field_key}__color", "#111111"),
                align=request.form.get(f"{field_key}__align", "left"),
                bold=request.form.get(f"{field_key}__bold") == "on",
                italic=request.form.get(f"{field_key}__italic") == "on",
                underline=request.form.get(f"{field_key}__underline") == "on",
                is_rich=field_key in ("description_above", "description_below"),
            )

        return redirect(url_for("templates.template_positions", template_id=template_id, saved="1"))

    upload_folder = current_app.config["UPLOAD_FOLDER"]
    file_path = os.path.join(upload_folder, template["file_name"])

    background_svg, width, height = load_background_svg(file_path)
    existing = {row["field_key"]: row for row in get_field_positions_for_template(template_id)}

    return render_template(
        "template_positions.html",
        template=template,
        background_svg=background_svg,
        width=width,
        height=height,
        fields=DETAILED_CERTIFICATE_FIELDS,
        existing=existing,
        saved=request.args.get("saved") == "1",
    )


@templates_bp.route("/templates/file/<int:template_id>")
@login_required
def template_file(template_id):
    template = get_template_by_id(template_id)
    if template is None:
        abort(404)

    return send_from_directory(
        current_app.config["UPLOAD_FOLDER"],
        template["file_name"],
    )


@templates_bp.route("/api/templates/<int:template_id>/raw")
@login_required
def template_raw_svg(template_id):
    template = get_template_by_id(template_id)
    if template is None:
        return jsonify({"success": False, "message": "Template not found."}), 404

    file_path = os.path.join(current_app.config["UPLOAD_FOLDER"], template["file_name"])

    if not os.path.exists(file_path):
        return jsonify({"success": False, "message": "Template file is missing on disk."}), 404

    if template["template_type"] != "svg":
        return jsonify({"success": False, "message": "This template is not an SVG template."}), 400

    with open(file_path, "r", encoding="utf-8") as f:
        svg_source = f.read()

    return jsonify({"success": True, "svg": svg_source})


# ============================================================
# TEMPLATE DESIGNER (only once — do not duplicate these routes)
# ============================================================

@templates_bp.route("/templates/<int:template_id>/designer")
@login_required
def template_designer(template_id):
    from modules.certificate_renderer import (
        PLACEHOLDER_CATALOG,
        get_positions_for_template,
    )
    template = get_template_by_id(template_id)
    if template is None:
        abort(404)
    positions = get_positions_for_template(template_id)
    return render_template(
        "template_designer.html",
        template=template,
        catalog=PLACEHOLDER_CATALOG,
        positions=positions,
    )


@templates_bp.route("/templates/<int:template_id>/designer/save", methods=["POST"])
@login_required
def save_designer_positions(template_id):
    template = get_template_by_id(template_id)
    if template is None:
        return jsonify({"success": False, "message": "Template not found"}), 404

    raw = request.form.get("positions_json", "")
    try:
        positions = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        return jsonify({"success": False, "message": "Invalid JSON"}), 400

    for key, vals in positions.items():
        if not isinstance(vals, dict):
            continue
        try:
            x = float(vals.get("x", 0.1))
            y = float(vals.get("y", 0.1))
            w = float(vals.get("w", 0.2))
            h = float(vals.get("h", 0.03))
            fs = float(vals.get("font_size", 0.014))
        except (TypeError, ValueError):
            continue
        if not (0 <= x <= 1 and 0 <= y <= 1):
            continue
        if w > 1:
            w = 0.3
        if h > 1:
            h = 0.03
        if fs >= 1:
            fs = fs / 850.0
        save_field_position(
            template_id, key, x, y, w, h,
            font_size=fs,
            color=vals.get("color", "#000000") or "#000000",
            align=vals.get("align", "left") or "left",
            bold=bool(vals.get("bold", 1)),
            italic=bool(vals.get("italic", 0)),
        )

    return jsonify({
        "success": True,
        "message": "Positions saved. Certificates will use these exact positions.",
    })