import requests
import os
import json

class ExcelOnlineClient:
    """Client for Excel on OneDrive with environment-based authentication"""
    
    def __init__(self, client_id: str = None):
        self.session_id = None
        self.headers = None
        self._refresh_headers()
    
    def _refresh_headers(self):
        """Refresh authentication headers from environment or cache"""
        try:
            # Use environment variable for access token
            access_token = os.getenv("ONEDRIVE_ACCESS_TOKEN")
            if access_token:
                self.headers = {"Authorization": f"Bearer {access_token}"}
                return
            
            # Try to load from cache file
            auth_cache_file = os.getenv("AUTH_CACHE_FILE", "auth_cache.json")
            if os.path.exists(auth_cache_file):
                with open(auth_cache_file, 'r') as f:
                    cache = json.load(f)
                    access_token = cache.get("access_token")
                    if access_token:
                        self.headers = {"Authorization": f"Bearer {access_token}"}
                        return
            
            print("Warning: No authentication available for Excel operations")
            self.headers = {}
        except Exception as e:
            print(f"❌ Error refreshing headers: {e}")
            self.headers = {}
    
    def _get_drive_id(self, item_id: str):
        """Extract drive ID from item ID"""
        return item_id.split('!')[0] if '!' in item_id else item_id
    
    def create_session(self, item_id: str):
        """Create a workbook session for better performance"""
        drive_id = self._get_drive_id(item_id)
        url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{item_id}/workbook/createSession"
        payload = {"persistChanges": True}
        response = requests.post(url, headers=self.headers, json=payload)
        
        if response.status_code in [200, 201]:
            self.session_id = response.json().get("id")
            self.headers["workbook-session-id"] = self.session_id
            print(f"✅ Session created")
        elif response.status_code == 401:
            print(f"🔄 Session creation failed due to auth, refreshing token...")
            self._refresh_headers()
            # Retry once with refreshed headers
            response = requests.post(url, headers=self.headers, json=payload)
            if response.status_code in [200, 201]:
                self.session_id = response.json().get("id")
                self.headers["workbook-session-id"] = self.session_id
                print(f"✅ Session created after token refresh")
            else:
                print(f"⚠️  Session creation failed, continuing without session")
        else:
            print(f"⚠️  Session creation failed, continuing without session")
    
    def close_session(self, item_id: str):
        """Close the workbook session"""
        if self.session_id:
            drive_id = self._get_drive_id(item_id)
            url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{item_id}/workbook/closeSession"
            requests.post(url, headers=self.headers)
            if "workbook-session-id" in self.headers:
                del self.headers["workbook-session-id"]
            print("✅ Session closed")
    
    def list_worksheets(self, item_id: str):
        """List all worksheets"""
        drive_id = self._get_drive_id(item_id)
        url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{item_id}/workbook/worksheets"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            sheets = response.json().get("value", [])
            return sheets
        else:
            return None
    
    def get_table_name(self, item_id: str):
        """Get the first table name (or None if no tables exist)"""
        drive_id = self._get_drive_id(item_id)
        url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{item_id}/workbook/tables"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            tables = response.json().get("value", [])
            if tables:
                table_name = tables[0].get("name")
                print(f"✅ Found table: '{table_name}'")
                return table_name
            else:
                print("⚠️  No tables found")
                return None
        else:
            print(f"❌ Error listing tables: {response.status_code}")
            return None
    
    def create_table(self, item_id: str, worksheet_name: str, range_address: str, table_name: str):
        """Create a table from a range"""
        drive_id = self._get_drive_id(item_id)
        url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{item_id}/workbook/tables/add"
        
        payload = {
            "address": f"{worksheet_name}!{range_address}",
            "hasHeaders": True,
            "name": table_name
        }
        
        response = requests.post(url, headers=self.headers, json=payload)
        
        if response.status_code in [200, 201]:
            print(f"✅ Table '{table_name}' created successfully!")
            return response.json()
        else:
            print(f"❌ Error creating table: {response.text}")
            return None
    
    def write_range(self, item_id: str, worksheet_name: str, range_address: str, values: list):
        """Write to a range in worksheet"""
        drive_id = self._get_drive_id(item_id)
        url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{item_id}/workbook/worksheets/{worksheet_name}/range(address='{range_address}')"
        
        payload = {"values": values}
        response = requests.patch(url, headers=self.headers, json=payload)
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            print(f"🔄 Write failed due to auth, refreshing token...")
            self._refresh_headers()
            # Retry once with refreshed headers
            response = requests.patch(url, headers=self.headers, json=payload)
            if response.status_code == 200:
                print(f"✅ Write successful after token refresh")
                return response.json()
            else:
                error_msg = f"❌ Error writing range after token refresh: {response.text}"
                print(error_msg)
                return None
        else:
            error_msg = f"❌ Error writing range: {response.text}"
            if "invalidRequest" in response.text and "item ID is not valid" in response.text:
                error_msg += f"\n💡 Tip: Check that EXCEL_ITEM_ID in .env matches your Excel file and authentication"
            print(error_msg)
            return None
    
    def add_row_to_table(self, item_id: str, table_name: str, row_data: list):
        """Add a single row to table"""
        drive_id = self._get_drive_id(item_id)
        url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{item_id}/workbook/tables/{table_name}/rows"
        
        # The API expects values wrapped in another array
        payload = {
            "values": [row_data]
        }
        
        response = requests.post(url, headers=self.headers, json=payload)
        
        if response.status_code in [200, 201]:
            print("✅ Row added successfully!")
            return response.json()
        else:
            print(f"❌ Error adding row: {response.text}")
            return None


