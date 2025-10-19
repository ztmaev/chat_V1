#!/usr/bin/env python3
"""
Test script for the admin join campaign endpoint
Demonstrates how admins can join campaign threads
"""

import requests
import json

# Configuration
API_BASE_URL = "http://localhost:5000"  # Adjust to your API URL
ADMIN_FIREBASE_TOKEN = "YOUR_ADMIN_FIREBASE_TOKEN_HERE"  # Replace with actual admin token
CAMPAIGN_ID = "68ba588b8500561576b8f3fd"  # Replace with actual campaign ID

def test_admin_join_campaign():
    """
    Test the admin join campaign endpoint
    """
    print("=" * 60)
    print("Testing Admin Join Campaign Endpoint")
    print("=" * 60)
    
    # Endpoint URL
    url = f"{API_BASE_URL}/messages/campaigns/{CAMPAIGN_ID}/join"
    
    # Headers with Firebase authentication
    headers = {
        "Authorization": f"Bearer {ADMIN_FIREBASE_TOKEN}",
        "Content-Type": "application/json"
    }
    
    print(f"\n📡 Sending POST request to: {url}")
    print(f"🔑 Using Firebase token: {ADMIN_FIREBASE_TOKEN[:20]}...")
    
    try:
        # Make the request
        response = requests.post(url, headers=headers)
        
        print(f"\n📊 Response Status: {response.status_code}")
        print(f"📄 Response Body:")
        print(json.dumps(response.json(), indent=2))
        
        if response.status_code == 200:
            print("\n✅ SUCCESS: Admin successfully joined the campaign!")
            data = response.json()
            print(f"   - Campaign ID: {data.get('campaign_id')}")
            print(f"   - Thread ID: {data.get('thread_id')}")
            print(f"   - Conversation ID: {data['conversation']['id']}")
            print(f"   - Conversation Name: {data['conversation']['name']}")
        elif response.status_code == 403:
            print("\n❌ FORBIDDEN: User is not an admin")
        elif response.status_code == 404:
            print("\n❌ NOT FOUND: Campaign thread not found")
        elif response.status_code == 400:
            print("\n⚠️  BAD REQUEST: Cannot join own campaign")
        else:
            print(f"\n❌ ERROR: Unexpected status code {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"\n❌ REQUEST FAILED: {e}")
    except json.JSONDecodeError:
        print(f"\n❌ INVALID JSON RESPONSE: {response.text}")

def test_non_admin_attempt():
    """
    Test that non-admins cannot join campaigns
    """
    print("\n" + "=" * 60)
    print("Testing Non-Admin Access (Should Fail)")
    print("=" * 60)
    
    # Use a non-admin token (client or influencer)
    NON_ADMIN_TOKEN = "YOUR_NON_ADMIN_TOKEN_HERE"
    
    url = f"{API_BASE_URL}/messages/campaigns/{CAMPAIGN_ID}/join"
    headers = {
        "Authorization": f"Bearer {NON_ADMIN_TOKEN}",
        "Content-Type": "application/json"
    }
    
    print(f"\n📡 Sending POST request to: {url}")
    print(f"🔑 Using non-admin token: {NON_ADMIN_TOKEN[:20]}...")
    
    try:
        response = requests.post(url, headers=headers)
        print(f"\n📊 Response Status: {response.status_code}")
        print(f"📄 Response Body:")
        print(json.dumps(response.json(), indent=2))
        
        if response.status_code == 403:
            print("\n✅ EXPECTED: Non-admin correctly denied access")
        else:
            print(f"\n⚠️  UNEXPECTED: Expected 403, got {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"\n❌ REQUEST FAILED: {e}")

if __name__ == "__main__":
    print("\n🚀 Admin Join Campaign Endpoint Test Suite")
    print("=" * 60)
    print("\n⚠️  SETUP REQUIRED:")
    print("   1. Update ADMIN_FIREBASE_TOKEN with a valid admin token")
    print("   2. Update CAMPAIGN_ID with an existing campaign ID")
    print("   3. Ensure the API server is running on", API_BASE_URL)
    print("   4. Ensure the admin user has role='admin' in the database")
    print("\n" + "=" * 60)
    
    # Run tests
    test_admin_join_campaign()
    
    # Uncomment to test non-admin access
    # test_non_admin_attempt()
    
    print("\n" + "=" * 60)
    print("✅ Test suite completed")
    print("=" * 60)
