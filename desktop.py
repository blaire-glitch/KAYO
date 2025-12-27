"""
KAYO Desktop Application
Launches the KAYO Flask app in a native desktop window.
"""
import sys
import os

# Handle PyInstaller bundled environment
if getattr(sys, 'frozen', False):
    # Running as compiled exe
    BASE_DIR = sys._MEIPASS
    # Set the working directory to where the exe is located for database access
    os.chdir(os.path.dirname(sys.executable))
else:
    # Running as script
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Ensure the app directory is in path
sys.path.insert(0, BASE_DIR)

# Set environment variable for Flask to find templates
os.environ['FLASK_APP_BASE'] = BASE_DIR

from flaskwebgui import FlaskUI
from app import create_app, db
from app.models import User
from werkzeug.security import generate_password_hash

def main():
    """Launch KAYO as a desktop application."""
    # Create the Flask app
    app = create_app()
    
    # Override template and static folders for PyInstaller
    if getattr(sys, 'frozen', False):
        app.template_folder = os.path.join(BASE_DIR, 'app', 'templates')
        app.static_folder = os.path.join(BASE_DIR, 'app', 'static')
    
    # Ensure database tables exist and create default admin
    with app.app_context():
        db.create_all()
        print("Database tables verified/created.")
        
        # Create default admin if no users exist
        if User.query.count() == 0:
            admin = User(
                name='Admin',
                email='admin@kayo.com',
                phone='0700000000',
                role='admin',
                password_hash=generate_password_hash('admin123'),
                is_approved=True,
                approval_status='approved',
                is_active=True
            )
            db.session.add(admin)
            db.session.commit()
            print("Default admin created: admin@kayo.com / admin123")
    
    # Configure FlaskUI
    # Uses Chrome/Edge in app mode for native-like experience
    ui = FlaskUI(
        app=app,
        server="flask",
        width=1400,
        height=900,
        fullscreen=False,
        browser_path=None,  # Auto-detect Chrome/Edge
    )
    
    # Run the desktop app
    ui.run()


if __name__ == "__main__":
    main()
