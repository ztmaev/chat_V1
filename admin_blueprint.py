"""
Admin management blueprint
Provides secure access to status pages and statistics
"""
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
from datetime import datetime, timedelta
import time
from admin_auth import check_admin_credentials, require_admin_auth, is_admin_authenticated
from db import get_db

# Track start time for uptime
START_TIME = time.time()

# Create blueprint
admin_blueprint = Blueprint('admin_blueprint', __name__, url_prefix='/admin')

# Get database instance
db = get_db()


@admin_blueprint.route('/login', methods=['GET', 'POST'])
def login():
    """Admin login page"""
    # If already authenticated, redirect to dashboard
    if is_admin_authenticated():
        return redirect(url_for('admin_blueprint.dashboard'))
    
    error = None
    
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        
        if check_admin_credentials(username, password):
            # Set session as authenticated
            session['admin_authenticated'] = True
            session['admin_username'] = username
            session.permanent = True  # Make session persistent
            
            # Redirect to original URL or dashboard
            next_url = session.pop('next_url', None)
            if next_url:
                return redirect(next_url)
            return redirect(url_for('admin_blueprint.dashboard'))
        else:
            error = 'Invalid username or password'
    
    return render_template('admin/login.html', error=error)


@admin_blueprint.route('/logout', methods=['GET', 'POST'])
def logout():
    """Admin logout"""
    session.pop('admin_authenticated', None)
    session.pop('admin_username', None)
    session.pop('next_url', None)
    return redirect(url_for('admin_blueprint.login'))


@admin_blueprint.route('/dashboard')
@require_admin_auth
def dashboard():
    """Admin dashboard - main status page"""
    # Calculate uptime
    uptime_seconds = int(time.time() - START_TIME)
    uptime_delta = timedelta(seconds=uptime_seconds)
    
    # Format uptime
    days = uptime_delta.days
    hours, remainder = divmod(uptime_delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    if days > 0:
        uptime_str = f"{days}d {hours}h {minutes}m"
    elif hours > 0:
        uptime_str = f"{hours}h {minutes}m"
    else:
        uptime_str = f"{minutes}m {seconds}s"
    
    # Check database status
    try:
        stats = db.get_stats()
        database_status = {"text": "Connected", "icon": "fa-check-circle", "color": "#3fb950"}
    except:
        database_status = {"text": "Error", "icon": "fa-times-circle", "color": "#f85149"}
    
    # Check Firebase status (import here to avoid circular dependency)
    from app import FIREBASE_INITIALIZED
    if FIREBASE_INITIALIZED:
        firebase_status = {"text": "Active", "icon": "fa-check-circle", "color": "#3fb950"}
    else:
        firebase_status = {"text": "Not Configured", "icon": "fa-exclamation-triangle", "color": "#d29922"}
    
    return render_template('admin/dashboard.html',
        status="Online",
        version="1.0.0",
        uptime=uptime_str,
        database_status=database_status,
        firebase_status=firebase_status,
        admin_username=session.get('admin_username', 'Admin')
    )




@admin_blueprint.route('/docs')
@require_admin_auth
def docs():
    """Admin API documentation page"""
    return render_template('admin/docs_full.html',
        admin_username=session.get('admin_username', 'Admin')
    )


@admin_blueprint.route('/api/stats')
@require_admin_auth
def api_stats():
    """API endpoint for stats (JSON)"""
    stats = db.get_stats()
    
    # Calculate uptime
    uptime_seconds = int(time.time() - START_TIME)
    uptime_delta = timedelta(seconds=uptime_seconds)
    
    # Format uptime
    days = uptime_delta.days
    hours, remainder = divmod(uptime_delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    if days > 0:
        uptime_str = f"{days}d {hours}h {minutes}m"
    elif hours > 0:
        uptime_str = f"{hours}h {minutes}m"
    else:
        uptime_str = f"{minutes}m {seconds}s"
    
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'uptime': uptime_str,
        'stats': stats
    })


# ============================================================================
# HTMX Content Endpoints (for SPA navigation)
# ============================================================================

@admin_blueprint.route('/dashboard/content')
@require_admin_auth
def dashboard_content():
    """Dashboard content only (for HTMX)"""
    # Calculate uptime
    uptime_seconds = int(time.time() - START_TIME)
    uptime_delta = timedelta(seconds=uptime_seconds)
    
    # Format uptime
    days = uptime_delta.days
    hours, remainder = divmod(uptime_delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    if days > 0:
        uptime_str = f"{days}d {hours}h {minutes}m"
    elif hours > 0:
        uptime_str = f"{hours}h {minutes}m"
    else:
        uptime_str = f"{minutes}m {seconds}s"
    
    # Check database status
    try:
        stats = db.get_stats()
        database_status = {"text": "Connected", "icon": "fa-check-circle", "color": "#3fb950"}
    except:
        database_status = {"text": "Error", "icon": "fa-times-circle", "color": "#f85149"}
    
    # Check Firebase status
    from app import FIREBASE_INITIALIZED
    if FIREBASE_INITIALIZED:
        firebase_status = {"text": "Active", "icon": "fa-check-circle", "color": "#3fb950"}
    else:
        firebase_status = {"text": "Not Configured", "icon": "fa-exclamation-triangle", "color": "#d29922"}
    
    return render_template('admin/dashboard_content.html',
        status="Online",
        version="1.0.0",
        uptime=uptime_str,
        database_status=database_status,
        firebase_status=firebase_status
    )




@admin_blueprint.route('/docs/content')
@require_admin_auth
def docs_content():
    """Docs content only (for HTMX)"""
    return render_template('admin/docs.html')
