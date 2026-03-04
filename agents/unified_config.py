#!/usr/bin/env python3
"""
Unified configuration system for Excel and OneDrive
Detects when they're on the same account and optimizes configuration
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class UnifiedConfig:
    """Unified configuration for Excel and OneDrive integration"""
    
    def __init__(self):
        self._analyze_configuration()
    
    def _analyze_configuration(self):
        """Analyze the configuration to detect unified setup"""
        # Use Azure client ID for both Excel and OneDrive
        self.azure_client_id = os.getenv("AZURE_CLIENT_ID")
        self.excel_item_id = os.getenv("EXCEL_ITEM_ID")
        self.excel_worksheet_name = os.getenv("EXCEL_WORKSHEET_NAME")
        self.excel_table_name = os.getenv("EXCEL_TABLE_NAME")
        
        # Support both new and old environment variable names
        self.shared_folder_id = (
            os.getenv("CERTIFICATE_FOLDER_ID") or 
            os.getenv("ONEDRIVE_SHARED_FOLDER_ID")
        )
        self.shared_drive_id = os.getenv("ONEDRIVE_SHARED_DRIVE_ID")
        self.shared_folder_url = os.getenv("ONEDRIVE_SHARED_FOLDER_URL")
        
        # Extract drive ID from Excel item ID
        self.excel_drive_id = None
        if self.excel_item_id and "!" in self.excel_item_id:
            self.excel_drive_id = self.excel_item_id.split("!")[0].lower()
        
        # Check if Excel and OneDrive are on the same account
        # If shared_drive_id is not specified, assume unified account if folder_id is present
        if not self.shared_drive_id and self.shared_folder_id and self.excel_drive_id:
            self.shared_drive_id = self.excel_drive_id
            print(f"🔄 Auto-detected drive ID from Excel configuration: {self.shared_drive_id}")
        
        self.is_unified_account = (
            self.excel_drive_id and 
            self.shared_folder_id and
            (not self.shared_drive_id or self.excel_drive_id.lower() == self.shared_drive_id.lower())
        )
        
        if self.is_unified_account:
            print(f"🔄 Detected unified configuration: Excel and OneDrive on same account")
            print(f"   📊 Excel Drive ID: {self.excel_drive_id}")
            print(f"   📁 OneDrive Drive ID: {self.shared_drive_id}")
            print(f"   ✅ Using optimized unified approach")
        else:
            print(f"🔍 Detected separate configurations:")
            print(f"   📊 Excel Drive ID: {self.excel_drive_id}")
            print(f"   📁 OneDrive Drive ID: {self.shared_drive_id}")
    
    def get_certificate_folder_config(self):
        """Get the certificate folder configuration"""
        if self.is_unified_account and self.shared_folder_id:
            return {
                'type': 'shared_folder',
                'drive_id': self.shared_drive_id,
                'folder_id': self.shared_folder_id,
                'folder_name': 'HCO_Staging_Certificate',
                'client_id': self.azure_client_id
            }
        else:
            return {
                'type': 'own_folder',
                'drive_id': self.excel_drive_id,
                'folder_name': 'HCO_Staging_Certificate',
                'client_id': self.azure_client_id
            }
    
    def get_excel_config(self):
        """Get Excel configuration"""
        return {
            'client_id': self.azure_client_id,
            'item_id': self.excel_item_id,
            'worksheet_name': self.excel_worksheet_name,
            'table_name': self.excel_table_name,
            'drive_id': self.excel_drive_id
        }
    
    def should_use_fallback(self):
        """Check if fallback mechanism is needed"""
        # If unified account, no fallback needed - everything is on same account
        if self.is_unified_account:
            return False
        
        # If different accounts or missing shared config, use fallback
        return bool(self.shared_drive_id and self.shared_drive_id != self.excel_drive_id)

# Create global unified config instance
_unified_config = None

def get_unified_config():
    """Get or create unified configuration instance"""
    global _unified_config
    if _unified_config is None:
        _unified_config = UnifiedConfig()
    return _unified_config

def optimize_env_config():
    """Optimize environment configuration by removing redundant variables"""
    config = get_unified_config()
    
    if config.is_unified_account:
        print(f"\n💡 Optimization suggestions for .env:")
        print(f"Since Excel and OneDrive are on the same account, you can simplify your configuration:")
        print(f"")
        print(f"# Simplified Configuration (same account)")
        print(f"AZURE_CLIENT_ID={config.azure_client_id}")
        print(f"EXCEL_ITEM_ID={config.excel_item_id}")
        print(f"EXCEL_WORKSHEET_NAME={config.excel_worksheet_name}")
        print(f"EXCEL_TABLE_NAME={config.excel_table_name}")
        print(f"")
        print(f"# Certificate folder on same account")
        print(f"CERTIFICATE_FOLDER_ID={config.shared_folder_id}")
        print(f"# Note: ONEDRIVE_SHARED_DRIVE_ID not needed - same as Excel drive")
        print(f"")
        
        return True
    else:
        print(f"\n📋 Your current configuration uses separate accounts:")
        print(f"   📊 Excel: {config.excel_drive_id}")
        print(f"   📁 OneDrive: {config.shared_drive_id}")
        print(f"   ✅ Current configuration is optimal for separate accounts")
        
        return False