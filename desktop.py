"""
KAYO Desktop Application
Launches the KAYO Flask app in a native desktop window.
"""
import sys
import os
import webbrowser
import threading
import time

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

from app import create_app, db
from app.models import User
from werkzeug.security import generate_password_hash

def open_browser(port):
    """Open browser after a short delay."""
    time.sleep(1.5)
    webbrowser.open(f'http://127.0.0.1:{port}')

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
    
    port = 5000
    print(f"\n{'='*50}")
    print("KAYO Desktop Application")
    print(f"{'='*50}")
    print(f"Server starting on http://127.0.0.1:{port}")
    print("Opening in your default browser...")
    print("Press Ctrl+C to stop the server")
    print(f"{'='*50}\n")
    
    # Open browser in background thread
    threading.Thread(target=open_browser, args=(port,), daemon=True).start()
    
    # Run Flask server
    app.run(host='127.0.0.1', port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
