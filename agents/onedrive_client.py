import requests
import os
from pathlib import Path
import json
from urllib.parse import quote

class OneDriveClient:
    """Client for OneDrive file operations with environment-based authentication"""
    
    def __init__(self, client_id: str = None):
        # Use environment variable for access token (set by frontend or external system)
        access_token = os.getenv("ONEDRIVE_ACCESS_TOKEN")
        if access_token:
            self.headers = {"Authorization": f"Bearer {access_token}"}
        else:
            # Fallback: Try to load from auth cache file
            self.headers = self._get_headers_from_cache()
    
    def _get_headers_from_cache(self):
        """Load authentication headers from cache file if available"""
        try:
            auth_cache_file = os.getenv("AUTH_CACHE_FILE", "auth_cache.json")
            if os.path.exists(auth_cache_file):
                with open(auth_cache_file, 'r') as f:
                    cache = json.load(f)
                    access_token = cache.get("access_token")
                    if access_token:
                        return {"Authorization": f"Bearer {access_token}"}
        except Exception as e:
            print(f"Warning: Could not load auth cache: {e}")
        
        # Return empty headers if no authentication available
        print("Warning: No authentication available for OneDrive operations")
        return {}
    
    # ============================================
    # FILE UPLOAD METHODS
    # ============================================
    
    def upload_small_file(self, local_file_path: str, onedrive_folder_path: str = "/"):
        """
        Upload a file < 4MB to OneDrive
        
        Args:
            local_file_path: Path to local file (e.g., "document.pdf")
            onedrive_folder_path: OneDrive folder path (e.g., "/" for root, "/Documents" for subfolder)
        """
        filename = os.path.basename(local_file_path)
        
        # Check file size
        file_size = os.path.getsize(local_file_path)
        if file_size > 4 * 1024 * 1024:  # 4MB
            print(f"⚠️  File is {file_size / (1024*1024):.2f}MB. Use upload_large_file() instead.")
            return self.upload_large_file(local_file_path, onedrive_folder_path)
        
        # Construct URL
        if onedrive_folder_path == "/":
            url = f"https://graph.microsoft.com/v1.0/me/drive/root:/{filename}:/content"
        else:
            onedrive_folder_path = onedrive_folder_path.strip('/')
            url = f"https://graph.microsoft.com/v1.0/me/drive/root:/{onedrive_folder_path}/{filename}:/content"
        
        # Read and upload file
        with open(local_file_path, 'rb') as f:
            file_content = f.read()
        
        response = requests.put(url, headers=self.headers, data=file_content)
        
        if response.status_code in [200, 201]:
            result = response.json()
            print(f"✅ Uploaded: {filename}")
            print(f"   Size: {result.get('size', 0) / 1024:.2f} KB")
            print(f"   WebUrl: {result.get('webUrl', 'N/A')}")
            return result
        else:
            print(f"❌ Upload failed: {response.status_code}")
            print(response.text)
            return None
    
    def upload_large_file(self, local_file_path: str, onedrive_folder_path: str = "/"):
        """
        Upload a file > 4MB using upload session (supports files up to 250GB)
        
        Args:
            local_file_path: Path to local file
            onedrive_folder_path: OneDrive folder path
        """
        filename = os.path.basename(local_file_path)
        file_size = os.path.getsize(local_file_path)
        
        print(f"📤 Uploading large file: {filename} ({file_size / (1024*1024):.2f} MB)")
        
        # Construct URL
        if onedrive_folder_path == "/":
            url = f"https://graph.microsoft.com/v1.0/me/drive/root:/{filename}:/createUploadSession"
        else:
            onedrive_folder_path = onedrive_folder_path.strip('/')
            url = f"https://graph.microsoft.com/v1.0/me/drive/root:/{onedrive_folder_path}/{filename}:/createUploadSession"
        
        # Create upload session
        session_response = requests.post(url, headers=self.headers, json={})
        
        if session_response.status_code not in [200, 201]:
            print(f"❌ Failed to create upload session: {session_response.text}")
            return None
        
        upload_url = session_response.json()['uploadUrl']
        
        # Upload in chunks (10MB per chunk)
        chunk_size = 10 * 1024 * 1024  # 10MB
        
        with open(local_file_path, 'rb') as f:
            chunk_number = 0
            while True:
                chunk_data = f.read(chunk_size)
                if not chunk_data:
                    break
                
                start_byte = chunk_number * chunk_size
                end_byte = start_byte + len(chunk_data) - 1
                
                headers = {
                    'Content-Length': str(len(chunk_data)),
                    'Content-Range': f'bytes {start_byte}-{end_byte}/{file_size}'
                }
                
                chunk_response = requests.put(upload_url, headers=headers, data=chunk_data)
                
                if chunk_response.status_code not in [200, 201, 202]:
                    print(f"❌ Upload failed at chunk {chunk_number}: {chunk_response.text}")
                    return None
                
                progress = ((end_byte + 1) / file_size) * 100
                print(f"   Progress: {progress:.1f}%")
                
                chunk_number += 1
        
        print(f"✅ Upload complete: {filename}")
        return chunk_response.json()
    
    def upload_file(self, local_file_path: str, onedrive_folder_path: str = "/"):
        """
        Smart upload - automatically chooses small or large file method
        
        Args:
            local_file_path: Path to local file
            onedrive_folder_path: OneDrive destination folder (default: root "/")
        """
        if not os.path.exists(local_file_path):
            print(f"❌ File not found: {local_file_path}")
            return None
        
        file_size = os.path.getsize(local_file_path)
        
        if file_size < 4 * 1024 * 1024:  # < 4MB
            return self.upload_small_file(local_file_path, onedrive_folder_path)
        else:
            return self.upload_large_file(local_file_path, onedrive_folder_path)
    
    # ============================================
    # FILE DOWNLOAD METHODS
    # ============================================
    
    def download_file(self, onedrive_file_path: str, local_download_path: str = None):
        """
        Download a file from OneDrive
        
        Args:
            onedrive_file_path: Path in OneDrive (e.g., "/Documents/report.pdf")
            local_download_path: Where to save locally (default: same filename in current dir)
        """
        # Remove leading slash if present
        onedrive_file_path = onedrive_file_path.lstrip('/')
        
        # Get file metadata first
        url = f"https://graph.microsoft.com/v1.0/me/drive/root:/{onedrive_file_path}"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code != 200:
            print(f"❌ File not found: {onedrive_file_path}")
            print(response.text)
            return None
        
        file_info = response.json()
        download_url = file_info.get('@microsoft.graph.downloadUrl')
        filename = file_info.get('name')
        file_size = file_info.get('size', 0)
        
        # Determine local save path
        if local_download_path is None:
            local_download_path = filename
        
        # Create directory if needed
        os.makedirs(os.path.dirname(local_download_path) or '.', exist_ok=True)
        
        print(f"📥 Downloading: {filename} ({file_size / 1024:.2f} KB)")
        
        # Download file
        download_response = requests.get(download_url, stream=True)
        
        if download_response.status_code == 200:
            with open(local_download_path, 'wb') as f:
                for chunk in download_response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"✅ Downloaded to: {local_download_path}")
            return local_download_path
        else:
            print(f"❌ Download failed: {download_response.status_code}")
            return None
    
    def download_file_by_id(self, item_id: str, local_download_path: str = None):
        """
        Download a file using its item ID
        
        Args:
            item_id: OneDrive item ID
            local_download_path: Where to save locally
        """
        # Get file metadata
        url = f"https://graph.microsoft.com/v1.0/me/drive/items/{item_id}"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code != 200:
            print(f"❌ File not found with ID: {item_id}")
            return None
        
        file_info = response.json()
        download_url = file_info.get('@microsoft.graph.downloadUrl')
        filename = file_info.get('name')
        file_size = file_info.get('size', 0)
        
        if local_download_path is None:
            local_download_path = filename
        
        print(f"📥 Downloading: {filename} ({file_size / 1024:.2f} KB)")
        
        # Download
        download_response = requests.get(download_url, stream=True)
        
        if download_response.status_code == 200:
            with open(local_download_path, 'wb') as f:
                for chunk in download_response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"✅ Downloaded to: {local_download_path}")
            return local_download_path
        else:
            print(f"❌ Download failed")
            return None
    
    # ============================================
    # FILE LISTING & SEARCH
    # ============================================
    
    def list_files(self, folder_path: str = "/"):
        """
        List files in a OneDrive folder
        
        Args:
            folder_path: Folder path (default: root "/")
        """
        if folder_path == "/":
            url = "https://graph.microsoft.com/v1.0/me/drive/root/children"
        else:
            folder_path = folder_path.strip('/')
            url = f"https://graph.microsoft.com/v1.0/me/drive/root:/{folder_path}:/children"
        
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            items = response.json().get("value", [])
            print(f"✅ Found {len(items)} items in '{folder_path}':\n")
            
            for item in items:
                icon = "📁" if item.get("folder") else "📄"
                size = f"{item.get('size', 0) / 1024:.2f} KB" if not item.get("folder") else "Folder"
                print(f"{icon} {item['name']} ({size})")
                print(f"   ID: {item['id']}")
            
            return items
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.text)
            return None
    
    def search_files(self, query: str):
        """
        Search for files in OneDrive
        
        Args:
            query: Search term (filename or content)
        """
        url = f"https://graph.microsoft.com/v1.0/me/drive/root/search(q='{query}')"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            items = response.json().get("value", [])
            print(f"✅ Found {len(items)} results for '{query}':\n")
            
            for item in items:
                icon = "📁" if item.get("folder") else "📄"
                path = item.get('parentReference', {}).get('path', 'N/A')
                print(f"{icon} {item['name']}")
                print(f"   Path: {path}")
                print(f"   ID: {item['id']}\n")
            
            return items
        else:
            print(f"❌ Search failed: {response.status_code}")
            return None
    
    # ============================================
    # FILE OPERATIONS
    # ============================================
    
    def delete_file(self, onedrive_file_path: str):
        """Delete a file from OneDrive"""
        onedrive_file_path = onedrive_file_path.lstrip('/')
        url = f"https://graph.microsoft.com/v1.0/me/drive/root:/{onedrive_file_path}"
        
        response = requests.delete(url, headers=self.headers)
        
        if response.status_code == 204:
            print(f"✅ Deleted: {onedrive_file_path}")
            return True
        else:
            print(f"❌ Delete failed: {response.status_code}")
            print(response.text)
            return False
    
    def create_folder(self, folder_name: str, parent_path: str = "/"):
        """Create a folder in OneDrive"""
        if parent_path == "/":
            url = "https://graph.microsoft.com/v1.0/me/drive/root/children"
        else:
            parent_path = parent_path.strip('/')
            url = f"https://graph.microsoft.com/v1.0/me/drive/root:/{parent_path}:/children"
        
        payload = {
            "name": folder_name,
            "folder": {},
            "@microsoft.graph.conflictBehavior": "rename"
        }
        
        headers = {**self.headers, "Content-Type": "application/json"}
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code in [200, 201]:
            result = response.json()
            print(f"✅ Folder created: {result.get('name')}")
            return result
        else:
            print(f"❌ Failed to create folder: {response.text}")
            return None
    
    def get_file_info(self, onedrive_file_path: str):
        """Get detailed information about a file"""
        onedrive_file_path = onedrive_file_path.lstrip('/')
        url = f"https://graph.microsoft.com/v1.0/me/drive/root:/{onedrive_file_path}"
        
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            info = response.json()
            print(f"📄 File: {info.get('name')}")
            print(f"   Size: {info.get('size', 0) / 1024:.2f} KB")
            print(f"   Created: {info.get('createdDateTime')}")
            print(f"   Modified: {info.get('lastModifiedDateTime')}")
            print(f"   ID: {info.get('id')}")
            print(f"   WebUrl: {info.get('webUrl')}")
            return info
        elif response.status_code == 404:
            # File not found - this is normal for new certificates
            return None
        else:
            print(f"❌ File not found: {response.text}")
            return None


