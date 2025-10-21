#!/usr/bin/env python3
"""
Startup script for Azure Communication Services Python Application
This script handles environment setup, dependency installation, and application startup.
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("Error: Python 3.8 or higher is required")
        print(f"Current version: {sys.version}")
        sys.exit(1)
    print(f"✓ Python version: {sys.version.split()[0]}")

def create_virtual_environment():
    """Create virtual environment if it doesn't exist"""
    venv_path = Path("venv")
    
    if not venv_path.exists():
        print("Creating virtual environment...")
        subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
        print("✓ Virtual environment created")
    else:
        print("✓ Virtual environment already exists")
    
    return venv_path

def get_venv_python(venv_path):
    """Get the Python executable path in the virtual environment"""
    if platform.system() == "Windows":
        return venv_path / "Scripts" / "python.exe"
    else:
        return venv_path / "bin" / "python"

def get_venv_pip(venv_path):
    """Get the pip executable path in the virtual environment"""
    if platform.system() == "Windows":
        return venv_path / "Scripts" / "pip.exe"
    else:
        return venv_path / "bin" / "pip"

def install_dependencies(venv_path):
    """Install Python dependencies"""
    pip_exe = get_venv_pip(venv_path)
    requirements_file = Path("requirements.txt")
    
    if not requirements_file.exists():
        print("Warning: requirements.txt not found")
        return
    
    print("Installing dependencies...")
    subprocess.run([
        str(pip_exe), "install", "-r", "requirements.txt"
    ], check=True)
    print("✓ Dependencies installed")

def setup_environment():
    """Setup environment configuration"""
    env_file = Path(".env")
    env_template = Path(".env.python.template")
    
    if not env_file.exists() and env_template.exists():
        print("Creating .env file from template...")
        with open(env_template, 'r') as template:
            content = template.read()
        
        with open(env_file, 'w') as env:
            env.write(content)
        
        print("✓ .env file created from template")
        print("Please edit .env file with your actual configuration values")
    elif env_file.exists():
        print("✓ .env file already exists")
    else:
        print("Warning: No environment configuration found")

def check_environment_variables():
    """Check if required environment variables are set"""
    required_vars = [
        'CONNECTION_STRING',
        'ACS_RESOURCE_PHONE_NUMBER',
        'CALLBACK_URI'
    ]
    
    # Load .env file manually for checking
    env_file = Path(".env")
    env_vars = {}
    
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key] = value
    
    missing_vars = []
    for var in required_vars:
        if var not in env_vars or not env_vars[var] or env_vars[var].startswith('your_'):
            missing_vars.append(var)
    
    if missing_vars:
        print("⚠️  Warning: Missing or incomplete environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("Please update your .env file with actual values")
    else:
        print("✓ All required environment variables are configured")

def start_application(venv_path):
    """Start the Flask application from main.py"""
    import webbrowser
    import time
    import threading
    
    # Check if main.py exists
    main_file = Path("main.py")
    if not main_file.exists():
        print("Error: main.py not found")
        sys.exit(1)
    
    # Check if template/index.html exists
    template_dir = Path("template")
    index_file = template_dir / "index.html"
    
    if not index_file.exists():
        print("Error: template/index.html not found")
        sys.exit(1)
    
    # Set environment variables for the Flask app
    os.environ['PORT'] = '8080'
    
    # Get the Python executable from virtual environment
    python_exe = get_venv_python(venv_path)
    
    print("Starting Azure Communication Services Python Application...")
    print(f"Using Python: {python_exe}")
    
    def start_flask_app():
        """Start the Flask application in a separate thread"""
        try:
            subprocess.run([
                str(python_exe), "main.py"
            ], check=True, cwd=str(Path.cwd()))
        except subprocess.CalledProcessError as e:
            print(f"Flask application exited with error: {e}")
        except Exception as e:
            print(f"Error running Flask application: {e}")
    
    try:
        # Start Flask app in background thread
        flask_thread = threading.Thread(target=start_flask_app, daemon=True)
        flask_thread.start()
        
        # Wait a moment for Flask to start
        print("Waiting for Flask application to start...")
        time.sleep(3)
        
        # Open browser to the Flask application
        app_url = "http://localhost:8080"
        print(f"Opening application at: {app_url}")
        webbrowser.open(app_url)
        
        print("✓ Application opened in browser")
        print("✓ Flask application is running")
        print("\nPress Ctrl+C to stop the server...")
        
        # Keep the main thread alive
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n✓ Server stopped by user")
            
    except Exception as e:
        print(f"Error starting application: {e}")
        sys.exit(1)

def main():
    """Main setup and startup function"""
    print("=== Azure Communication Services Python Application Setup ===")
    print()
    
    # Check Python version
    check_python_version()
    
    # Create virtual environment
    venv_path = create_virtual_environment()
    
    # Install dependencies
    install_dependencies(venv_path)
    
    # Setup environment
    setup_environment()
    
    # Check environment variables
    check_environment_variables()
    
    print()
    print("=== Setup Complete ===")
    print()
    
    # Start application
    start_application(venv_path)

if __name__ == "__main__":
    main()