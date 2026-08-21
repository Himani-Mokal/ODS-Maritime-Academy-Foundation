from flask import Blueprint, render_template, request, redirect, url_for, session
from werkzeug.security import check_password_hash

from database.models import get_admin_by_username

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("admin_id"):
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        admin = get_admin_by_username(username)

        if admin and check_password_hash(admin["password"], password):
            session["admin_id"] = admin["id"]
            session["username"] = admin["username"]
            next_url = request.args.get("next") or url_for("dashboard")
            if not next_url.startswith("/"):
                next_url = url_for("dashboard")
            return redirect(next_url)

        return render_template("login.html", error="Invalid username or password")

    return render_template("login.html", error=None)


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))