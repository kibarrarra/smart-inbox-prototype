#!/usr/bin/env python3
"""
Gmail Authentication Diagnostics
===============================
Step-by-step checks to diagnose Gmail OAuth issues
"""

import sys
import os
import json
import base64
import requests
sys.path.append('src')

from src.config import cfg

def check_credentials_loaded():
    """Step 1: Check if credentials are loaded from config"""
    print("🔍 Step 1: Checking credential loading...")
    
    try:
        has_refresh = bool(cfg.REFRESH_B64)
        has_client_id = bool(cfg.CLIENT_ID_B64)
        has_client_secret = bool(cfg.CLIENT_SECRET_B64)
        
        print(f"  REFRESH_B64: {'✅ Loaded' if has_refresh else '❌ Missing'}")
        print(f"  CLIENT_ID_B64: {'✅ Loaded' if has_client_id else '❌ Missing'}")
        print(f"  CLIENT_SECRET_B64: {'✅ Loaded' if has_client_secret else '❌ Missing'}")
        
        if has_refresh:
            # Decode and show first few chars
            rt = json.loads(base64.b64decode(cfg.REFRESH_B64))['refresh_token']
            print(f"  Refresh token preview: {rt[:15]}...")
            
        return has_refresh and has_client_id and has_client_secret
    except Exception as e:
        print(f"  ❌ Error loading credentials: {e}")
        return False

def check_token_format():
    """Step 2: Validate token format"""
    print("\n🔍 Step 2: Checking token format...")
    
    try:
        # Decode refresh token
        refresh_data = json.loads(base64.b64decode(cfg.REFRESH_B64))
        rt = refresh_data['refresh_token']
        
        # Decode client credentials
        client_id = base64.b64decode(cfg.CLIENT_ID_B64).decode()
        client_secret = base64.b64decode(cfg.CLIENT_SECRET_B64).decode()
        
        print(f"  Refresh token format: {'✅ Valid' if rt and rt.startswith('1//') else '❌ Invalid'}")
        print(f"  Client ID format: {'✅ Valid' if '.apps.googleusercontent.com' in client_id else '❌ Invalid'}")
        print(f"  Client secret format: {'✅ Valid' if client_secret.startswith('GOCSPX-') else '❌ Valid (older format)'}")
        
        return rt, client_id, client_secret
    except Exception as e:
        print(f"  ❌ Error parsing tokens: {e}")
        return None, None, None

def test_manual_token_refresh(refresh_token, client_id, client_secret):
    """Step 3: Test direct OAuth refresh call"""
    print("\n🔍 Step 3: Testing manual token refresh...")
    
    try:
        # Direct call to Google's OAuth endpoint
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
            'client_id': client_id,
            'client_secret': client_secret
        }
        
        response = requests.post('https://oauth2.googleapis.com/token', data=data)
        
        if response.status_code == 200:
            result = response.json()
            print("  ✅ Token refresh successful!")
            print(f"  New access token: {result['access_token'][:20]}...")
            print(f"  Token type: {result.get('token_type', 'bearer')}")
            print(f"  Expires in: {result.get('expires_in', 'unknown')} seconds")
            return result['access_token']
        else:
            error_data = response.json()
            print(f"  ❌ Token refresh failed: {response.status_code}")
            print(f"  Error: {error_data.get('error', 'unknown')}")
            print(f"  Description: {error_data.get('error_description', 'No description')}")
            
            # Common error interpretations
            if error_data.get('error') == 'invalid_grant':
                print("\n  💡 This usually means:")
                print("     - Refresh token has been revoked")
                print("     - User revoked access in Google Account settings")
                print("     - OAuth app credentials changed")
                print("     - Token is from different OAuth app")
            
            return None
    except Exception as e:
        print(f"  ❌ Request failed: {e}")
        return None

def test_gmail_api_call(access_token):
    """Step 4: Test Gmail API with fresh access token"""
    print("\n🔍 Step 4: Testing Gmail API access...")
    
    if not access_token:
        print("  ⏭️ Skipping - no valid access token")
        return False
        
    try:
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/json'
        }
        
        # Test getting user profile
        response = requests.get('https://gmail.googleapis.com/gmail/v1/users/me/profile', headers=headers)
        
        if response.status_code == 200:
            profile = response.json()
            print(f"  ✅ Gmail API working!")
            print(f"  Email: {profile['emailAddress']}")
            print(f"  Total messages: {profile['messagesTotal']}")
            return True
        else:
            print(f"  ❌ Gmail API failed: {response.status_code}")
            print(f"  Response: {response.text}")
            return False
    except Exception as e:
        print(f"  ❌ Gmail API test failed: {e}")
        return False

def main():
    print("Gmail Authentication Diagnostics")
    print("=" * 50)
    
    # Step 1: Check credentials
    if not check_credentials_loaded():
        print("\n❌ Cannot proceed - missing credentials")
        return
    
    # Step 2: Check format
    refresh_token, client_id, client_secret = check_token_format()
    if not all([refresh_token, client_id, client_secret]):
        print("\n❌ Cannot proceed - invalid credential format")
        return
    
    # Step 3: Test refresh
    access_token = test_manual_token_refresh(refresh_token, client_id, client_secret)
    
    # Step 4: Test Gmail API
    test_gmail_api_call(access_token)
    
    print("\n" + "=" * 50)
    if access_token:
        print("✅ Diagnosis: Gmail authentication is working!")
        print("   The issue may be in the application code, not the tokens.")
    else:
        print("❌ Diagnosis: Gmail tokens need to be refreshed.")
        print("\n🔧 Next steps:")
        print("   1. Check Google Account settings: https://myaccount.google.com/permissions")
        print("   2. Look for 'Smart Inbox' or your app name and verify it's still authorized")
        print("   3. If revoked, you'll need to re-run the OAuth flow")
        print("   4. Check Google Cloud Console OAuth app is still active")

if __name__ == "__main__":
    main()