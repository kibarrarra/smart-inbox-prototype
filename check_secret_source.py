#!/usr/bin/env python3
"""
Check exactly where credentials are coming from
"""

import os
import sys
sys.path.append('src')

def check_credential_sources():
    print("🔍 Checking credential sources...")
    print("=" * 50)
    
    # Check environment variables first
    print("1. Environment Variables:")
    env_vars = ['GMAIL_REFRESH_B64', 'GOOGLE_CLIENT_ID_B64', 'GOOGLE_CLIENT_SECRET_B64']
    for var in env_vars:
        value = os.getenv(var)
        if value:
            print(f"   ✅ {var}: Found (length: {len(value)})")
        else:
            print(f"   ❌ {var}: Not found")
    
    print("\n2. Google Cloud Project:")
    project = os.getenv('GOOGLE_CLOUD_PROJECT')
    print(f"   Project: {project}")
    
    print("\n3. Testing Secret Manager access:")
    if project:
        try:
            from google.cloud import secretmanager
            client = secretmanager.SecretManagerServiceClient()
            
            # Try to list secrets to test access
            parent = f"projects/{project}"
            secrets = client.list_secrets(request={"parent": parent})
            secret_names = [secret.name.split('/')[-1] for secret in secrets]
            
            print(f"   ✅ Secret Manager accessible")
            print(f"   Available secrets: {secret_names}")
            
            # Test specific secrets
            gmail_secrets = ['gmail-refresh-token', 'gmail-client-id', 'gmail-client-secret']
            for secret_name in gmail_secrets:
                if secret_name in secret_names:
                    try:
                        secret_path = f"projects/{project}/secrets/{secret_name}/versions/latest"
                        response = client.access_secret_version(name=secret_path)
                        payload = response.payload.data.decode()
                        print(f"   ✅ {secret_name}: Retrieved (length: {len(payload)})")
                    except Exception as e:
                        print(f"   ❌ {secret_name}: Error retrieving - {e}")
                else:
                    print(f"   ❌ {secret_name}: Not found in secrets")
                    
        except Exception as e:
            print(f"   ❌ Secret Manager error: {e}")
    else:
        print("   ⏭️ No GOOGLE_CLOUD_PROJECT set, skipping Secret Manager")
    
    print("\n4. Config loading test:")
    try:
        from src.config import cfg
        print(f"   REFRESH_B64 source: {'Environment' if os.getenv('GMAIL_REFRESH_B64') else 'Secret Manager or missing'}")
        print(f"   CLIENT_ID_B64 source: {'Environment' if os.getenv('GOOGLE_CLIENT_ID_B64') else 'Secret Manager or missing'}")
        print(f"   CLIENT_SECRET_B64 source: {'Environment' if os.getenv('GOOGLE_CLIENT_SECRET_B64') else 'Secret Manager or missing'}")
        
        # Show first few chars to confirm they're different sources
        if cfg.REFRESH_B64:
            print(f"   REFRESH_B64 preview: {cfg.REFRESH_B64[:20]}...")
        if cfg.CLIENT_ID_B64:
            print(f"   CLIENT_ID_B64 preview: {cfg.CLIENT_ID_B64[:20]}...")
            
    except Exception as e:
        print(f"   ❌ Config loading error: {e}")

if __name__ == "__main__":
    check_credential_sources()