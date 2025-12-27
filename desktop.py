"""
KAYO Desktop Application
Launches the KAYO Flask app in a native desktop window.
"""
import sys
import os

# Ensure the app directory is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flaskwebgui import FlaskUI
from app import create_app

def main():
    """Launch KAYO as a desktop application."""
    # Create the Flask app
    app = create_app()
    
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