# ============================================
# CERTIFICATE SPECIFIC FUNCTIONS
# ============================================

# Use same client ID as Excel
ONEDRIVE_CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
CERTIFICATE_FOLDER = "HCO_Staging_Certificate"
CERTIFICATE_FOLDER_ID = os.getenv("CERTIFICATE_FOLDER_ID")

def _get_auth_headers():
    """Get authentication headers from environment or cache"""
    access_token = os.getenv("ONEDRIVE_ACCESS_TOKEN")
    if access_token:
        return {"Authorization": f"Bearer {access_token}"}
    
    # Try to load from cache file
    try:
        auth_cache_file = os.getenv("AUTH_CACHE_FILE", "auth_cache.json")
        if os.path.exists(auth_cache_file):
            with open(auth_cache_file, 'r') as f:
                cache = json.load(f)
                access_token = cache.get("access_token")
                if access_token:
                    return {"Authorization": f"Bearer {access_token}"}
    except Exception as e:
        print(f"Warning: Could not load auth cache: {e}")
    
    print("Warning: No authentication available for OneDrive operations")
    return None

def upload_certificate_to_staging_folder(local_file_path: str, filename: str):
    """
    Upload a certificate directly to the HCO_Staging_Certificate folder (shared folder)
    
    Args:
        local_file_path: Path to certificate file
        filename: Name for the file in OneDrive
    
    Returns:
        dict: Upload result with webUrl
    """
    try:
        if not CERTIFICATE_FOLDER_ID:
            print("❌ CERTIFICATE_FOLDER_ID environment variable is not set")
            return None
            
        headers = _get_auth_headers()
        if headers is None:
            print("❌ No authentication headers available")
            return None
        
        # CERTIFICATE_FOLDER_ID can be either a plain itemId, or a composite "driveId!itemId".
        if '!' in CERTIFICATE_FOLDER_ID:
            drive_id, folder_item_id = CERTIFICATE_FOLDER_ID.split('!', 1)
        else:
            drive_id, folder_item_id = CERTIFICATE_FOLDER_ID, CERTIFICATE_FOLDER_ID
        
        # Sanitize filename to prevent folder creation from slashes
        sanitized_filename = filename.replace('/', '_').replace('\\', '_')
        safe_filename = quote(sanitized_filename, safe="")
        # Upload to shared folder using drive and folder item id
        url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{folder_item_id}:/{safe_filename}:/content"
        
        # Read and upload file
        with open(local_file_path, 'rb') as f:
            file_content = f.read()
        
        response = requests.put(url, headers=headers, data=file_content)
        
        if response.status_code in [200, 201]:
            result = response.json()
            print(f"✅ Uploaded '{filename}' to shared HCO_Staging_Certificate folder")
            return result
        else:
            print(f"❌ Upload failed: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error uploading to staging folder: {e}")
        return None

