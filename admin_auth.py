"""
Admin authentication module for management pages
Uses session-based authentication with credentials from environment variables
"""
from functools import wraps
from flask import session, redirect, url_for, request
import os


def check_admin_credentials(username: str, password: str) -> bool:
    """
    Verify admin credentials against environment variables
    
    Args:
        username: Provided username
        password: Provided password
    
    Returns:
        True if credentials are valid, False otherwise
    """
    admin_username = os.getenv('ADMIN_USERNAME')
    admin_password = os.getenv('ADMIN_PASSWORD')
    
    if not admin_username or not admin_password:
        print("⚠️  Warning: ADMIN_USERNAME or ADMIN_PASSWORD not set in environment")
        return False
    
    return username == admin_username and password == admin_password


def is_admin_authenticated() -> bool:
    """
    Check if current session is authenticated as admin
    
    Returns:
        True if authenticated, False otherwise
    """
    return session.get('admin_authenticated', False)


def require_admin_auth(f):
    """
    Decorator to protect admin routes
    Redirects to login page if not authenticated
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_admin_authenticated():
            # Store the original URL to redirect back after login
            session['next_url'] = request.url
            return redirect(url_for('admin_blueprint.login'))
        return f(*args, **kwargs)
    return decorated_function
