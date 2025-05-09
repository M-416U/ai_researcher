from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager, get_jwt_identity
import os
from dotenv import load_dotenv
from datetime import datetime
import atexit
from apscheduler.schedulers.background import BackgroundScheduler

# Load environment variables
load_dotenv()

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
scheduler = BackgroundScheduler()

from app.models import *


def init_db(app):
    """Initialize database and create admin user if needed"""
    with app.app_context():
        db.create_all()
        from app.models.user import User

        admin = User.query.filter_by(is_admin=True).first()
        if not admin:
            username = os.environ.get("ADMIN_USERNAME", "admin")
            email = os.environ.get("ADMIN_EMAIL", "admin@example.com")
            password = os.environ.get("ADMIN_PASSWORD", "adminpassword")

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
    db_path = os.path.join(os.getcwd(), "app.db")
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
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

    def setup_database():
        from app import init_db

        init_db(app)

    # At the end of the function, before returning app:
    @app.cli.command("init-db")
    def initialize_db():
        """Flask CLI command to initialize database with admin user"""
        init_db(app)
        print("Database initialized with admin user")

    # Set up scheduled tasks
    with app.app_context():
        from app.services.export_service import ExportService
        
        # Schedule export cleanup task to run every hour
        def cleanup_exports_job():
            with app.app_context():
                result = ExportService.cleanup_exports(max_age_hours=1)
                app.logger.info(f"Scheduled export cleanup: {result['message']}")
        
        # Add the job to the scheduler
        scheduler.add_job(func=cleanup_exports_job, trigger="interval", hours=1, id="cleanup_exports")
        
        # Start the scheduler if it's not already running
        if not scheduler.running:
            scheduler.start()
            
        # Shut down the scheduler when the app exits
        atexit.register(lambda: scheduler.shutdown())

    setup_database()
    return app
