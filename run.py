from app import create_app, db
from app.models.user import User
from app.models.research import ResearchProject, ResearchOutline
from app.models.content import ResearchContent
import os

app = create_app(os.environ.get('FLASK_ENV', 'production'))

@app.shell_context_processor
def make_shell_context():
    """Add database and models to flask shell context"""
    return {
        'db': db, 
        'User': User, 
        'ResearchProject': ResearchProject,
        'ResearchOutline': ResearchOutline,
        'ResearchContent': ResearchContent
    }

def create_admin_user():
    """Create admin user if none exists"""
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

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        create_admin_user()
    # Use host and port from environment variables for deployment
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host=host, port=port, debug=debug)