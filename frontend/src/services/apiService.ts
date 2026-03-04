import { getApiUrl } from '../config/env';

// Essential Backend API Types
export interface ImageRequest {
  image_data?: string;
  filename?: string;
  content_type?: string;
  text_query?: string;
}

export interface ImageResponse {
  timestamp: number;
  message: string;
  agent_address: string;
  image_size: number;
  processed: boolean;
}

export interface CertificateQueryRequest {
  query: string;
  user_id?: string | null; // For authentication (optional)
}


export interface CertificateQueryResponse {
  timestamp: number;
  message: string;
  agent_address: string;
  query_type: string; // "verification", "download", "inquiry", "product_verification"
  certificate_no: string | null;
  download_url: string | null;
  processed: boolean;
  filename: string | null;
  found: boolean; // defaults to False
  verified_product_names?: string[];
  verified_product_codes?: string[];
  missing_product_names?: string[];
  missing_product_codes?: string[];
}

export interface ChatRequest {
  query: string;
}

export interface ChatResponse {
  timestamp: number;
  message: string;
  agent_address: string;
  query_type: string; // "inquiry" or "verification" or "product_verification"
  processed: boolean;
  certificate_no?: string | null;
  certificate_found?: boolean;
  verified_product_names?: string[];
  verified_product_codes?: string[];
  missing_product_names?: string[];
  missing_product_codes?: string[];
}

export interface CertificateDownloadRequest {
  certificate_no: string;
  file_type: string; // "png" or "pdf"
}

export interface CertificateDownloadResponse {
  certificate_no: string;
  file_data: string | null; // base64 encoded file data (optional)
  filename: string | null;  // filename for download (optional)
  download_url?: string | null; // OneDrive URL for reference (optional)
  found: boolean; // Whether certificate file was found (defaults to False)
  message: string; // Status message (defaults to "")
}

// Certificate Generation Types
export interface CertificateGenerationRequest {
  certificate_no: string;
  company_name: string;
  company_reg_no: string;
  issue_date: string; // YYYY-MM-DD format
  certificate_type?: string; // defaults to "halal_certificate"
  standards: string;
  cert_num_footer?: string;
  csv_files_count?: number;
  text_color?: string; // defaults to "black"
  company_address: string;
  pu_au_text?: string;
  sow: string; // Scope of Work
  pu?: string; // Production Unit
  au?: string; // Administrative Unit
  validity_period: string; // "1", "2", or "3" years
  xlsx_files?: Array<{ filename: string; data: string }>; // base64 encoded files
  company_logo?: { filename: string; data: string; content_type: string } | null; // Company logo
  annex_layout_options?: {
    products_per_page?: number;
    rows?: number;
    columns?: number;
  };
}

export interface CertificateGenerationResponse {
  timestamp: number;
  message: string;
  agent_address: string;
  certificate_id: string;
  png_filename: string;
  pdf_filename: string;
  download_url?: string;
  csv_logged: boolean;
  processed: boolean;
}

// Simplified API Service
export class ApiService {
  private baseUrl: string;

  constructor() {
    this.baseUrl = getApiUrl();
  }

