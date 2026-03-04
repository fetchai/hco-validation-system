// Simple certificate generation service without external dependencies

export interface CertificateData {
  issue_date: string;
  certificate_no: string;
  standards: string;
  company_name: string;
  company_address: string;
  pu?: string; // Production Unit (optional - either PU or AU)
  au?: string; // Administrative Unit (optional - either PU or AU)
  sow: string; // SOW (Scope of Work)
  validity_period: '1' | '2' | '3'; // 1, 2, or 3 years
  expiry_date?: string; // Auto-calculated at backend
  company_reg_no: string; // Registration number
  csv_files?: File[];
  company_logo?: File; // Optional company logo
}

export interface CertificateStep {
  id: string;
  question: string;
  placeholder?: string;
  type: 'text' | 'date' | 'select' | 'file';
  options?: string[];
  validation?: (value: string) => boolean;
}

export const certificateSteps: CertificateStep[] = [
  {
    id: 'issue_date',
    question: 'What is the issue date?',
    type: 'date',
    validation: (value: string) => {
      // Try multiple date formats
      const trimmed = value.trim();
      
      // Try direct parsing first
      let date = new Date(trimmed);
      if (!isNaN(date.getTime())) {
        return true;
      }
      
      // Try DD/MM/YYYY format (common in UK/Europe)
      const ddmmyyyyMatch = trimmed.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
      if (ddmmyyyyMatch) {
        const [, day, month, year] = ddmmyyyyMatch;
        date = new Date(parseInt(year), parseInt(month) - 1, parseInt(day));
        return !isNaN(date.getTime()) && 
               date.getDate() == parseInt(day) && 
               date.getMonth() == parseInt(month) - 1 && 
               date.getFullYear() == parseInt(year);
      }
      
      // Try DD-MM-YYYY format
      const ddmmyyyyDashMatch = trimmed.match(/^(\d{1,2})-(\d{1,2})-(\d{4})$/);
      if (ddmmyyyyDashMatch) {
        const [, day, month, year] = ddmmyyyyDashMatch;
        date = new Date(parseInt(year), parseInt(month) - 1, parseInt(day));
        return !isNaN(date.getTime()) && 
               date.getDate() == parseInt(day) && 
               date.getMonth() == parseInt(month) - 1 && 
               date.getFullYear() == parseInt(year);
      }
      
      // Try YYYY-MM-DD format (ISO)
      const yyyymmddMatch = trimmed.match(/^(\d{4})-(\d{1,2})-(\d{1,2})$/);
      if (yyyymmddMatch) {
        const [, year, month, day] = yyyymmddMatch;
        date = new Date(parseInt(year), parseInt(month) - 1, parseInt(day));
        return !isNaN(date.getTime()) && 
               date.getDate() == parseInt(day) && 
               date.getMonth() == parseInt(month) - 1 && 
               date.getFullYear() == parseInt(year);
      }
      
      return false;
    }
  },
  {
    id: 'certificate_no',
    question: 'What is the certificate number?',
    placeholder: 'e.g., HCO-2025-001',
    type: 'text',
    validation: (value: string) => value.trim().length > 0
  },
  {
    id: 'standards',
    question: 'What standards and requirements should be mentioned?',
    placeholder: 'e.g., MS 1500:2019, JAKIM Guidelines',
    type: 'text',
    validation: (value: string) => value.trim().length > 0
  },
  {
    id: 'company_name',
    question: 'What is the company name?',
    placeholder: 'Enter full legal company name',
    type: 'text',
    validation: (value: string) => value.trim().length > 0
  },
  {
    id: 'company_address',
    question: 'What is the company address?',
    placeholder: 'Enter complete company address',
    type: 'text',
    validation: (value: string) => value.trim().length > 0
  },
  {
    id: 'pu_or_au',
    question: 'Enter PU (Production Unit) or AU (Administrative Unit) - one is required:',
    placeholder: 'Enter PU or AU details',
    type: 'text',
    validation: (value: string) => value.trim().length > 0
  },
  {
    id: 'sow',
    question: 'What is the SOW (Scope of Work)?',
    placeholder: 'Enter scope of work details',
    type: 'text',
    validation: (value: string) => value.trim().length > 0
  },
  {
    id: 'validity_period',
    question: 'What is the validity period for this certificate?',
    type: 'select',
    options: [
      '1|1 Year',
      '2|2 Years', 
      '3|3 Years'
    ],
    validation: (value: string) => ['1', '2', '3'].includes(value.trim())
  },
  {
    id: 'company_reg_no',
    question: 'What is the company registration number?',
    placeholder: 'Enter company registration number',
    type: 'text',
    validation: (value: string) => value.trim().length > 0
  },
  {
    id: 'csv_files',
    question: 'Please upload CSV or Excel files with product data (or type "skip" to continue without files):',
    type: 'file',
    validation: (_value: string) => true // File is optional
  },
  {
    id: 'company_logo',
    question: 'Please upload your company logo (or type "skip" to continue without logo):',
    type: 'file',
    validation: (_value: string) => true // Logo is optional
  }
];

