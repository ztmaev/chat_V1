#!/usr/bin/env python3
"""
Firebase Authentication Diagnostic Tool

This script helps diagnose "Invalid Firebase ID token" errors by checking:
1. Firebase Admin SDK initialization
2. Service account credentials
3. Token verification
"""

import os
import sys
import json

def check_firebase_credentials():
    """Check if Firebase credentials are available"""
    print("\n" + "="*80)
    print("FIREBASE CREDENTIALS CHECK")
    print("="*80 + "\n")
    
    # Check for service account key file
    service_account_path = os.environ.get('FIREBASE_SERVICE_ACCOUNT_KEY', 'serviceAccountKey.json')
    
    if os.path.exists(service_account_path):
        print(f"✅ Service account key file found: {service_account_path}")
        try:
            with open(service_account_path, 'r') as f:
                data = json.load(f)
                print(f"   Project ID: {data.get('project_id', 'NOT FOUND')}")
                print(f"   Client Email: {data.get('client_email', 'NOT FOUND')}")
                print(f"   Private Key: {'Present' if data.get('private_key') else 'MISSING'}")
            return True
        except Exception as e:
            print(f"❌ Error reading service account key: {e}")
            return False
    
    # Check for environment variable
    service_account_json = os.environ.get('FIREBASE_SERVICE_ACCOUNT_JSON')
    if service_account_json:
        print("✅ Service account JSON found in environment variable")
        try:
            data = json.loads(service_account_json)
            print(f"   Project ID: {data.get('project_id', 'NOT FOUND')}")
            print(f"   Client Email: {data.get('client_email', 'NOT FOUND')}")
            return True
        except Exception as e:
            print(f"❌ Error parsing service account JSON: {e}")
            return False
    
    print("❌ No Firebase credentials found!")
    print("   Set FIREBASE_SERVICE_ACCOUNT_KEY or FIREBASE_SERVICE_ACCOUNT_JSON")
    return False


def test_firebase_initialization():
    """Test Firebase Admin SDK initialization"""
    print("\n" + "="*80)
    print("FIREBASE INITIALIZATION TEST")
    print("="*80 + "\n")
    
    try:
        from firebase_auth import initialize_firebase
        initialize_firebase()
        print("✅ Firebase Admin SDK initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Firebase initialization failed: {e}")
        return False


def test_token_verification(token=None):
    """Test token verification"""
    print("\n" + "="*80)
    print("TOKEN VERIFICATION TEST")
    print("="*80 + "\n")
    
    if not token:
        print("ℹ️  No token provided. Skipping token verification test.")
        print("   To test a token, run: python3 diagnose_firebase_auth.py <token>")
        return None
    
    try:
        from firebase_auth import verify_firebase_token
        decoded = verify_firebase_token(token)
        print("✅ Token is valid!")
        print(f"   User ID: {decoded.get('uid', 'NOT FOUND')}")
        print(f"   Email: {decoded.get('email', 'NOT FOUND')}")
        print(f"   Email Verified: {decoded.get('email_verified', False)}")
        
        # Check token expiration
        import time
        exp = decoded.get('exp', 0)
        iat = decoded.get('iat', 0)
        now = int(time.time())
        
        if exp:
            time_until_expiry = exp - now
            if time_until_expiry > 0:
                print(f"   Expires in: {time_until_expiry // 60} minutes")
            else:
                print(f"   ⚠️  Token expired {abs(time_until_expiry) // 60} minutes ago")
        
        if iat:
            token_age = now - iat
            print(f"   Token age: {token_age // 60} minutes")
        
        return True
    except Exception as e:
        print(f"❌ Token verification failed: {e}")
        print(f"   Token preview: {token[:50]}..." if len(token) > 50 else f"   Token: {token}")
        return False


def check_firebase_project():
    """Check Firebase project configuration"""
    print("\n" + "="*80)
    print("FIREBASE PROJECT CHECK")
    print("="*80 + "\n")
    
    service_account_path = os.environ.get('FIREBASE_SERVICE_ACCOUNT_KEY', 'serviceAccountKey.json')
    
    if os.path.exists(service_account_path):
        try:
            with open(service_account_path, 'r') as f:
                data = json.load(f)
                project_id = data.get('project_id')
                
                print(f"Backend Firebase Project: {project_id}")
                print("\nℹ️  Ensure frontend uses the same project ID:")
                print(f"   NEXT_PUBLIC_FIREBASE_PROJECT_ID={project_id}")
                print("\n   Check .env.local file in the root directory")
                
                # Try to read .env.local
                env_path = '../.env.local'
                if os.path.exists(env_path):
                    print(f"\n✅ Found .env.local file")
                    with open(env_path, 'r') as env_file:
                        for line in env_file:
                            if 'FIREBASE_PROJECT_ID' in line:
                                print(f"   {line.strip()}")
                                frontend_project = line.split('=')[1].strip()
                                if frontend_project == project_id:
                                    print("   ✅ Frontend and backend projects MATCH")
                                else:
                                    print(f"   ❌ Frontend project ({frontend_project}) != Backend project ({project_id})")
                else:
                    print(f"\n⚠️  .env.local not found at {env_path}")
                
        except Exception as e:
            print(f"❌ Error checking project: {e}")


def main():
    """Run all diagnostic checks"""
    print("\n🔍 Firebase Authentication Diagnostic Tool")
    print("="*80)
    
    # Get token from command line if provided
    token = sys.argv[1] if len(sys.argv) > 1 else None
    
    # Run checks
    creds_ok = check_firebase_credentials()
    init_ok = test_firebase_initialization() if creds_ok else False
    token_ok = test_token_verification(token) if init_ok and token else None
    check_firebase_project()
    
    # Summary
    print("\n" + "="*80)
    print("DIAGNOSTIC SUMMARY")
    print("="*80)
    print(f"Firebase Credentials: {'✅ OK' if creds_ok else '❌ FAILED'}")
    print(f"Firebase Initialization: {'✅ OK' if init_ok else '❌ FAILED'}")
    if token_ok is not None:
        print(f"Token Verification: {'✅ OK' if token_ok else '❌ FAILED'}")
    else:
        print(f"Token Verification: ⏭️  SKIPPED (no token provided)")
    print("="*80)
    
    # Recommendations
    print("\n📋 RECOMMENDATIONS:")
    if not creds_ok:
        print("  1. Add Firebase service account key to serviceAccountKey.json")
        print("  2. Or set FIREBASE_SERVICE_ACCOUNT_JSON environment variable")
    elif not init_ok:
        print("  1. Check service account key format (must be valid JSON)")
        print("  2. Ensure service account has proper permissions")
    elif token_ok is False:
        print("  1. Token may be from wrong Firebase project")
        print("  2. Token may be expired (check expiration time above)")
        print("  3. Token may be malformed")
        print("  4. Ensure frontend and backend use same Firebase project")
    elif token_ok is None:
        print("  1. Test with a real token: python3 diagnose_firebase_auth.py <token>")
        print("  2. Get token from browser console:")
        print("     import { ensureAdminFirebaseUser } from '@/lib/admin-messaging-api';")
        print("     const token = await ensureAdminFirebaseUser();")
        print("     console.log(token);")
    else:
        print("  ✅ Everything looks good!")
        print("  If you're still getting errors, check:")
        print("    - Network connectivity to Firebase")
        print("    - Server time (clock skew can cause issues)")
        print("    - Backend logs for specific error messages")
    
    print("\n")


if __name__ == "__main__":
    main()
