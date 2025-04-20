from flask import Blueprint, render_template, redirect, url_for, request, flash, g
from flask_jwt_extended import (
    create_access_token,
    set_access_cookies,
    unset_jwt_cookies,
    get_jwt_identity,
    verify_jwt_in_request,
)
from app.models.user import User
from app import db
from datetime import timedelta

auth_views_bp = Blueprint("auth_views", __name__)


@auth_views_bp.before_request
def get_current_user():
    """Get current user before each request"""
    g.user = None
    try:
        verify_jwt_in_request(optional=True, locations=["cookies"])
        user_id = get_jwt_identity()
        if user_id:
            g.user = User.query.get(int(user_id))
    except Exception:
        pass


@auth_views_bp.route("/login", methods=["GET", "POST"])
def login():
    """Render the login page and handle login form submission"""
    # Redirect to dashboard if user is already logged in
    if g.user:
        flash("You are already logged in", "info")
        return redirect(url_for("main.dashboard"))
        
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            access_token = create_access_token(
                identity=str(user.id),
                expires_delta=timedelta(days=1)
            )

            response = redirect(url_for("main.dashboard"))
            set_access_cookies(response, access_token)
            return response

        flash("Invalid username or password", "error")

    return render_template("auth/login.html", current_user=g.user)


@auth_views_bp.route("/register", methods=["GET", "POST"])
def register():
    """Registration is currently disabled"""
    flash("Registration is currently disabled", "info")
    return redirect(url_for("auth_views.login"))

    """Render the registration page and handle registration form submission"""
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        # Validate form data
        if not all([username, email, password, confirm_password]):
            flash("All fields are required", "error")
            return render_template("auth/register.html", current_user=g.user)

        if password != confirm_password:
            flash("Passwords do not match", "error")
            return render_template("auth/register.html", current_user=g.user)

        # Check if user already exists
        if User.query.filter_by(username=username).first():
            flash("Username already exists", "error")
            return render_template("auth/register.html", current_user=g.user)

        if User.query.filter_by(email=email).first():
            flash("Email already exists", "error")
            return render_template("auth/register.html", current_user=g.user)

        # Create new user
        user = User(username=username, email=email)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        flash("Registration successful! Please log in.", "success")
        return redirect(url_for("auth_views.login"))

    return render_template("auth/register.html", current_user=g.user)


@auth_views_bp.route("/logout")
def logout():
    """Handle logout"""
    response = redirect(url_for("main.index"))
    unset_jwt_cookies(response)
    flash("You have been logged out", "info")
    return response