# ============================================
# SIMPLE USAGE - NO LOGIN AFTER FIRST TIME!
# ============================================

def add_data_to_excel(certificate_no: str, issue_date: str, company_reg_no: str, company_name: str, certificate_url: str = ""):
    """Add certificate data to Excel table"""
    
    CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
    ITEM_ID = os.getenv("EXCEL_ITEM_ID")
    if not ITEM_ID:
        print("❌ EXCEL_ITEM_ID is not set in environment. Set it in .env to use Excel operations.")
        return None
    WORKSHEET_NAME = "Table1"
    TABLE_NAME = "Table1"
    
    try:
        # Initialize (uses cached auth - NO LOGIN!)
        excel = ExcelOnlineClient(CLIENT_ID)
        
        # Create session for better performance
        excel.create_session(ITEM_ID)
        
        # Get table name
        existing_table = excel.get_table_name(ITEM_ID)
        
        # If no table, create one
        if not existing_table:
            print("\n🔨 Setting up table for first time...")
            
            # Write headers
            excel.write_range(ITEM_ID, WORKSHEET_NAME, "A1:C1", [
                ["Name", "Language", "Status"]
            ])
            
            # Write initial row
            excel.write_range(ITEM_ID, WORKSHEET_NAME, "A2:C2", [
                ["Sample", "Python", "Initial"]
            ])
            
            # Create table
            result = excel.create_table(ITEM_ID, WORKSHEET_NAME, "A1:C2", TABLE_NAME)
            
            if result:
                existing_table = TABLE_NAME
            else:
                print("❌ Failed to create table")
                excel.close_session(ITEM_ID)
                return False
        
        # Add the new row
        print(f"➕ Adding: {certificate_no}, {issue_date}, {company_reg_no}, {company_name}")
        result = excel.add_row_to_table(ITEM_ID, existing_table, [certificate_no, issue_date, company_reg_no, company_name, certificate_url])
        
        # Close session
        excel.close_session(ITEM_ID)
        
        return result is not None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============================================
# AGENT INTEGRATION FUNCTIONS
# ============================================

# Excel configuration - using same credentials as template
AZURE_CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
EXCEL_ITEM_ID = os.getenv("EXCEL_ITEM_ID")
EXCEL_WORKSHEET_NAME = os.getenv("EXCEL_WORKSHEET_NAME") or "Sheet1"
EXCEL_TABLE_NAME = os.getenv("EXCEL_TABLE_NAME") or "Certificates"

# Global client instance
_excel_client = None

