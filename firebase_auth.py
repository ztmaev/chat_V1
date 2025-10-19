"""
Firebase Admin Authentication Module
Handles Firebase ID token verification for secure API access
"""

import os
import json
from functools import wraps
from flask import request, jsonify
import firebase_admin
from firebase_admin import credentials, auth

# Initialize Firebase Admin SDK
_firebase_initialized = False

def initialize_firebase():
    """Initialize Firebase Admin SDK with service account credentials"""
    global _firebase_initialized
    
    if _firebase_initialized:
        return
    
    try:
        # Try to load from service account key file
        service_account_path = os.environ.get('FIREBASE_SERVICE_ACCOUNT_KEY', 'serviceAccountKey.json')
        
        if os.path.exists(service_account_path):
            cred = credentials.Certificate(service_account_path)
            firebase_admin.initialize_app(cred)
            print(f"✅ Firebase Admin initialized with service account: {service_account_path}")
        else:
            # Try to load from environment variable (JSON string)
            service_account_json = os.environ.get('FIREBASE_SERVICE_ACCOUNT_JSON')
            
            if service_account_json:
                service_account_dict = json.loads(service_account_json)
                cred = credentials.Certificate(service_account_dict)
                firebase_admin.initialize_app(cred)
                print("✅ Firebase Admin initialized with environment variable credentials")
            else:
                print("⚠️  WARNING: No Firebase credentials found. Authentication will fail.")
                print("   Set FIREBASE_SERVICE_ACCOUNT_KEY or FIREBASE_SERVICE_ACCOUNT_JSON")
                return
        
        _firebase_initialized = True
        
    except Exception as e:
        print(f"❌ Failed to initialize Firebase Admin: {str(e)}")
        raise

def verify_firebase_token(id_token):
    """
    Verify Firebase ID token and return decoded token
    
    Args:
        id_token (str): Firebase ID token from client
        
    Returns:
        dict: Decoded token with user information
        
    Raises:
        Exception: If token is invalid or expired
    """
    try:
        # Verify the ID token
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token
    except auth.InvalidIdTokenError:
        raise Exception("Invalid Firebase ID token")
    except auth.ExpiredIdTokenError:
        raise Exception("Firebase ID token has expired")
    except auth.RevokedIdTokenError:
        raise Exception("Firebase ID token has been revoked")
    except Exception as e:
        raise Exception(f"Token verification failed: {str(e)}")

def get_token_from_request():
    """
    Extract Firebase ID token from request headers
    
    Returns:
        str: Firebase ID token or None
    """
    # Check Authorization header (Bearer token)
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        return auth_header.split('Bearer ')[1]
    
    # Check X-Firebase-Token header (alternative)
    firebase_token = request.headers.get('X-Firebase-Token')
    if firebase_token:
        return firebase_token
    
    return None

def require_auth(f):
    """
    Decorator to require Firebase authentication for API endpoints
    
    Usage:
        @app.route('/protected')
        @require_auth
        def protected_route():
            # Access user info via request.user
            user_id = request.user['uid']
            user_email = request.user['email']
            return jsonify({'message': 'Success'})
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get token from request
        id_token = get_token_from_request()
        
        if not id_token:
            return jsonify({
                'error': 'Authentication required',
                'message': 'No Firebase ID token provided. Include token in Authorization header as "Bearer <token>"'
            }), 401
        
        try:
            # Verify token
            decoded_token = verify_firebase_token(id_token)
            
            # Ensure decoded_token is a dictionary
            if not isinstance(decoded_token, dict):
                return jsonify({
                    'error': 'Authentication failed',
                    'message': f'Invalid token format: expected dict, got {type(decoded_token).__name__}'
                }), 401
            
            # Attach user info to request object
            request.user = decoded_token
            
            # Call the original function
            return f(*args, **kwargs)
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"❌ Authentication error: {error_details}")
            return jsonify({
                'error': 'Authentication failed',
                'message': str(e)
            }), 401
    
    return decorated_function

def optional_auth(f):
    """
    Decorator for optional authentication
    Attaches user info if token is valid, but doesn't require it
    
    Usage:
        @app.route('/public')
        @optional_auth
        def public_route():
            if hasattr(request, 'user'):
                # User is authenticated
                user_id = request.user['uid']
            else:
                # Anonymous access
                pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get token from request
        id_token = get_token_from_request()
        
        if id_token:
            try:
                # Verify token
                decoded_token = verify_firebase_token(id_token)
                request.user = decoded_token
            except Exception:
                # Token invalid, but continue without auth
                pass
        
        return f(*args, **kwargs)
    
    return decorated_function

def get_current_user():
    """
    Get current authenticated user from request
    
    Returns:
        dict: User info from decoded token or None
    """
    return getattr(request, 'user', None)

def require_role(required_role):
    """
    Decorator to require specific user role
    Assumes role is stored in Firestore user profile
    
    Usage:
        @app.route('/admin')
        @require_auth
        @require_role('admin')
        def admin_route():
            return jsonify({'message': 'Admin access'})
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            
            if not user:
                return jsonify({
                    'error': 'Authentication required',
                    'message': 'User must be authenticated'
                }), 401
            
            # Check role from custom claims
            user_role = user.get('role') or user.get('custom_claims', {}).get('role')
            
            if user_role != required_role:
                return jsonify({
                    'error': 'Forbidden',
                    'message': f'This endpoint requires {required_role} role'
                }), 403
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator
