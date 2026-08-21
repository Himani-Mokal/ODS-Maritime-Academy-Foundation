from flask import Flask, render_template, request, session, g, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from database.models import get_admin_by_username, create_admin
from database.db import run_schema_migrations
# --- Blueprints (each file handles one section of the website) ---
from routes.courses import courses_bp
from routes.templates import templates_bp
from routes.participants import participants_bp
from routes.certificates_gen import certificates_gen_bp
from routes.verify import verify_bp
from routes.auth import auth_bp

from database.models import (
    get_dashboard_stats,
    get_admin_by_id,
    update_admin_password,
    update_admin_profile,
    get_recent_certificates,
)
from modules.auth_decorators import login_required
from database.db import run_schema_migrations

app = Flask(__name__)
app.config.from_pyfile("config.py")

# Runs safely every startup: renames Event→Course, adds new columns, drops email_logs
run_schema_migrations()

app.register_blueprint(courses_bp)
app.register_blueprint(templates_bp)
app.register_blueprint(participants_bp)
app.register_blueprint(certificates_gen_bp)
app.register_blueprint(verify_bp)
app.register_blueprint(auth_bp)

def ensure_bootstrap_admin():
    username = os.environ.get("BOOTSTRAP_ADMIN_USER", "").strip()
    password = os.environ.get("BOOTSTRAP_ADMIN_PASSWORD", "").strip()
    email = os.environ.get("BOOTSTRAP_ADMIN_EMAIL", "admin@example.com").strip()
    if not username or not password:
        return
    if get_admin_by_username(username) is None:
        create_admin(
            username,
            email,
            generate_password_hash(password),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

# after run_schema_migrations()
run_schema_migrations()
def ensure_bootstrap_admin():
    username = os.environ.get("BOOTSTRAP_ADMIN_USER", "").strip()
    password = os.environ.get("BOOTSTRAP_ADMIN_PASSWORD", "").strip()
    email = os.environ.get("BOOTSTRAP_ADMIN_EMAIL", "admin@example.com").strip()

    if not username or not password:
        print("BOOTSTRAP: skipped (USER or PASSWORD env not set)")
        return

    existing = get_admin_by_username(username)
    if existing is not None:
        print(f"BOOTSTRAP: admin '{username}' already exists")
        return

    create_admin(
        username,
        email,
        generate_password_hash(password),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )
    print(f"BOOTSTRAP: created admin '{username}'")
    ensure_bootstrap_admin()
@app.before_request
def load_logged_in_admin():
    admin_id = session.get("admin_id")
    g.admin = get_admin_by_id(admin_id) if admin_id else None

    # Public routes only (no admin login)
    public_endpoints = {
        "auth.login",
        "verify.verify_search",
        "verify.verify_certificate",
        "verify.qr_image",
        "static",
    }
    if request.endpoint is None:
        return
    if request.endpoint in public_endpoints:
        return
    if request.endpoint.startswith("verify."):
        return

    # Everything else requires admin login
    if "admin_id" not in session:
        return redirect(url_for("auth.login"))


@app.route("/")
@login_required
def dashboard():
    stats = get_dashboard_stats()
    recent_certs = get_recent_certificates(5)
    return render_template("dashboard.html", stats=stats, recent_certs=recent_certs)


@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    message = None
    error = None

    if request.method == "POST":
        form_type = request.form.get("form_type")

        if form_type == "profile":
            username = (request.form.get("username") or "").strip()
            email = (request.form.get("email") or "").strip()
            profile_pic_filename = None

            if not username:
                error = "Username is required."
            elif not email:
                error = "Email is required."
            else:
                file = request.files.get("profile_pic")
                if file and file.filename != "":
                    upload_folder = os.path.join(app.static_folder, "uploads")
                    os.makedirs(upload_folder, exist_ok=True)
                    profile_pic_filename = secure_filename(f"{session['admin_id']}_{file.filename}")
                    file.save(os.path.join(upload_folder, profile_pic_filename))

                    update_admin_profile(
                    session["admin_id"],
                    username=username,
                    email=email,
                    profile_pic=profile_pic_filename,
                )
                session["username"] = username
                g.admin = get_admin_by_id(session["admin_id"])
                message = "Profile updated successfully!"

        elif form_type == "password":
            current_password = request.form.get("current_password", "")
            new_password = request.form.get("new_password", "")
            confirm_password = request.form.get("confirm_password", "")

            admin = get_admin_by_id(session["admin_id"])

            if admin is None:
                error = "Admin session invalid. Please log in again."
            elif not check_password_hash(admin["password"], current_password):
                error = "Current password is incorrect."
            elif new_password != confirm_password:
                error = "New passwords do not match."
            elif len(new_password) < 6:
                error = "New password must be at least 6 characters long."
            else:
                update_admin_password(admin["id"], generate_password_hash(new_password))
                message = "Password updated successfully!"

    admin = get_admin_by_id(session["admin_id"])
    return render_template("settings.html", admin=admin, message=message, error=error)


if __name__ == "__main__":
    app.run(debug=True)