def get_excel_client():
    """Get or create Excel client instance"""
    global _excel_client
    if _excel_client is None:
        if not AZURE_CLIENT_ID:
            raise Exception("AZURE_CLIENT_ID not configured in environment")
        _excel_client = ExcelOnlineClient(AZURE_CLIENT_ID)
    return _excel_client

def get_table_rows(item_id: str, table_name: str):
    """Get all rows from a table"""
    excel = get_excel_client()
    drive_id = item_id.split('!')[0] if '!' in item_id else item_id
    url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{item_id}/workbook/tables/{table_name}/rows"
    
    response = requests.get(url, headers=excel.headers)
    
    if response.status_code == 200:
        return response.json().get("value", [])
    else:
        print(f"❌ Error reading table rows: {response.text}")
        return []

def read_certificates_from_excel():
    """Read all certificate records from Excel Online - directly from worksheet cells"""
    from typing import List, Dict
    try:
        if not EXCEL_ITEM_ID:
            print("Excel not configured (missing EXCEL_ITEM_ID)")
            return []
        
        excel = get_excel_client()
        excel.create_session(EXCEL_ITEM_ID)
        
        # Read directly from worksheet cells instead of table
        # Read a large range to capture all data (now includes E column for URL)
        drive_id = EXCEL_ITEM_ID.split('!')[0] if '!' in EXCEL_ITEM_ID else EXCEL_ITEM_ID
        range_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{EXCEL_ITEM_ID}/workbook/worksheets/{EXCEL_WORKSHEET_NAME}/range(address='A1:E100')"
        range_response = requests.get(range_url, headers=excel.headers)
        
        excel.close_session(EXCEL_ITEM_ID)
        
        if range_response.status_code == 200:
            range_data = range_response.json()
            values = range_data.get("values", [])
            
            certificates = []
            # Start from row 2 (skip header row 1)
            for i in range(1, len(values)):
                row = values[i]
                if len(row) >= 4 and any(str(cell).strip() for cell in row):  # Non-empty row
                    # Handle Excel date serial numbers
                    issue_date = row[1] if row[1] else ""
                    if isinstance(issue_date, (int, float)) and issue_date > 30000:  # Excel date serial number
                        try:
                            from datetime import datetime, timedelta
                            excel_epoch = datetime(1899, 12, 30)
                            issue_date = (excel_epoch + timedelta(days=int(issue_date))).strftime('%Y-%m-%d')
                        except Exception:
                            issue_date = str(issue_date)
                    else:
                        issue_date = str(issue_date) if issue_date else ""
                    
                    certificates.append({
                        "certificate_no": str(row[0]) if row[0] else "",
                        "issue_date": issue_date,
                        "company_reg_no": str(row[2]) if row[2] else "",
                        "company_name": str(row[3]) if row[3] else "",
                        "certificate_url": str(row[4]) if len(row) > 4 and row[4] else ""
                    })
            
            print(f"✅ Read {len(certificates)} certificates from Excel worksheet")
            return certificates
        else:
            print(f"❌ Error reading from Excel worksheet: {range_response.status_code}")
            return []
        
    except Exception as e:
        print(f"Error reading from Excel: {e}")
        import traceback
        traceback.print_exc()
        return []

