import { authService } from './authService';

export interface ApiRequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
  body?: any;
  headers?: Record<string, string>;
}

class MicrosoftApiService {
  private baseUrl = 'https://graph.microsoft.com/v1.0';

  /**
   * Make an authenticated API request with automatic token refresh
   */
  async makeAuthenticatedRequest<T = any>(
    endpoint: string, 
    options: ApiRequestOptions = {}
  ): Promise<T> {
    const accessToken = await authService.getAccessToken();
    
    if (!accessToken) {
      throw new Error('No access token available. Please log in again.');
    }

    const url = endpoint.startsWith('http') ? endpoint : `${this.baseUrl}${endpoint}`;
    
    const requestOptions: RequestInit = {
      method: options.method || 'GET',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
        ...options.headers,
      },
    };

    if (options.body) {
      requestOptions.body = typeof options.body === 'string' 
        ? options.body 
        : JSON.stringify(options.body);
    }

    try {
      const response = await fetch(url, requestOptions);
      
      if (response.status === 401) {
        // Token might be expired, try to refresh and retry once
        console.log('Received 401, attempting token refresh...');
        await authService.checkAndRefreshToken();
        
        const newAccessToken = await authService.getAccessToken();
        if (newAccessToken) {
          requestOptions.headers = {
            ...requestOptions.headers,
            'Authorization': `Bearer ${newAccessToken}`,
          };
          
          const retryResponse = await fetch(url, requestOptions);
          if (!retryResponse.ok) {
            throw new Error(`API request failed: ${retryResponse.statusText}`);
          }
          return await retryResponse.json();
        }
        throw new Error('Authentication failed. Please log in again.');
      }

      if (!response.ok) {
        throw new Error(`API request failed: ${response.statusText}`);
      }

      // Handle empty responses
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        return await response.json();
      }
      
      return response.text() as unknown as T;
    } catch (error) {
      console.error('API request failed:', error);
      throw error;
    }
  }

  /**
   * Get user profile from Microsoft Graph
   */
  async getUserProfile(): Promise<any> {
    return this.makeAuthenticatedRequest('/me');
  }

  /**
   * Get user's OneDrive files
   */
  async getOneDriveFiles(folderId?: string): Promise<any> {
    const endpoint = folderId ? `/me/drive/items/${folderId}/children` : '/me/drive/root/children';
    return this.makeAuthenticatedRequest(endpoint);
  }

  /**
   * Get SharePoint sites the user has access to
   */
  async getSharePointSites(): Promise<any> {
    return this.makeAuthenticatedRequest('/sites?search=*');
  }

  /**
   * Get files from a specific SharePoint site
   */
  async getSharePointSiteFiles(siteId: string): Promise<any> {
    return this.makeAuthenticatedRequest(`/sites/${siteId}/drive/root/children`);
  }

  /**
   * Upload file to OneDrive
   */
  async uploadToOneDrive(fileName: string, content: string | Blob, folderId?: string): Promise<any> {
    const endpoint = folderId 
      ? `/me/drive/items/${folderId}:/${fileName}:/content`
      : `/me/drive/root:/${fileName}:/content`;

    return this.makeAuthenticatedRequest(endpoint, {
      method: 'PUT',
      body: content,
      headers: {
        'Content-Type': 'application/octet-stream',
      },
    });
  }

  /**
   * Download file from OneDrive
   */
  async downloadFromOneDrive(fileId: string): Promise<Blob> {
    const endpoint = `/me/drive/items/${fileId}/content`;
    const response = await this.makeAuthenticatedRequest(endpoint);
    return response;
  }

  /**
   * Create folder in OneDrive
   */
  async createOneDriveFolder(folderName: string, parentFolderId?: string): Promise<any> {
    const endpoint = parentFolderId 
      ? `/me/drive/items/${parentFolderId}/children`
      : '/me/drive/root/children';

    return this.makeAuthenticatedRequest(endpoint, {
      method: 'POST',
      body: {
        name: folderName,
        folder: {},
        '@microsoft.graph.conflictBehavior': 'rename',
      },
    });
  }

  /**
   * Get Excel workbook worksheets
   */
  async getWorkbookWorksheets(fileId: string): Promise<any> {
    return this.makeAuthenticatedRequest(`/me/drive/items/${fileId}/workbook/worksheets`);
  }

  /**
   * Read data from Excel worksheet
   */
  async readExcelWorksheet(fileId: string, worksheetName: string, range?: string): Promise<any> {
    const endpoint = range 
      ? `/me/drive/items/${fileId}/workbook/worksheets/${worksheetName}/range(address='${range}')`
      : `/me/drive/items/${fileId}/workbook/worksheets/${worksheetName}/usedRange`;
    
    return this.makeAuthenticatedRequest(endpoint);
  }

  /**
   * Write data to Excel worksheet
   */
  async writeExcelWorksheet(fileId: string, worksheetName: string, range: string, values: any[][]): Promise<any> {
    const endpoint = `/me/drive/items/${fileId}/workbook/worksheets/${worksheetName}/range(address='${range}')`;
    
    return this.makeAuthenticatedRequest(endpoint, {
      method: 'PATCH',
      body: { values },
    });
  }

  /**
   * Check user permissions for a file/folder
   */
  async checkPermissions(itemId: string): Promise<any> {
    return this.makeAuthenticatedRequest(`/me/drive/items/${itemId}/permissions`);
  }

  /**
   * Share a file or folder
   */
  async shareItem(itemId: string, recipientEmail: string, role: 'read' | 'write' = 'read'): Promise<any> {
    return this.makeAuthenticatedRequest(`/me/drive/items/${itemId}/invite`, {
      method: 'POST',
      body: {
        recipients: [{ email: recipientEmail }],
        message: 'Shared via HCO application',
        requireSignIn: true,
        sendInvitation: true,
        roles: [role],
      },
    });
  }
}

// Export singleton instance
export const microsoftApiService = new MicrosoftApiService();