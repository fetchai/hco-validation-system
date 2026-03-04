#!/usr/bin/env python3
"""
Interactive popup authentication using MSAL
"""

import os
import msal
import webbrowser
import requests
import json
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

class PopupMSALAuth:
    """Interactive popup authentication for Excel and OneDrive clients"""
    
    def __init__(self, client_id: str = None):
        self.client_id = client_id or os.getenv("AZURE_CLIENT_ID")
        
        if not self.client_id:
            raise ValueError("AZURE_CLIENT_ID must be set in .env")
        
        self.access_token = None
        self.headers = None
        self._authenticated = False
        self.token_expires_at = None
        
        # Cache file for token persistence (shared with backend agent)
        self.cache_file = "auth_cache.json"
        
    def _load_cached_token(self):
        """Load cached token if it exists and is not expired"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    cache_data = json.load(f)
                
                # Handle both frontend sync format and popup auth format
                expires_at_str = cache_data.get('expires_at', '')
                if not expires_at_str:
                    print("⚠️ No expires_at found in cached token")
                    return False
                
                # Parse the datetime string, handling various formats
                try:
                    # Handle ISO format with Z suffix or timezone info
                    if expires_at_str.endswith('Z'):
                        expires_at_str = expires_at_str.replace('Z', '+00:00')
                    expires_at = datetime.fromisoformat(expires_at_str)
                    
                    # Ensure both datetime objects are timezone-naive for comparison
                    if expires_at.tzinfo is not None:
                        expires_at = expires_at.replace(tzinfo=None)
                except ValueError as ve:
                    print(f"⚠️ Invalid datetime format in cached token: {expires_at_str}, error: {ve}")
                    return False
                
                # Check if token is still valid (with 5 minute buffer)
                now = datetime.now()
                access_token = cache_data.get('access_token')
                if not access_token:
                    return False
                if now + timedelta(minutes=5) < expires_at:
                    self.access_token = access_token
                    self.token_expires_at = expires_at
                    self.headers = {
                        "Authorization": f"Bearer {self.access_token}",
                        "Content-Type": "application/json"
                    }
                    self._authenticated = True
                    source = cache_data.get('source', 'unknown')
                    user_email = cache_data.get('user_email', 'Unknown')
                    print(f"🔄 Using cached authentication token from {source} for user: {user_email}")
                    return True
                else:
                    print(f"⏰ Cached token expired (expires: {expires_at}, now: {now})")
                    # Don't remove the cache file if it came from frontend sync
                    if cache_data.get('source') != 'frontend':
                        os.remove(self.cache_file)
                    return False
        except Exception as e:
            print(f"⚠️ Error loading cached token: {e}")
            # Only remove cache if it's not from frontend
            try:
                if os.path.exists(self.cache_file):
                    with open(self.cache_file, 'r') as f:
                        cache_check = json.load(f)
                    if cache_check.get('source') != 'frontend':
                        os.remove(self.cache_file)
            except Exception:
                pass
        
        return False

    def _save_token_cache(self, result):
        """Save token to cache with expiry information"""
        try:
            expires_in = result.get('expires_in', 3600)  # Default 1 hour
            expires_at = datetime.now() + timedelta(seconds=expires_in)
            
            cache_data = {
                'access_token': result['access_token'],
                'expires_at': expires_at.isoformat(),
                'client_id': self.client_id
            }
            
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f)
            
            self.token_expires_at = expires_at
            print(f"💾 Token cached until {expires_at.strftime('%Y-%m-%d %H:%M:%S')}")
            
        except Exception as e:
            print(f"⚠️ Error saving token cache: {e}")

    def authenticate(self):
        """Authenticate using interactive popup flow with caching"""
        # First try to use cached token (could be from frontend sync)
        if self._load_cached_token():
            return
            
        # Check if we have a frontend token (even if expired)
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    cache_data = json.load(f)
                if cache_data.get('source') == 'frontend':
                    print("⚠️ Frontend authentication detected but token expired.")
                    print("💡 Please refresh your browser or log in again through the frontend web interface.")
                    print("🚫 Backend will not attempt popup authentication when frontend auth is used.")
                    # Don't proceed with popup auth if we have a frontend token
                    # The user should log in through the web interface instead
                    self._authenticated = False
                    return
        except Exception:
            pass
        
        # Check if user explicitly wants to use frontend auth
        print("⚠️ No frontend authentication found.")
        print("💡 For web users: Please log in through the frontend interface.")
        print("🔧 For direct API users: Popup authentication will be attempted.")
        
        try:
            print("🔑 Starting interactive authentication...")
            
            # Create public client application (using common tenant)
            app = msal.PublicClientApplication(
                client_id=self.client_id,
                authority="https://login.microsoftonline.com/common"
            )
            
            # Define the scopes we need
            scopes = [
                "https://graph.microsoft.com/Files.ReadWrite.All",
                "https://graph.microsoft.com/Sites.ReadWrite.All"
            ]
            
            # Try to get token from MSAL cache first
            accounts = app.get_accounts()
            result = None
            
            if accounts:
                print("🔄 Found MSAL cached account, trying silent authentication...")
                result = app.acquire_token_silent(scopes, account=accounts[0])
            
            if not result:
                print("🌐 Opening browser for authentication...")
                # Interactive login - this will open a popup/browser
                result = app.acquire_token_interactive(
                    scopes=scopes,
                    prompt="select_account",
                    parent_window_handle=None,
                    # Add redirect URI for native app
                    port=8080
                )
            
            if "access_token" not in result:
                error = result.get("error_description", result.get("error", "Unknown error"))
                raise Exception(f"Authentication failed: {error}")
            
            self.access_token = result["access_token"]
            self.headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            # Save to our custom cache
            self._save_token_cache(result)
            
            self._authenticated = True
            print("✅ Interactive authentication successful!")
            
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            raise e
        
    def _check_token_expiry(self):
        """Check if token is about to expire and refresh if needed"""
        if self.token_expires_at:
            # Ensure token_expires_at is timezone-naive for comparison
            expires_at = self.token_expires_at
            if expires_at.tzinfo is not None:
                expires_at = expires_at.replace(tzinfo=None)
            
            # Refresh if token expires in less than 5 minutes
            if datetime.now() + timedelta(minutes=5) >= expires_at:
                print("⏰ Token expiring soon...")
                
                # Check if this token came from frontend sync
                try:
                    if os.path.exists(self.cache_file):
                        with open(self.cache_file, 'r') as f:
                            cache_data = json.load(f)
                        
                        if cache_data.get('source') == 'frontend':
                            print("💡 Frontend token expiring - waiting for frontend to refresh and sync new token")
                            print("🔄 If you're experiencing issues, please refresh your browser or log in again")
                            self._authenticated = False
                            # Don't remove the cache file, wait for frontend to update it
                            return
                except Exception:
                    pass
                
                # Only try popup authentication for non-frontend tokens
                print("🔄 Attempting token refresh...")
                self._authenticated = False
                if os.path.exists(self.cache_file):
                    os.remove(self.cache_file)
                self.authenticate()

    def get_headers(self):
        """Get authentication headers with automatic token refresh"""
        # Always try to reload cache first (in case frontend synced a new token)
        if self._load_cached_token():
            return self.headers
            
        if not self._authenticated:
            # Check if we should wait for frontend instead of doing popup auth
            if self._should_wait_for_frontend():
                print("⏳ Waiting for frontend authentication...")
                import time
                for attempt in range(3):
                    time.sleep(1)  # Wait 1 second between retries
                    if self._load_cached_token():
                        return self.headers
                    print(f"⏳ Still waiting for frontend token (attempt {attempt + 1}/3)...")
                
                print("❌ No valid token found. Please log in through the frontend.")
                return None
            else:
                self.authenticate()
        else:
            self._check_token_expiry()
            # If token expired and we're waiting for frontend, try reloading cache with retries
            if not self._authenticated:
                if self._should_wait_for_frontend():
                    print("⏳ Token expired, waiting for frontend refresh...")
                    import time
                    for attempt in range(3):
                        time.sleep(1)
                        if self._load_cached_token():
                            return self.headers
                        print(f"⏳ Still waiting for frontend refresh (attempt {attempt + 1}/3)...")
                    
                    print("❌ No refreshed token found. Please refresh your browser.")
                    return None
        return self.headers
    
    def _should_wait_for_frontend(self):
        """Check if we should wait for frontend auth instead of doing popup"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    cache_data = json.load(f)
                return cache_data.get('source') == 'frontend'
        except Exception:
            pass
        return False
    
    def get_access_token(self):
        """Get access token with automatic token refresh"""
        # Always try to reload cache first (in case frontend synced a new token)
        if self._load_cached_token():
            return self.access_token
            
        if not self._authenticated:
            # Check if we should wait for frontend instead of doing popup auth
            if self._should_wait_for_frontend():
                print("⏳ Waiting for frontend authentication...")
                import time
                for attempt in range(3):
                    time.sleep(1)  # Wait 1 second between retries
                    if self._load_cached_token():
                        return self.access_token
                    print(f"⏳ Still waiting for frontend token (attempt {attempt + 1}/3)...")
                
                print("❌ No valid token found. Please log in through the frontend.")
                return None
            else:
                self.authenticate()
        else:
            self._check_token_expiry()
            # If token expired and we're waiting for frontend, try reloading cache with retries
            if not self._authenticated:
                if self._should_wait_for_frontend():
                    print("⏳ Token expired, waiting for frontend refresh...")
                    import time
                    for attempt in range(3):
                        time.sleep(1)
                        if self._load_cached_token():
                            return self.access_token
                        print(f"⏳ Still waiting for frontend refresh (attempt {attempt + 1}/3)...")
                    
                    print("❌ No refreshed token found. Please refresh your browser.")
                    return None
        return self.access_token
    
    def handle_api_error(self, status_code: int):
        """Handle API errors, particularly authentication failures"""
        if status_code == 401:
            print("🔄 API returned 401, token may be expired. Re-authenticating...")
            self._authenticated = False
            if os.path.exists(self.cache_file):
                os.remove(self.cache_file)
            self.authenticate()
            return True
        return False

# Global shared authentication instance
_popup_auth = None

def get_popup_auth():
    """Get or create popup authentication instance"""
    global _popup_auth
    if _popup_auth is None:
        client_id = os.getenv("AZURE_CLIENT_ID")
        if not client_id:
            raise Exception("AZURE_CLIENT_ID not configured in environment")
        _popup_auth = PopupMSALAuth(client_id)
    return _popup_auth

if __name__ == "__main__":
    print("🔧 Testing Popup Authentication")
    print("=" * 50)
    
    try:
        auth = get_popup_auth()
        headers = auth.get_headers()
        
        # Test Graph API access
        response = requests.get(
            "https://graph.microsoft.com/v1.0/me",
            headers=headers
        )
        
        if response.status_code == 200:
            user_info = response.json()
            print(f"✅ Authenticated as: {user_info.get('displayName', 'Unknown')}")
            print("🎉 Popup authentication working!")
        else:
            print(f"❌ API test failed: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Setup error: {e}")
        print("\n📋 Setup Required:")
        print("1. Ensure AZURE_CLIENT_ID is set in .env")
        print("2. App must allow public client flows in Azure portal")
        print("3. Add redirect URI: http://localhost")