def upload_certificate_to_onedrive(local_file_path: str, certificate_no: str):
    """
    Upload a certificate to OneDrive with fallback mechanism
    Tries shared folder first, falls back to own folder if access fails
    
    Args:
        local_file_path: Path to certificate file (PDF/PNG)
        certificate_no: Certificate number for naming
    
    Returns:
        dict: Upload result with webUrl for linking
    """
    try:
        # Get file extension and create upload filename
        import os
        file_extension = os.path.splitext(local_file_path)[1]
        upload_filename = f"{certificate_no}{file_extension}"
        
        # Use the staging folder upload function
        return upload_certificate_to_staging_folder(local_file_path, upload_filename)
            
    except Exception as e:
        print(f"❌ Error uploading certificate to OneDrive: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_certificate_download_url(certificate_no: str, file_type: str = "pdf"):
    """
    Get download URL for a certificate from OneDrive with fallback mechanism
    Tries shared folder first, falls back to own folder if access fails
    
    Args:
        certificate_no: Certificate number
        file_type: File extension (pdf, png, etc.)
    
    Returns:
        str: Download URL or None
    """
    try:
        if not CERTIFICATE_FOLDER_ID:
            print("❌ CERTIFICATE_FOLDER_ID environment variable is not set")
            return None
            
        headers = _get_auth_headers()
        if headers is None:
            print("❌ No authentication headers available")
            return None
        
        # CERTIFICATE_FOLDER_ID can be either a plain itemId, or a composite "driveId!itemId".
        if '!' in CERTIFICATE_FOLDER_ID:
            drive_id, folder_item_id = CERTIFICATE_FOLDER_ID.split('!', 1)
        else:
            drive_id, folder_item_id = CERTIFICATE_FOLDER_ID, CERTIFICATE_FOLDER_ID
        
        # Search for file in the staging folder (with sanitized certificate number)
        sanitized_cert_no = certificate_no.replace('/', '_').replace('\\', '_')
        filename = f"{sanitized_cert_no}.{file_type}"
        search_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{folder_item_id}/children"
        
        response = requests.get(search_url, headers=headers)
        
        if response.status_code == 200:
            items = response.json().get('value', [])
            for item in items:
                if item.get('name', '').startswith(sanitized_cert_no):
                    return item.get('webUrl')
        
        return None
            
    except Exception as e:
        # Don't print error for file not found - this is expected for new certificates
        if "itemNotFound" not in str(e) and "File not found" not in str(e):
            print(f"Error getting certificate download URL: {e}")
        return None

def get_certificate_file_data(certificate_no: str, file_type: str = "pdf"):
    """
    Download certificate file content from OneDrive with fallback mechanism
    Tries shared folder first, falls back to own folder if access fails
    
    Args:
        certificate_no: Certificate number
        file_type: File extension (pdf, png, etc.)
    
    Returns:
        tuple: (base64_file_data, filename, file_info) or (None, None, None) if not found
    """
    try:
        if not CERTIFICATE_FOLDER_ID:
            print("❌ CERTIFICATE_FOLDER_ID environment variable is not set")
            return None, None, None
            
        import base64
        
        headers = _get_auth_headers()
        if headers is None:
            print(f"❌ No authentication headers available for certificate search")
            return None, None, None
        
        print(f"🔍 Searching for certificate {certificate_no}.{file_type} in OneDrive...")
        
        # CERTIFICATE_FOLDER_ID can be either a plain itemId, or a composite "driveId!itemId".
        if '!' in CERTIFICATE_FOLDER_ID:
            drive_id, folder_item_id = CERTIFICATE_FOLDER_ID.split('!', 1)
        else:
            drive_id, folder_item_id = CERTIFICATE_FOLDER_ID, CERTIFICATE_FOLDER_ID
        print(f"📁 Using drive ID: {drive_id}")
        print(f"📁 Using folder ID: {folder_item_id}")
        
        # Search for file in the staging folder
        search_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{folder_item_id}/children"
        print(f"🔗 Search URL: {search_url}")
        
        response = requests.get(search_url, headers=headers)
        print(f"📡 Response status: {response.status_code}")
        
        if response.status_code == 200:
            items = response.json().get('value', [])
            print(f"📋 Found {len(items)} files in folder")
            
            # Log all filenames for debugging
            for item in items:
                filename = item.get('name', '')
                print(f"  📄 File: {filename}")
            
            # Search for matching files (with sanitized certificate number)
            sanitized_cert_no = certificate_no.replace('/', '_').replace('\\', '_')
            target_filename = f"{sanitized_cert_no}.{file_type}"
            print(f"🎯 Looking for file: {target_filename} (sanitized from {certificate_no})")
            
            for item in items:
                filename = item.get('name', '')
                if filename == target_filename or filename.startswith(sanitized_cert_no):
                    print(f"✅ Found matching file: {filename}")
                    
                    # Try to download using multiple methods
                    file_content = None
                    item_id = item.get('id')
                    
                    # Method 1: Try downloadUrl if available
                    download_url = item.get('downloadUrl')
                    if download_url:
                        print(f"⬇️ Method 1: Downloading using downloadUrl...")
                        try:
                            file_response = requests.get(download_url)
                            if file_response.status_code == 200:
                                file_content = base64.b64encode(file_response.content).decode()
                                print(f"✅ Successfully downloaded {len(file_content)} characters of base64 data")
                                return file_content, item.get('name'), item
                        except Exception as e:
                            print(f"❌ downloadUrl method failed: {e}")
                    
                    # Method 2: Use Graph API content endpoint
                    if item_id:
                        print(f"⬇️ Method 2: Downloading using Graph API content endpoint...")
                        try:
                            content_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{item_id}/content"
                            print(f"🔗 Content URL: {content_url}")
                            file_response = requests.get(content_url, headers=headers)
                            if file_response.status_code == 200:
                                file_content = base64.b64encode(file_response.content).decode()
                                print(f"✅ Successfully downloaded {len(file_content)} characters of base64 data via content endpoint")
                                return file_content, item.get('name'), item
                            else:
                                print(f"❌ Content endpoint failed: {file_response.status_code} - {file_response.text}")
                        except Exception as e:
                            print(f"❌ Content endpoint method failed: {e}")
                    
                    # Method 3: Try direct drive item content URL
                    if '!' in CERTIFICATE_FOLDER_ID:
                        drive_id, folder_item_id = CERTIFICATE_FOLDER_ID.split('!', 1)
                    else:
                        drive_id, folder_item_id = CERTIFICATE_FOLDER_ID, CERTIFICATE_FOLDER_ID
                    
                    if item_id:
                        print(f"⬇️ Method 3: Trying alternative content endpoint...")
                        try:
                            # Use sanitized filename for URL path
                            sanitized_filename = filename.replace('/', '_').replace('\\', '_')
                            safe_filename = quote(sanitized_filename, safe="")
                            alt_content_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{folder_item_id}:/{safe_filename}:/content"
                            print(f"🔗 Alternative content URL: {alt_content_url}")
                            file_response = requests.get(alt_content_url, headers=headers)
                            if file_response.status_code == 200:
                                file_content = base64.b64encode(file_response.content).decode()
                                print(f"✅ Successfully downloaded {len(file_content)} characters of base64 data via alternative endpoint")
                                return file_content, item.get('name'), item
                            else:
                                print(f"❌ Alternative content endpoint failed: {file_response.status_code}")
                        except Exception as e:
                            print(f"❌ Alternative content endpoint method failed: {e}")
                    
                    print(f"❌ All download methods failed for {filename}")
            
            print(f"❌ No matching files found for certificate {certificate_no}")
        else:
            print(f"❌ Failed to access OneDrive folder: {response.status_code} {response.text}")
        
        return None, None, None
                
    except Exception as e:
        print(f"❌ Error downloading certificate file data: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None


# ============================================
# EASY-TO-USE FUNCTIONS
# ============================================

def upload(local_file: str, onedrive_folder: str = "/"):
    """Upload a file to OneDrive"""
    client = OneDriveClient(ONEDRIVE_CLIENT_ID)
    return client.upload_file(local_file, onedrive_folder)

def download(onedrive_file: str, local_path: str = None):
    """Download a file from OneDrive"""
    client = OneDriveClient(ONEDRIVE_CLIENT_ID)
    return client.download_file(onedrive_file, local_path)

def list_folder(folder: str = "/"):
    """List files in OneDrive folder"""
    client = OneDriveClient(ONEDRIVE_CLIENT_ID)
    return client.list_files(folder)

def search(query: str):
    """Search for files in OneDrive"""
    client = OneDriveClient(ONEDRIVE_CLIENT_ID)
    return client.search_files(query)