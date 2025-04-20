from flask import Blueprint, render_template, redirect, url_for, g
from flask_jwt_extended import (
    verify_jwt_in_request,
    get_jwt_identity,
)
from app.models.user import User
from datetime import datetime, timedelta
from app.models.research import ResearchProject, ResearchOutline
from app.models.content import ResearchContent

main_bp = Blueprint("main", __name__)


@main_bp.before_request
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


def public_route(f):
    """Decorator for public routes that can handle optional JWT"""

    def decorated_function(*args, **kwargs):
        try:
            verify_jwt_in_request(optional=True, locations=["cookies"])
            return f(*args, **kwargs)
        except Exception as e:
            print(f"JWT verification error: {str(e)}")
            return f(*args, **kwargs)

    decorated_function.__name__ = f.__name__
    return decorated_function


@main_bp.route("/")
@public_route
def index():
    """Render the home page"""
    return render_template("index.html", current_user=g.user, now=datetime.now())


@main_bp.route("/dashboard")
def dashboard():
    """Render the dashboard page"""
    try:
        verify_jwt_in_request(locations=["cookies"])
        user_id = get_jwt_identity()
        user = User.query.get(int(user_id))

        if not user:
            return redirect(url_for("auth_views.login"))

        # Get user's projects
        projects = ResearchProject.query.filter_by(user_id=int(user_id)).all()

        # Count completed projects (those with content)
        completed_projects = 0
        for project in projects:
            # Get the latest outline
            latest_outline = (
                ResearchOutline.query.filter_by(project_id=project.id, is_approved=True)
                .order_by(ResearchOutline.created_at.desc())
                .first()
            )

            if latest_outline:
                # Check if all sections have content
                outline_structure = latest_outline.get_outline_structure()
                total_sections = 2  # Introduction and Conclusion
                if "sections" in outline_structure:
                    total_sections += len(outline_structure["sections"])

                content_count = ResearchContent.query.filter_by(
                    project_id=project.id, outline_id=latest_outline.id
                ).count()

                if content_count >= total_sections:
                    completed_projects += 1

        # Get recent activity (last 5 actions)
        recent_activity = 0
        activities = []

        # For now, we'll just count the number of projects created in the last 7 days
        recent_date = datetime.now() - timedelta(days=7)
        recent_activity = ResearchProject.query.filter(
            ResearchProject.user_id == int(user_id),
            ResearchProject.created_at >= recent_date,
        ).count()

        # Create some sample activities
        if projects:
            for project in projects[:3]:  # Take up to 3 most recent projects
                activities.append(
                    {
                        "title": f"Project Created: {project.title}",
                        "description": (
                            project.description[:100] + "..."
                            if project.description and len(project.description) > 100
                            else project.description or "No description"
                        ),
                        "timestamp": project.created_at.strftime("%Y-%m-%d %H:%M"),
                    }
                )

                # Get latest outline for this project
                latest_outline = (
                    ResearchOutline.query.filter_by(project_id=project.id)
                    .order_by(ResearchOutline.created_at.desc())
                    .first()
                )

                if latest_outline:
                    activities.append(
                        {
                            "title": f"Outline Generated: {project.title}",
                            "description": f"A {latest_outline.total_pages}-page outline was created",
                            "timestamp": latest_outline.created_at.strftime(
                                "%Y-%m-%d %H:%M"
                            ),
                        }
                    )

        return render_template(
            "dashboard.html",
            user=user,
            current_user=user,
            projects=projects,
            completed_projects=completed_projects,
            recent_activity=recent_activity,
            activities=activities,
            now=datetime.now(),
        )
    except Exception as e:
        print(f"Dashboard error: {str(e)}")
        return redirect(url_for("auth_views.login"))
