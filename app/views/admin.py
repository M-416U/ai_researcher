from flask import Blueprint, render_template, redirect, url_for, request, flash, g
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from app.models.user import User
from app import db
from functools import wraps
import logging

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

@admin_bp.before_request
def get_current_user():
    """Get current user before each request to admin routes"""
    g.user = None
    try:
        verify_jwt_in_request(optional=True, locations=["cookies"])
        user_id = get_jwt_identity()
        if user_id:
            g.user = User.query.get(int(user_id))
    except Exception as e:
        logging.error(f"Error getting current user: {str(e)}", exc_info=True)
        pass

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        logging.debug(f"Admin access attempt for route: {request.path}")
        try:
            verify_jwt_in_request(locations=["cookies"])
            user_id = get_jwt_identity()
            logging.debug(f"JWT identity found: {user_id}")
            
            user = User.query.get(int(user_id))
            if not user:
                logging.warning(f"User not found for ID: {user_id}")
                flash("Admin access required", "error")
                return redirect(url_for("main.index"))
                
            if not user.is_admin:
                logging.warning(f"Non-admin user attempted admin access: {user.username} (ID: {user.id})")
                flash("Admin access required", "error")
                return redirect(url_for("main.index"))
                
            logging.info(f"Admin access granted to {user.username} (ID: {user.id}) for route: {request.path}")
            return f(*args, **kwargs)
        except Exception as e:
            logging.error(f"Admin access error: {str(e)}", exc_info=True)
            logging.error(f"Request details: Path={request.path}, Method={request.method}")
            flash("Please log in as an admin", "error")
            return redirect(url_for("auth_views.login"))
    return decorated_function

@admin_bp.route("/users")
@admin_required
def manage_users():
    """Admin page to manage users"""
    users = User.query.all()
    return render_template("admin/manage_users.html", users=users, current_user=g.user)

@admin_bp.route("/users/create", methods=["GET", "POST"])
@admin_required
def create_user():
    """Admin page to create a new user"""
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        is_admin = request.form.get("is_admin") == "on"
        
        # Validate form data
        if not all([username, email, password]):
            flash("All fields are required", "error")
            return render_template("admin/create_user.html", current_user=g.user)
            
        # Check if user already exists
        if User.query.filter_by(username=username).first():
            flash("Username already exists", "error")
            return render_template("admin/create_user.html", current_user=g.user)
            
        if User.query.filter_by(email=email).first():
            flash("Email already exists", "error")
            return render_template("admin/create_user.html", current_user=g.user)
            
        # Create new user
        try:
            User.create_user(username, email, password, is_admin)
            flash(f"User {username} created successfully", "success")
            return redirect(url_for("admin.manage_users"))
        except Exception as e:
            flash(f"Error creating user: {str(e)}", "error")
            
    return render_template("admin/create_user.html", current_user=g.user)

@admin_bp.route("/users/edit/<int:user_id>", methods=["POST"])
@admin_required
def edit_user(user_id):
    """Edit an existing user"""
    user = User.query.get_or_404(user_id)
    
    username = request.form.get("username")
    email = request.form.get("email")
    password = request.form.get("password")
    is_admin = request.form.get("is_admin") == "on"
    
    # Check if username or email is being changed and already exists
    if username != user.username and User.query.filter_by(username=username).first():
        flash("Username already exists", "error")
        return redirect(url_for("admin.manage_users"))
        
    if email != user.email and User.query.filter_by(email=email).first():
        flash("Email already exists", "error")
        return redirect(url_for("admin.manage_users"))
    
    # Update user details
    user.username = username
    user.email = email
    user.is_admin = is_admin
    
    # Update password if provided
    if password:
        user.set_password(password)
    
    try:
        db.session.commit()
        flash(f"User {username} updated successfully", "success")
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error updating user: {str(e)}", exc_info=True)
        flash(f"Error updating user: {str(e)}", "error")
    
    return redirect(url_for("admin.manage_users"))

@admin_bp.route("/users/delete/<int:user_id>", methods=["POST"])
@admin_required
def delete_user(user_id):
    """Delete a user"""
    user = User.query.get_or_404(user_id)
    
    # Prevent deleting yourself
    if g.user and g.user.id == user.id:
        flash("You cannot delete your own account", "error")
        return redirect(url_for("admin.manage_users"))
    
    try:
        username = user.username
        db.session.delete(user)
        db.session.commit()
        flash(f"User {username} deleted successfully", "success")
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error deleting user: {str(e)}", exc_info=True)
        flash(f"Error deleting user: {str(e)}", "error")
    
    return redirect(url_for("admin.manage_users"))