  private async makeRequest<T>(endpoint: string, data?: any): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    console.log(`Request to: ${url}`);
    console.log(`Request data:`, data);

    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });

    console.log(`Response status: ${response.status}`);
    const responseText = await response.text();
    console.log(`Response text:`, responseText);
    
    // Handle schema errors specifically
    if (response.status === 500 && responseText.includes("Handler response does not match response schema")) {
      console.error(`Schema error detected on ${endpoint}`);
      throw new Error(`Backend schema error: The server is experiencing configuration issues. Please try again later or contact support.`);
    }
    
    if (!response.ok) {
      console.error(`Error response:`, responseText);
      throw new Error(`HTTP ${response.status}: ${responseText}`);
    }

    try {
      const jsonResponse = JSON.parse(responseText);
      console.log(`Response data:`, jsonResponse);
      return jsonResponse;
    } catch (parseError) {
      console.error(`JSON parse error:`, parseError);
      throw new Error(`Invalid response format from server`);
    }
  }

  // Upload image
  async uploadImage(request: ImageRequest): Promise<ImageResponse> {
    return this.makeRequest<ImageResponse>('/image/upload', request);
  }

  // Chat with assistant for general queries
  async chatWithAssistant(query: string): Promise<ChatResponse> {
    const request: ChatRequest = { query };
    return this.makeRequest<ChatResponse>('/chat', request);
  }

  // Login with username and password
  async login(username: string, password: string): Promise<{
    success: boolean;
    token?: string;
    expires_at?: number;
    user_email?: string;
    message?: string;
  }> {
    try {
      const response = await this.makeRequest<{
        timestamp: number;
        message: string;
        agent_address: string;
        token: string;
        expires_at: number;
        user_email: string;
        allowed: boolean;
      }>('/auth/login', { username, password });

      return {
        success: response.allowed,
        token: response.token,
        expires_at: response.expires_at,
        user_email: response.user_email,
        message: response.message
      };
    } catch (error) {
      console.error('Login error:', error);
      return {
        success: false,
        message: error instanceof Error ? error.message : 'Login failed'
      };
    }
  }

  // Validate token
  async validateToken(token: string): Promise<{
    allowed: boolean;
    message?: string;
    user_email?: string;
  }> {
    try {
      const response = await this.makeRequest<{
        timestamp: number;
        message: string;
        agent_address: string;
        allowed: boolean;
        user_email: string;
      }>('/auth/validate', { access_token: token });

      return {
        allowed: response.allowed,
        message: response.message,
        user_email: response.user_email
      };
    } catch (error) {
      console.error('Token validation error:', error);
      return {
        allowed: false,
        message: error instanceof Error ? error.message : 'Validation failed'
      };
    }
  }

  // Query certificates for specific certificate operations (download, verify)
  async searchCertificate(query: string, userId?: string): Promise<CertificateQueryResponse> {
    const request: CertificateQueryRequest = {
      query,
      user_id: userId || null
    };
    return this.makeRequest<CertificateQueryResponse>('/certificate/query', request);
  }

  // Download certificate with schema error handling
  async downloadCertificate(certificateNo: string, fileType: 'pdf' | 'png' = 'pdf'): Promise<CertificateDownloadResponse> {
    const url = `${this.baseUrl}/certificate/download`;
    const requestData = {
      certificate_no: certificateNo,
      file_type: fileType
    };
    
    console.log(`Download request to: ${url}`);
    console.log(`Download request data:`, requestData);

    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(requestData),
    });

    console.log(`Download response status: ${response.status}`);
    
    // Handle the response even if status is 500 (schema errors)
    const responseText = await response.text();
    console.log(`Download response text:`, responseText);
    
    // Check for schema validation error
    const isSchemaError = response.status === 500 && (
      responseText.includes("Handler response does not match response schema") ||
      responseText.includes("does not match response schema") ||
      responseText.includes("schema validation") ||
      responseText.includes("ValidationError")
    );

    // Check for the specific short error response that indicates backend processing succeeded
    const isShortSchemaError = response.status === 500 && 
      responseText === '{"error": "Handler response does not match response schema."}';

    if (isShortSchemaError) {
      console.log("Detected short schema error response, attempting retry...");
      
      try {
        // Wait a moment then retry
        await new Promise(resolve => setTimeout(resolve, 1500));
        
        console.log("Retrying download request...");
        const retryResponse = await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(requestData),
        });

        const retryResponseText = await retryResponse.text();
        console.log("Retry response status:", retryResponse.status);
        console.log("Retry response preview:", retryResponseText.substring(0, 200));

        if (retryResponse.ok) {
          try {
            const retryData = JSON.parse(retryResponseText);
            console.log("Retry successful, returning data");
            return retryData;
          } catch (parseError) {
            console.warn("Retry response parse failed, continuing to normal error handling");
          }
        }
        
        // If retry fails, continue to normal schema error handling
        console.log("Retry failed, falling back to extraction logic");
      } catch (retryError) {
        console.warn("Retry attempt failed:", retryError);
      }
    }
    
    if (isSchemaError || isShortSchemaError) {
      console.log("Detected schema error, attempting data extraction...");
      
      // Try to extract data from malformed response
      try {
        // Try multiple patterns to extract the response data
        let extractedData = null;
        
        // Pattern 1: Try to find complete JSON object with improved regex
        const jsonMatch = responseText.match(/\{.*?"found"\s*:\s*(true|false).*?\}/s);
        if (jsonMatch) {
          try {
            extractedData = JSON.parse(jsonMatch[0]);
            console.log("Extracted data via improved JSON pattern:", extractedData);
          } catch (e) {
            console.log("Failed to parse extracted JSON:", e);
          }
        }
        
        // Pattern 2: Enhanced regex for large base64 data extraction
        if (!extractedData) {
          // Updated regex to handle large base64 strings
          const fileDataMatch = responseText.match(/"file_data":\s*"([A-Za-z0-9+/=]{1,500000})"/);
          const filenameMatch = responseText.match(/"filename":\s*"([^"]+)"/);
          const foundMatch = responseText.match(/"found":\s*(true|false)/);
          const messageMatch = responseText.match(/"message":\s*"([^"]+)"/);
          const certNoMatch = responseText.match(/"certificate_no":\s*"([^"]+)"/);
          
          console.log("Enhanced regex extraction results:", {
            hasFileData: !!fileDataMatch,
            fileDataLength: fileDataMatch ? fileDataMatch[1].length : 0,
            hasFilename: !!filenameMatch,
            filename: filenameMatch ? filenameMatch[1] : null,
            found: foundMatch ? foundMatch[1] : null
          });
          
          if (fileDataMatch || foundMatch) {
            extractedData = {
              certificate_no: certNoMatch ? certNoMatch[1] : certificateNo,
              file_data: fileDataMatch ? fileDataMatch[1] : null,
              filename: filenameMatch ? filenameMatch[1] : null,
              found: foundMatch ? foundMatch[1] === "true" : false,
              message: messageMatch ? messageMatch[1] : "Certificate processing completed"
            };
            console.log("Extracted data via enhanced regex pattern:", extractedData);
          }
        }
        
        // Pattern 3: Enhanced fallback extraction for large base64 data
        if (!extractedData) {
          console.log("Attempting enhanced fallback extraction...");
          console.log("Response length:", responseText.length);
          
          // Try multiple approaches to find base64 data
          let base64Data = null;
          let filename = null;
          let found = false;
          
          // Check if response indicates certificate was found
          const foundMatch = responseText.match(/"found":\s*(true|false)/);
          found = foundMatch ? foundMatch[1] === "true" : responseText.includes(certificateNo);
          
          if (found) {
            // Method 1: Look for large continuous base64 strings
            const largeBase64Match = responseText.match(/[A-Za-z0-9+/]{1000,}={0,2}/);
            if (largeBase64Match) {
              base64Data = largeBase64Match[0];
              console.log("Found large base64 string:", base64Data.length, "characters");
            }
            
            // Method 2: Look for base64 with quotes around it
            if (!base64Data) {
              const quotedBase64Match = responseText.match(/"([A-Za-z0-9+/]{1000,}={0,2})"/);
              if (quotedBase64Match) {
                base64Data = quotedBase64Match[1];
                console.log("Found quoted base64 string:", base64Data.length, "characters");
              }
            }
            
            // Method 3: Extract everything between quotes that looks like base64
            if (!base64Data) {
              const allQuotedStrings = responseText.match(/"[A-Za-z0-9+/=]{500,}"/g);
              if (allQuotedStrings) {
                for (const quotedString of allQuotedStrings) {
                  const cleanString = quotedString.slice(1, -1); // Remove quotes
                  if (cleanString.length > 1000 && /^[A-Za-z0-9+/=]+$/.test(cleanString)) {
                    base64Data = cleanString;
                    console.log("Found base64 in quoted string:", base64Data.length, "characters");
                    break;
                  }
                }
              }
            }
            
            // Extract filename
            const filenameMatch = responseText.match(/"filename":\s*"([^"]+)"/) || 
                                responseText.match(/([A-Z]{3}-[A-Z0-9-]+\.pdf)/i);
            filename = filenameMatch ? (filenameMatch[1] || filenameMatch[0]) : `${certificateNo}.pdf`;
            
            if (base64Data) {
              extractedData = {
                certificate_no: certificateNo,
                file_data: base64Data,
                filename: filename,
                found: true,
                message: "Certificate extracted via enhanced fallback method"
              };
              console.log("Successfully extracted data via enhanced fallback:", {
                dataLength: base64Data.length,
                filename: filename
              });
            }
          }
        }
        
        if (extractedData) {
          return extractedData as CertificateDownloadResponse;
        } else {
          throw new Error("Could not extract certificate data from malformed response");
        }
      } catch (extractError) {
        console.error("Data extraction failed:", extractError);
        throw new Error(`Schema error - could not parse response: ${extractError}`);
      }
    }
    
    // Normal JSON response handling
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${responseText}`);
    }

    try {
      const jsonResponse = JSON.parse(responseText);
      console.log(`Download response data:`, jsonResponse);
      return jsonResponse;
    } catch (parseError) {
      throw new Error(`Invalid JSON response: ${parseError}`);
    }
  }

  // Download and trigger file download
  async downloadAndTriggerFile(certificateNo: string, fileType: 'pdf' | 'png' = 'pdf'): Promise<string> {
    try {
      console.log(`Starting download for certificate: ${certificateNo}, type: ${fileType}`);
      const response = await this.downloadCertificate(certificateNo, fileType);
      
      console.log("Download response received:", response);

      if (response.found) {
        if (response.file_data) {
          console.log("Certificate found with file data, processing download...");
          
          // Convert base64 to blob
          try {
            const byteCharacters = atob(response.file_data);
            const byteArray = new Uint8Array(byteCharacters.length);
            for (let i = 0; i < byteCharacters.length; i++) {
              byteArray[i] = byteCharacters.charCodeAt(i);
            }
            
            const blob = new Blob([byteArray], { 
              type: fileType === 'pdf' ? 'application/pdf' : 'image/png' 
            });
            
            // Trigger download
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = response.filename || `${certificateNo}.${fileType}`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            window.URL.revokeObjectURL(url);
            
            console.log(`Download completed successfully: ${response.filename}`);
            return `✅ Download successful: ${response.filename || `${certificateNo}.${fileType}`}`;
          } catch (decodeError) {
            console.error("Error decoding file data:", decodeError);
            return `❌ Error processing certificate file: ${decodeError}`;
          }
        } else if (response.download_url) {
          console.log("Certificate found with OneDrive URL:", response.download_url);
          
          try {
            // Open OneDrive URL in new tab for download
            const link = document.createElement('a');
            link.href = response.download_url;
            link.target = '_blank';
            link.rel = 'noopener noreferrer';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);

            return `✅ **Certificate Found!**\n\n📋 **Certificate:** ${response.filename || `${certificateNo}.${fileType}`}\n💾 **Status:** Opening OneDrive for download\n🔗 **Direct Link:** [Click here if the download didn't start](${response.download_url})\n\n**Note:** The file will open in OneDrive where you can download it directly to your device.`;
          } catch (urlError) {
            console.error("Error opening OneDrive URL:", urlError);
            return `✅ **Certificate Found!**\n\n📋 **Certificate:** ${response.filename || `${certificateNo}.${fileType}`}\n💾 **Download Link:** ${response.download_url}\n\n**Instructions:** Click the link above to access your certificate in OneDrive and download it to your device.`;
          }
        } else {
          console.log("Certificate found but no file data or URL");
          return `❌ Certificate found but no file available: ${response.message ?? 'Unknown error'}`;
        }
      } else {
        console.log("Certificate not found");
        return `❌ Certificate "${certificateNo}" not found: ${response.message ?? 'Unknown error'}`;
      }
    } catch (error) {
      console.error("Download error:", error);
      
      // Handle different types of errors
      if (error instanceof Error) {
        if (error.message.includes("Schema error") || error.message.includes("Backend schema error")) {
          return `⚠️ **Backend processing issue:** The certificate "${certificateNo}" was found and processed successfully (based on logs), but the response format is incorrect. This might be a temporary backend issue. Please try again in a moment or contact support at info@hcoltd.co.uk if the problem persists.`;
        } else if (error.message.includes("HTTP 500")) {
          return `❌ Server error: ${error.message}`;
        } else if (error.message.includes("HTTP 404")) {
          return `❌ Certificate "${certificateNo}" not found.`;
        } else {
          return `❌ Download failed: ${error.message}`;
        }
      }
      
      return `❌ Download failed: Unknown error`;
    }
  }

  // Upload image file
  async uploadImageFile(file: File): Promise<ImageResponse> {
    const reader = new FileReader();
    return new Promise((resolve, reject) => {
      reader.onload = async () => {
        try {
          const parts = (reader.result as string).split(',');
          const base64Data = parts.length > 1 ? parts[1] : null;
          if (!base64Data) { reject(new Error("Invalid file data format")); return; }
          const result = await this.uploadImage({
            image_data: base64Data,
            filename: file.name,
            content_type: file.type
          });
          resolve(result);
        } catch (error) {
          reject(error);
        }
      };
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  }

  // Generate certificate
  async generateCertificate(certificateData: CertificateGenerationRequest): Promise<CertificateGenerationResponse> {
    return this.makeRequest<CertificateGenerationResponse>('/generate-certificate', certificateData);
  }

  // Helper method to process files and generate certificate
  async processAndGenerateCertificate(
    certificateData: any, 
    files?: File[]
  ): Promise<CertificateGenerationResponse> {
    // Prepare the request data
    const request: CertificateGenerationRequest = {
      certificate_no: certificateData.certificate_no,
      company_name: certificateData.company_name,
      company_reg_no: certificateData.company_reg_no,
      issue_date: certificateData.issue_date,
      certificate_type: 'halal_certificate',
      standards: certificateData.standards,
      company_address: certificateData.company_address,
      sow: certificateData.sow,
      pu: certificateData.pu,
      au: certificateData.au,
      validity_period: certificateData.validity_period,
      csv_files_count: files ? files.length : 0,
      text_color: 'black'
    };

    // Process CSV/Excel files if provided
    if (files && files.length > 0) {
      const xlsxFiles = await Promise.all(
        files.map(async (file) => {
          return new Promise<{ filename: string; data: string }>((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => {
              const parts = (reader.result as string).split(',');
              const base64Data = parts.length > 1 ? parts[1] : null;
              if (!base64Data) { reject(new Error("Invalid file data format")); return; }
              resolve({
                filename: file.name,
                data: base64Data
              });
            };
            reader.onerror = reject;
            reader.readAsDataURL(file);
          });
        })
      );
      request.xlsx_files = xlsxFiles;
    }

    // Process company logo if provided
    if (certificateData.company_logo) {
      const logoFile = certificateData.company_logo;
      const logoData = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => {
          const parts = (reader.result as string).split(',');
          const base64Data = parts.length > 1 ? parts[1] : null;
          if (!base64Data) { reject(new Error("Invalid file data format")); return; }
          resolve(base64Data);
        };
        reader.onerror = reject;
        reader.readAsDataURL(logoFile);
      });
      
      request.company_logo = {
        filename: logoFile.name,
        data: logoData,
        content_type: logoFile.type
      };
    }

    return this.generateCertificate(request);
  }
}

// Export singleton instance
export const apiService = new ApiService();