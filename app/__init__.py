from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager, get_jwt_identity
import os
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()

from app.models import *

def init_db(app):
    """Initialize database and create admin user if needed"""
    with app.app_context():
        db.create_all()
        # Check if admin user exists
        from app.models.user import User
        admin = User.query.filter_by(is_admin=True).first()
        if not admin:
            username = os.environ.get('ADMIN_USERNAME', 'admin')
            email = os.environ.get('ADMIN_EMAIL', 'admin@example.com')
            password = os.environ.get('ADMIN_PASSWORD', 'adminpassword')
            
            admin = User(username=username, email=email, is_admin=True)
            admin.set_password(password)
            db.session.add(admin)
            db.session.commit()
            print(f"Admin user created: {username}")
        else:
            print("Admin user already exists")


def create_app(config_name="development"):
    """Application factory function"""
    app = Flask(__name__, template_folder="templates", static_folder="static")

    # Configure the app
    if config_name == "development":
        app.config.from_object("config.DevelopmentConfig")
    elif config_name == "production":
        app.config.from_object("config.ProductionConfig")
    elif config_name == "testing":
        app.config.from_object("config.TestingConfig")

    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    # Register blueprints
    # from app.api.routes import api_bp
    from app.api.auth import auth_bp
    from app.api.research import research_bp
    from app.api.content import content_bp
    from app.api.export import export_bp
    from app.views.main import main_bp
    from app.views.auth import auth_views_bp
    from app.views.research import research_views_bp

    # Add this import at the top with your other blueprint imports
    from app.views.admin import admin_bp

    # Add this line where you register your other blueprints
    app.register_blueprint(admin_bp)
    # app.register_blueprint(api_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(research_bp)
    app.register_blueprint(content_bp)
    app.register_blueprint(export_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_views_bp)
    app.register_blueprint(research_views_bp)

    # Add context processor for templates
    @app.context_processor
    def inject_user():
        from app.models.user import User

        user = None
        try:
            user_id = get_jwt_identity()
            if user_id:
                user = User.query.get(user_id)
        except:
            pass
        return {"current_user": user, "now": datetime.now()}

    # At the end of the function, before returning app:
    @app.cli.command("init-db")
    def initialize_db():
        """Flask CLI command to initialize database with admin user"""
        init_db(app)
        print("Database initialized with admin user")

    return app