export class CertificateGenerationService {
  private currentStep: number = 0;
  private certificateData: Partial<CertificateData> = {};
  private isActive: boolean = false;

  startGeneration(): string {
    this.currentStep = 0;
    this.certificateData = {};
    this.isActive = true;
    
    return `🎯 **Certificate Generation Started!**

I'll help you create a new certificate by asking you some questions step by step.

**Step 1/${certificateSteps.length}:** ${certificateSteps[0].question}`;
  }

  processAnswer(answer: string, files?: File[]): { 
    response: string; 
    isComplete: boolean; 
    progress: number;
    currentData: Partial<CertificateData>;
  } {
    if (!this.isActive) {
      return {
        response: "Certificate generation is not active. Please say 'generate certificate' to start.",
        isComplete: false,
        progress: 0,
        currentData: {}
      };
    }

    const currentStepData = certificateSteps[this.currentStep];
    
    // Handle file input
    if (currentStepData.type === 'file') {
      if (files && files.length > 0) {
        // Files were uploaded
        if (currentStepData.id === 'csv_files') {
          this.certificateData.csv_files = files;
        } else if (currentStepData.id === 'company_logo') {
          // For company logo, only take the first file and validate it's an image
          const logoFile = files[0];
          if (logoFile.type.startsWith('image/')) {
            this.certificateData.company_logo = logoFile;
          } else {
            return {
              response: `❌ Invalid file type. Please upload an image file (JPG, PNG, GIF, etc.) for the company logo.\n\n${currentStepData.question}`,
              isComplete: false,
              progress: Math.round(this.currentStep / certificateSteps.length * 100),
              currentData: this.certificateData
            };
          }
        }
      } else {
        // No files uploaded, check if user wants to skip with text
        const answerLower = answer.toLowerCase().trim();
        if (answerLower === 'skip' || answerLower === 'no' || answerLower === 'none' || answerLower === 'no files' || answerLower === '') {
          // User wants to skip file upload
          if (currentStepData.id === 'csv_files') {
            this.certificateData.csv_files = undefined;
          } else if (currentStepData.id === 'company_logo') {
            this.certificateData.company_logo = undefined;
          }
        } else {
          // User provided text but no files for a file step
          const fileTypeHint = currentStepData.id === 'csv_files' 
            ? 'CSV/Excel files' 
            : currentStepData.id === 'company_logo' 
              ? 'image files (JPG, PNG, GIF, etc.)'
              : 'files';
          
          return {
            response: `📁 This step requires file upload or you can type "skip" to continue without files.\n\n${currentStepData.question}\n\nYou can either:\n• Upload ${fileTypeHint}\n• Type "skip" to continue without files`,
            isComplete: false,
            progress: Math.round(this.currentStep / certificateSteps.length * 100),
            currentData: this.certificateData
          };
        }
      }
    } else {
      // Handle non-file inputs
      // Validate answer
      if (currentStepData.validation && !currentStepData.validation(answer.trim())) {
        return {
          response: `❌ Invalid input. ${currentStepData.question}`,
          isComplete: false,
          progress: Math.round(this.currentStep / certificateSteps.length * 100),
          currentData: this.certificateData
        };
      }

      // Store the answer
      const key = currentStepData.id;
      
      // Handle special cases
      if (key === 'pu_or_au') {
        // Detect if it's PU or AU based on content
        const answerLower = answer.toLowerCase().trim();
        if (answerLower.includes('pu') || answerLower.includes('production')) {
          this.certificateData.pu = answer.trim();
        } else if (answerLower.includes('au') || answerLower.includes('administrative')) {
          this.certificateData.au = answer.trim();
        } else {
          // Default to PU if unclear
          this.certificateData.pu = answer.trim();
        }
      } else if (key === 'sow') {
        this.certificateData.sow = answer.trim();
      } else if (key === 'issue_date') {
        // Convert date to YYYY-MM-DD format for backend
        const convertedDate = this.convertDateToISO(answer.trim());
        this.certificateData.issue_date = convertedDate;
      } else if (currentStepData.type === 'select' && currentStepData.options) {
        // For select options, find matching option
        const answerLower = answer.toLowerCase().trim();
        const selectedOption = currentStepData.options.find(opt => {
          const [value, label] = opt.split('|');
          const valueLower = value.toLowerCase();
          const labelLower = label.toLowerCase();
          
          return valueLower === answerLower || 
                 labelLower === answerLower ||
                 labelLower.includes(answerLower) ||
                 (answerLower === '1' && opt === currentStepData.options?.[0]) ||
                 (answerLower === '2' && opt === currentStepData.options?.[1]) ||
                 (answerLower === '3' && opt === currentStepData.options?.[2]);
        });
        
        if (selectedOption) {
          (this.certificateData as any)[key] = selectedOption.split('|')[0];
        } else {
          // Default fallback
          (this.certificateData as any)[key] = currentStepData.options?.length ? currentStepData.options[0].split('|')[0] : answer.trim();
        }
      } else {
        (this.certificateData as any)[key] = answer.trim();
      }
    }

    this.currentStep++;

    // Check if we're done
    if (this.currentStep >= certificateSteps.length) {
      this.isActive = false;
      return {
        response: this.generateSummary(),
        isComplete: true,
        progress: 100,
        currentData: this.certificateData
      };
    }

    // Move to next step
    const nextStep = certificateSteps[this.currentStep];
    let response = `✅ **${this.getFieldDisplayName(currentStepData.id)}:** ${this.getDisplayValue(currentStepData.id)}

**Step ${this.currentStep + 1}/${certificateSteps.length}:** ${nextStep.question}`;

    // Add options for select type
    if (nextStep.type === 'select' && nextStep.options) {
      response += '\n\nOptions:\n';
      nextStep.options.forEach((option, index) => {
        const [_value, label] = option.split('|');
        response += `${index + 1}. ${label}\n`;
      });
      response += '\nYou can type the number 1, 2 or 3.';
    }
    
    // Add instructions for file type
    if (nextStep.type === 'file') {
      if (nextStep.id === 'csv_files') {
        response += '\n\n📁 **Instructions:**\n• Upload CSV/Excel files using the attachment button\n• Or type "skip" to continue without files';
      } else if (nextStep.id === 'company_logo') {
        response += '\n\n🖼️ **Instructions:**\n• Upload an image file (JPG, PNG, GIF, etc.) using the attachment button\n• Or type "skip" to continue without a company logo';
      }
    }

    return {
      response,
      isComplete: false,
      progress: Math.round(this.currentStep / certificateSteps.length * 100),
      currentData: this.certificateData
    };
  }

