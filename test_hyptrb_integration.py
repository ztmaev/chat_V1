#!/usr/bin/env python3
"""
Test script for Hyptrb API integration
Tests fetching user roles and profiles from the Hyptrb API
"""
import sys
from hyptrb_api import (
    fetch_user_role,
    fetch_client_profile,
    fetch_admin_profile,
    fetch_influencer_profile,
    fetch_user_profile_by_role,
    extract_display_name,
    HyptrbAPIError
)

def test_fetch_role(email: str):
    """Test fetching user role"""
    print(f"\n{'='*60}")
    print(f"Testing: Fetch role for {email}")
    print('='*60)
    try:
        result = fetch_user_role(email)
        if result:
            print(f"✅ Success!")
            print(f"   Role: {result.get('role')}")
            print(f"   Email: {result.get('email')}")
            print(f"   Created: {result.get('createdAt')}")
            return result.get('role')
        else:
            print(f"❌ No role found for {email}")
            return None
    except HyptrbAPIError as e:
        print(f"❌ Error: {e}")
        return None

def test_fetch_client_profile(email: str):
    """Test fetching client profile"""
    print(f"\n{'='*60}")
    print(f"Testing: Fetch client profile for {email}")
    print('='*60)
    try:
        result = fetch_client_profile(email)
        if result:
            print(f"✅ Success!")
            print(f"   Business Name: {result.get('businessName')}")
            print(f"   Business Mode: {result.get('businessMode')}")
            print(f"   Industry: {result.get('industry')}")
            print(f"   Verification Status: {result.get('verificationStatus')}")
            display_name = extract_display_name(result, 'client')
            print(f"   Display Name: {display_name}")
            return result
        else:
            print(f"❌ No profile found for {email}")
            return None
    except HyptrbAPIError as e:
        print(f"❌ Error: {e}")
        return None

def test_fetch_influencer_profile(uid: str):
    """Test fetching influencer profile"""
    print(f"\n{'='*60}")
    print(f"Testing: Fetch influencer profile for {uid}")
    print('='*60)
    try:
        result = fetch_influencer_profile(uid)
        if result:
            print(f"✅ Success!")
            print(f"   Full Name: {result.get('full_name')}")
            print(f"   Contact Email: {result.get('contact_email')}")
            print(f"   Contact Phone: {result.get('contact_phone')}")
            print(f"   Gender: {result.get('gender')}")
            print(f"   Age: {result.get('age')}")
            print(f"   Verification Status: {result.get('verification_status')}")
            display_name = extract_display_name(result, 'influencer')
            print(f"   Display Name: {display_name}")
            return result
        else:
            print(f"❌ No profile found for {uid}")
            return None
    except HyptrbAPIError as e:
        print(f"❌ Error: {e}")
        return None

def test_full_workflow(email: str):
    """Test complete workflow: role fetch → profile fetch"""
    print(f"\n{'='*60}")
    print(f"Testing: Complete workflow for {email}")
    print('='*60)
    
    # Step 1: Fetch role
    print("\n📋 Step 1: Fetching user role...")
    role = test_fetch_role(email)
    
    if not role:
        print("❌ Cannot continue without role")
        return
    
    # Step 2: Fetch profile based on role
    print(f"\n📋 Step 2: Fetching {role} profile...")
    try:
        if role == 'client':
            profile = fetch_client_profile(email)
        elif role == 'influencer':
            # For influencer, we'd need the UID - using email as placeholder
            print("⚠️  Note: For influencer, we need the Firebase UID")
            profile = None
        elif role == 'admin':
            profile = fetch_admin_profile(email)
        else:
            print(f"❌ Unknown role: {role}")
            profile = None
        
        if profile:
            display_name = extract_display_name(profile, role)
            print(f"\n✅ Complete workflow successful!")
            print(f"   Email: {email}")
            print(f"   Role: {role}")
            print(f"   Display Name: {display_name}")
        else:
            print(f"❌ Profile not found")
    except HyptrbAPIError as e:
        print(f"❌ Error fetching profile: {e}")

def main():
    """Run tests"""
    print("\n" + "="*60)
    print("🧪 Hyptrb API Integration Tests")
    print("="*60)
    
    # Test with known emails from the requirements
    test_emails = [
        "maevorian@gmail.com",  # From role API example
        "test03@gmail.com",      # From client API example
    ]
    
    test_influencer_uid = "5c1QXpqdW8OHYJlSMftYNSld5j73"  # From influencer API example
    
    # Test role fetching
    for email in test_emails:
        test_fetch_role(email)
    
    # Test client profile
    test_fetch_client_profile("test03@gmail.com")
    
    # Test influencer profile
    test_fetch_influencer_profile(test_influencer_uid)
    
    # Test complete workflow
    test_full_workflow("maevorian@gmail.com")
    test_full_workflow("test03@gmail.com")
    
    print("\n" + "="*60)
    print("✅ Tests completed!")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
