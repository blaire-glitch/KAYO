# WSGI entry point for PythonAnywhere
import sys
import os

# Add your project directory to the sys.path
# Replace 'yourusername' with your actual PythonAnywhere username
project_home = '/home/yourusername/KAYO'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Load environment variables from .env file
from dotenv import load_dotenv
env_path = os.path.join(project_home, '.env')
load_dotenv(env_path)

# Import and create the Flask application
from app import create_app

application = create_app()