  private getFieldDisplayName(fieldId: string): string {
    const names: { [key: string]: string } = {
      issue_date: 'Issue Date',
      certificate_no: 'Certificate Number',
      standards: 'Standards',
      company_name: 'Company Name',
      company_address: 'Company Address',
      pu_or_au: 'PU/AU Details',
      sow: 'SOW',
      validity_period: 'Validity Period',
      company_reg_no: 'Registration Number',
      csv_files: 'Data Files',
      company_logo: 'Company Logo'
    };
    return names[fieldId] || fieldId;
  }

  private getDisplayValue(fieldId: string): string {
    const value = (this.certificateData as any)[fieldId];
    if (fieldId === 'validity_period') {
      return value ? `${value} Year${value !== '1' ? 's' : ''}` : '';
    }
    if (fieldId === 'pu_or_au') {
      return this.certificateData.pu || this.certificateData.au || '';
    }
    if (fieldId === 'csv_files' && value && Array.isArray(value)) {
      return value.map(file => file.name).join(', ');
    }
    if (fieldId === 'company_logo' && value) {
      return value.name;
    }
    return value || '';
  }

  private generateSummary(): string {
    let summary = `✅ **Certificate Information Complete!**

📅 **Issue Date:** ${this.certificateData.issue_date}
📋 **Certificate Number:** ${this.certificateData.certificate_no}
📏 **Standards:** ${this.certificateData.standards}
🏢 **Company Name:** ${this.certificateData.company_name}
🏠 **Company Address:** ${this.certificateData.company_address}
🏭 **${this.certificateData.pu ? 'PU' : 'AU'}:** ${this.certificateData.pu || this.certificateData.au}
🔧 **SOW:** ${this.certificateData.sow}
⏰ **Validity Period:** ${this.getDisplayValue('validity_period')}
📄 **Registration Number:** ${this.certificateData.company_reg_no}`;

    
    if (this.certificateData.csv_files && this.certificateData.csv_files.length > 0) {
      const fileNames = this.certificateData.csv_files.map(file => file.name).join(', ');
      summary += `\n📁 **Data Files:** ${fileNames}`;
    }

    if (this.certificateData.company_logo) {
      summary += `\n🖼️ **Company Logo:** ${this.certificateData.company_logo.name}`;
    }

    summary += '\n\nType **"generate"** to create the certificate!';
    
    return summary;
  }