def write_certificate_to_excel(certificate_data):
    """Write a new certificate record to Excel Online"""
    try:
        if not EXCEL_ITEM_ID:
            print("Excel not configured (missing EXCEL_ITEM_ID)")
            return False
        
        excel = get_excel_client()
        excel.create_session(EXCEL_ITEM_ID)
        
        # Find the actual next empty row by reading current data
        next_row = 2  # Start from row 2 (after headers)
        
        # Check if headers exist, if not write them
        drive_id = EXCEL_ITEM_ID.split('!')[0] if '!' in EXCEL_ITEM_ID else EXCEL_ITEM_ID
        headers_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{EXCEL_ITEM_ID}/workbook/worksheets/{EXCEL_WORKSHEET_NAME}/range(address='A1:G1')"
        headers_response = requests.get(headers_url, headers=excel.headers)
        
        if headers_response.status_code == 200:
            header_data = headers_response.json()
            values = header_data.get("values", [[]])
            header_values = values[0] if values else []
            if not any(str(cell).strip() for cell in header_values if cell):
                # No headers, write them
                print("Writing headers to worksheet...")
                excel.write_range(EXCEL_ITEM_ID, EXCEL_WORKSHEET_NAME, "A1:G1", [
                    ["Certificate No", "Issue Date", "Company Reg No", "Company Name", "Certificate URL", "products_code", "products_name"]
                ])
        
        # Read down from row 2 to find the first empty row
        max_check_rows = 100  # Check up to 100 rows to find empty spot
        for row_num in range(2, max_check_rows + 2):
            drive_id = EXCEL_ITEM_ID.split('!')[0] if '!' in EXCEL_ITEM_ID else EXCEL_ITEM_ID
            check_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{EXCEL_ITEM_ID}/workbook/worksheets/{EXCEL_WORKSHEET_NAME}/range(address='A{row_num}:A{row_num}')"
            check_response = requests.get(check_url, headers=excel.headers)
            
            if check_response.status_code == 200:
                cell_data = check_response.json()
                cell_values = cell_data.get("values", [[]])
                cell_value = cell_values[0] if cell_values else []
                if not cell_value or not str(cell_value[0] if cell_value else "").strip():
                    # Found empty row
                    next_row = row_num
                    break
            else:
                # If we can't read the cell, assume it's empty
                next_row = row_num
                break
        
        # Prepare row data (now includes certificate URL)
        row_data = [
            certificate_data.get('certificate_no', ''),
            certificate_data.get('issue_date', ''),
            certificate_data.get('company_reg_no', ''),
            certificate_data.get('company_name', ''),
            certificate_data.get('certificate_url', ''),
            certificate_data.get('products_code', ''),
            certificate_data.get('products_name', ''),
        ]
        
        # Write directly to worksheet cells (now A-G columns)
        range_address = f"A{next_row}:G{next_row}"
        print(f"Writing to Excel {range_address}: {row_data}")
        
        result = excel.write_range(EXCEL_ITEM_ID, EXCEL_WORKSHEET_NAME, range_address, [row_data])
        
        if result:
            print(f"Successfully wrote certificate {certificate_data.get('certificate_no')} to Excel row {next_row}")
            
            # Try to ensure the data is part of a table for better functionality
            try:
                # Check if table exists, if not create one
                table_name = excel.get_table_name(EXCEL_ITEM_ID)
                if not table_name:
                    # Create table with the current data range (now includes G column)
                    table_range = f"A1:G{next_row}"
                    excel.create_table(EXCEL_ITEM_ID, EXCEL_WORKSHEET_NAME, table_range, EXCEL_TABLE_NAME)
                    print(f"Created table covering range {table_range}")
            except Exception as table_error:
                print(f"Note: Could not create/update table, but data was written: {table_error}")
            
            excel.close_session(EXCEL_ITEM_ID)
            return True
        else:
            print("Failed to write to Excel")
            excel.close_session(EXCEL_ITEM_ID)
            return False
            
    except Exception as e:
        print(f"Error writing to Excel: {e}")
        import traceback
        traceback.print_exc()
        return False

def find_certificate_in_excel(certificate_no: str):
    """Find a specific certificate in Excel by certificate number"""
    from typing import Optional, Dict
    try:
        certificates = read_certificates_from_excel()
        
        # Normalize the search certificate number
        normalized_search = normalize_certificate_no(certificate_no)
        
        for cert in certificates:
            normalized_db = normalize_certificate_no(cert.get('certificate_no', ''))
            if normalized_db.upper() == normalized_search.upper():
                return cert
        
        return None
        
    except Exception as e:
        print(f"Error finding certificate in Excel: {e}")
        return None

def normalize_certificate_no(cert_no: str) -> str:
    """Normalize certificate number by replacing various dash characters with standard hyphen"""
    if not cert_no:
        return ""
    # Replace em-dash, en-dash, and other dash variants with standard hyphen
    return cert_no.replace('–', '-').replace('—', '-').replace('―', '-').strip()