  getCertificateData(): CertificateData | null {
    if (!this.isDataComplete()) {
      return null;
    }
    return this.certificateData as CertificateData;
  }

  private isDataComplete(): boolean {
    const requiredFields = ['issue_date', 'certificate_no', 'standards', 'company_name', 'company_address', 'sow', 'validity_period', 'company_reg_no'];
    const hasRequiredFields = requiredFields.every(field => (this.certificateData as any)[field]);
    
    // Also check that either PU or AU is provided
    const hasPuOrAu = Boolean(this.certificateData.pu || this.certificateData.au);
    
    return hasRequiredFields && hasPuOrAu;
  }

  reset(): void {
    this.currentStep = 0;
    this.certificateData = {};
    this.isActive = false;
  }

  getProgress(): number {
    return Math.round(this.currentStep / certificateSteps.length * 100);
  }

  isGenerationActive(): boolean {
    return this.isActive;
  }

  private convertDateToISO(dateString: string): string {
    const trimmed = dateString.trim();
    
    // Try DD/MM/YYYY format (common in UK/Europe)
    const ddmmyyyyMatch = trimmed.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
    if (ddmmyyyyMatch) {
      const [, day, month, year] = ddmmyyyyMatch;
      // Pad with zeros to ensure proper format
      const paddedDay = day.padStart(2, '0');
      const paddedMonth = month.padStart(2, '0');
      return `${year}-${paddedMonth}-${paddedDay}`;
    }
    
    // Try DD-MM-YYYY format
    const ddmmyyyyDashMatch = trimmed.match(/^(\d{1,2})-(\d{1,2})-(\d{4})$/);
    if (ddmmyyyyDashMatch) {
      const [, day, month, year] = ddmmyyyyDashMatch;
      // Pad with zeros to ensure proper format
      const paddedDay = day.padStart(2, '0');
      const paddedMonth = month.padStart(2, '0');
      return `${year}-${paddedMonth}-${paddedDay}`;
    }
    
    // Try YYYY-MM-DD format (already ISO)
    const yyyymmddMatch = trimmed.match(/^(\d{4})-(\d{1,2})-(\d{1,2})$/);
    if (yyyymmddMatch) {
      const [, year, month, day] = yyyymmddMatch;
      // Ensure proper padding
      const paddedDay = day.padStart(2, '0');
      const paddedMonth = month.padStart(2, '0');
      return `${year}-${paddedMonth}-${paddedDay}`;
    }
    
    // Try direct parsing for other formats
    const date = new Date(trimmed);
    if (!isNaN(date.getTime())) {
      // Use local date components to avoid timezone issues
      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, '0');
      const day = String(date.getDate()).padStart(2, '0');
      return `${year}-${month}-${day}`;
    }
    
    // Fallback: return as-is
    return trimmed;
  }
}