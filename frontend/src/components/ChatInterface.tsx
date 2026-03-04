import React, { useState, useRef, useEffect } from "react";
import ChatMessage from "./ChatMessage";
import ChatInput from "./ChatInput";
import {
  CertificateGenerationService,
  type CertificateData,
} from "../services/certificateService";
import { apiService } from "../services/apiService";

interface Message {
  id: string;
  text: string;
  sender: "user" | "assistant";
  timestamp: Date;
  image?: File;
  imageUrl?: string;
}

// CertificateDownloadResponse interface moved to apiService.ts

interface ChatInterfaceProps {
  user: { email: string } | null;
}

const ChatInterface: React.FC<ChatInterfaceProps> = ({ user }) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const [certificateService] = useState(new CertificateGenerationService());
  const [certificateData, setCertificateData] = useState<
    Partial<CertificateData>
  >({});
  const [generationProgress, setGenerationProgress] = useState(0);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Using the API service for all backend communication

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const handleCertificateGeneration = async (
    certificateData: CertificateData
  ): Promise<string> => {
    try {
      console.log("Sending certificate data to backend:", certificateData);

      // Use the API service to generate the certificate
      const result = await apiService.processAndGenerateCertificate(
        certificateData,
        certificateData.csv_files
      );

      if (result.processed) {
        const downloadLine = result.download_url
          ? `\n\n⬇️ **Download Link:** ${result.download_url}`
          : "";

        return `✅ **Certificate Generated Successfully!**\n\n🎉 **Certificate ID:** ${result.certificate_id}\n📋 **Certificate Number:** ${certificateData.certificate_no}\n🏢 **Company:** ${certificateData.company_name}\n\n${result.message}${downloadLine}\n\n📧 **Next Steps:** You will receive your certificate files via email, or contact HCO at info@hcoltd.co.uk for assistance.`;
      } else {
        return `❌ **Certificate Generation Failed**\n\n${result.message}\n\n📞 **Support:** Please contact HCO at info@hcoltd.co.uk or +44 (0) 333 577 0902 for assistance.`;
      }
    } catch (error) {
      console.error("Certificate generation error:", error);
      return `❌ **Certificate Generation Error**\n\nFailed to generate certificate: ${
        error instanceof Error ? error.message : "Unknown error"
      }\n\n📞 **Support:** Please contact HCO at info@hcoltd.co.uk or +44 (0) 333 577 0902 for assistance.`;
    }
  };

  const handleImageUpload = async (image: File): Promise<string> => {
    try {
      console.log("Uploading file for verification:", image.name, image.type);

      // Use the API service for image upload
      const result = await apiService.uploadImageFile(image);

      if (result.processed) {
        return result.message;
      } else {
        return `Error processing image: ${result.message}`;
      }
    } catch (error) {
      console.error("Error uploading image:", error);
      return `Failed to upload and analyze image: ${
        error instanceof Error ? error.message : "Unknown error"
      }`;
    }
  };

  // Unused function - replaced by direct API calls
  // const handleCertificateDownload = async (
  //   certificateNo: string
  // ): Promise<string> => {
  //   // Function content removed to avoid unused variable warning
  // };

  // Helper function to check if a query requires authentication
  const requiresAuthentication = (text: string): boolean => {
    const textLower = text.toLowerCase().trim();

    // Certificate generation keywords
    const generationKeywords = [
      "generate certificate", "create certificate", "want certificate",
      "need certificate", "generate", "create"
    ];

    // Download keywords with certificate patterns
    const downloadKeywords = ["download"];
    const hasCertificatePattern = /\b[A-Z]{2,4}[-/]\d{2,4}[-/]\d{2,4}\b/.test(text) || // HCO-2024-001
                                 /\b[A-Z]{2,4}\/[A-Z]{2,4}\/\d{6}\b/.test(text) || // HCO/RAO/091024
                                 /\b[A-Z]{2,4}(?:\/[A-Z0-9]{2,10}){2,}\b/.test(text) || // HCO/TEST/SS/DD/23
                                 /\b[A-Z]{2,4}\d{4,8}\b/.test(text); // HCO20240001

    // Check for generation requests
    const wantsGeneration = generationKeywords.some(keyword =>
      textLower.includes(keyword) ||
      (textLower.includes("generate") && textLower.includes("certificate")) ||
      (textLower.includes("create") && textLower.includes("certificate"))
    );

    // Check for download requests - NOTE: Verification does NOT require authentication
    const wantsDownload = downloadKeywords.some(keyword => textLower.includes(keyword)) &&
                         (textLower.includes("certificate") || hasCertificatePattern);

    return wantsGeneration || wantsDownload;
  };

  const _formatProductVerificationResponse = (result: {
    message?: string;
    processed?: boolean;
    found?: boolean;
    certificate_found?: boolean;
    certificate_no?: string | null;
    verified_product_names?: string[];
    verified_product_codes?: string[];
    missing_product_names?: string[];
    missing_product_codes?: string[];
  }): string => {
    const certFound = Boolean(result.found ?? result.certificate_found);
    const allVerified = Boolean(result.processed);
    const verifiedNames = result.verified_product_names || [];
    const verifiedCodes = result.verified_product_codes || [];
    const missingNames = result.missing_product_names || [];
    const missingCodes = result.missing_product_codes || [];
    const hasStructuredData = verifiedNames.length + verifiedCodes.length + missingNames.length + missingCodes.length > 0;

    if (!certFound) {
      const certNo = result.certificate_no || "the given certificate";
      return `❌ **Certificate Not Found**\n\nCertificate **${certNo}** was not found in our records.`;
    }

    if (!hasStructuredData) {
      const msg = result.message || "Product verification completed.";
      const hasV = msg.includes("✅");
      const hasM = msg.includes("❌");
      let title = "❌ **Products Not Verified**";
      if (allVerified) title = "✅ **All Products Verified**";
      else if (hasV && hasM) title = "⚠️ **Partial Verification**";
      return `${title}\n\n${msg}`;
    }

    const totalVerified = verifiedNames.length + verifiedCodes.length;
    const totalMissing = missingNames.length + missingCodes.length;
    const total = totalVerified + totalMissing;
    const certNo = result.certificate_no || "";

    let title: string;
    if (allVerified) {
      title = "✅ **All Products Verified**";
    } else if (totalVerified > 0 && totalMissing > 0) {
      title = "⚠️ **Partial Verification**";
    } else {
      title = "❌ **Products Not Verified**";
    }

    const parts: string[] = [title, ""];
    parts.push(`**Certificate:** ${certNo}`);
    parts.push(`**Total Checked:** ${total} product(s)\n`);

    if (totalVerified > 0) {
      parts.push(`✅ **Verified (${totalVerified}):**`);
      for (const n of verifiedNames) parts.push(`  - ${n} *(name)*`);
      for (const c of verifiedCodes) parts.push(`  - ${c} *(code)*`);
      parts.push("");
    }

    if (totalMissing > 0) {
      parts.push(`❌ **Not Found (${totalMissing}):**`);
      for (const n of missingNames) parts.push(`  - ${n} *(name)*`);
      for (const c of missingCodes) parts.push(`  - ${c} *(code)*`);
      parts.push("");
    }

    return parts.join("\n");
  };

  const handleTextMessage = async (text: string, requireAuth: boolean = false): Promise<string> => {
    try {
      const textLower = text.toLowerCase().trim();
      
      // If authentication is required but user is not logged in
      if (requireAuth && !user) {
        if (requiresAuthentication(text)) {
          return `🔒 **Authentication Required**\n\nTo access this feature, please sign in first.\n\n**Please use the login button in the top navigation to sign in.**`;
        }
      }

      // Check for direct download requests with comprehensive certificate number patterns
      // Pattern 1: HCO-2024-001
      // Pattern 2: HCO/RAO/1110235432
      // Pattern 3: HCO20240001
      const certPatterns = [
        /\b([A-Z]{2,4}[-\/][A-Z]{2,4}[-\/]\d{6,})\b/i,  // HCO/RAO/1110235432 or HCO-RAO-1110235432
        /\b([A-Z]{2,4}(?:\/[A-Z0-9]{2,10}){2,})\b/i,       // HCO/TEST/SS/DD/23
        /\b([A-Z]{2,4}[-]\d{4}[-]\d{3,})\b/i,            // HCO-2024-001
        /\b([A-Z]{2,4}\d{6,})\b/i                        // HCO20240001
      ];

      let certMatch = null;
      for (const pattern of certPatterns) {
        const match = text.match(pattern);
        if (match) {
          certMatch = match[1];
          break;
        }
      }

      if (certMatch && textLower.includes("download")) {
        console.log(`Download request detected for certificate: ${certMatch}`);
        if (!user) {
          return `🔒 **Sign In Required**\n\nTo access this feature, please sign in first.\n\n**How to sign in:**\n1. Click the login button in the top navigation\n2. Sign in with your Microsoft account\n3. Return here and try again`;
        }
        return await apiService.downloadAndTriggerFile(certMatch, "pdf");
      }

      // Check for specific certificate operations (verify, download, check with cert number)
      const hasVerifyKeywords = textLower.includes("verify") || textLower.includes("validate") || textLower.includes("check certificate");
      const hasProductVerifyKeywords = (textLower.includes("product") || textLower.includes("products")) &&
                                       (textLower.includes("verify") || textLower.includes("validate") || textLower.includes("check") ||
                                        textLower.includes("available") || textLower.includes("listed") || textLower.includes("present") ||
                                        textLower.includes("find") || textLower.includes("exist") || textLower.includes("confirm") ||
                                        textLower.includes("match"));
      const hasDownloadKeywords = textLower.includes("download") && textLower.includes("certificate");
      const hasCertificatePattern = /\b[A-Z]{2,4}[-/]\d{2,4}[-/]\d{2,4}\b/.test(text) || // HCO-2024-001
                                   /\b[A-Z]{2,4}\/[A-Z]{2,4}\/\d{6}\b/.test(text) || // HCO/RAO/091024
                                   /\b[A-Z]{2,4}(?:\/[A-Z0-9]{2,10}){2,}\b/.test(text) || // HCO/TEST/SS/DD/23
                                   /\b[A-Z]{2,4}\d{4,8}\b/.test(text); // HCO20240001

      // Use certificate endpoint for certificate operations with cert numbers, or product verification
      if ((hasVerifyKeywords || hasDownloadKeywords || hasProductVerifyKeywords) && hasCertificatePattern) {
        // Check if authentication is required ONLY for download operations, NOT for verification
        if (!user && hasDownloadKeywords) {
          return `🔒 **Sign In Required**\n\nTo access this feature, please sign in first.\n\n**How to sign in:**\n1. Click the login button in the top navigation\n2. Sign in with your Microsoft account\n3. Return here and try again\n\n**Note:** Certificate verification is available without sign-in. Try "verify certificate [number]" instead.`;
        }

        console.log("Using certificate/query endpoint for:", text);
        const result = await apiService.searchCertificate(text, user?.email);

        // Handle download responses
        if (result.query_type === "download" && result.certificate_no) {
          console.log(`Triggering automatic download for certificate: ${result.certificate_no}`);
          try {
            const downloadMessage = await apiService.downloadAndTriggerFile(
              result.certificate_no,
              "pdf"
            );
            return downloadMessage;
          } catch (downloadError) {
            console.error("Download failed:", downloadError);
            return result.message || `❌ Download failed: ${downloadError}`;
          }
        }

        if (result.query_type === "product_verification") {
          return _formatProductVerificationResponse(result);
        }

        return result.message || "How can I help you today?";
      } else {
        console.log("Using chat endpoint for:", text);
        const result = await apiService.chatWithAssistant(text);

        if (result.query_type === "product_verification") {
          return _formatProductVerificationResponse(result);
        }

        return result.message || "How can I help you today?";
      }
    } catch (error) {
      console.error("Error:", error);
      return `❌ Error: ${
        error instanceof Error ? error.message : "Request failed"
      }`;
    }
  };

  const handleCertificateFlow = (text: string, files?: File[]): string => {
    const textLower = text.toLowerCase().trim();

    // Check if user wants to start certificate generation (more flexible patterns)
    const wantsToGenerateCertificate =
      (!certificateService.isGenerationActive() &&
        textLower.includes("generate") &&
        textLower.includes("certificate")) ||
      (textLower.includes("create") && textLower.includes("certificate")) ||
      (textLower.includes("want") && textLower.includes("certificate")) ||
      (textLower.includes("need") && textLower.includes("certificate"));

    if (wantsToGenerateCertificate) {
      // Check authentication first
      if (!user) {
        return "🔒 Please login to the dashboard to generate certificates.";
      }

      const response = certificateService.startGeneration();
      setCertificateData({});
      setGenerationProgress(0);
      return response;
    }

    // If generation is active, process the answer
    if (certificateService.isGenerationActive()) {
      const result = certificateService.processAnswer(text, files);
      setCertificateData(result.currentData);
      setGenerationProgress(result.progress);

      if (result.isComplete) {
        return result.response;
      }

      return result.response;
    }

    // Check if user wants to generate after completion (more flexible patterns)
    const finalGenerateCommand =
      textLower === "generate" ||
      (textLower.includes("generate") &&
        (textLower.includes("yes") || textLower.includes("please"))) ||
      (textLower.includes("yes") && textLower.includes("generate")) ||
      textLower === "yes generate" ||
      textLower === "please generate" ||
      (textLower.startsWith("yes") && textLower.includes("generate"));

    if (finalGenerateCommand) {
      const completeData = certificateService.getCertificateData();
      console.log(
        "Certificate generation requested. Complete data:",
        completeData
      );

      if (completeData) {
        // Generate certificate asynchronously
        setTimeout(async () => {
          try {
            console.log("Sending certificate data to backend:", completeData);
            const result = await handleCertificateGeneration(completeData);

            // Reset state after generation
            setCertificateData({});
            setGenerationProgress(0);
            certificateService.reset();

            const generationMessage: Message = {
              id: (Date.now() + 2).toString(),
              text: result,
              sender: "assistant",
              timestamp: new Date(),
            };
            setMessages((prev) => [...prev, generationMessage]);
          } catch (error) {
            console.error("Certificate generation error:", error);
            const errorMessage: Message = {
              id: (Date.now() + 2).toString(),
              text: "❌ Error generating certificate. Please try again.",
              sender: "assistant",
              timestamp: new Date(),
            };
            setMessages((prev) => [...prev, errorMessage]);
          }
        }, 100);

        return "🚀 Generating your certificate now...";
      } else {
        return "❌ Certificate data is not complete. Please complete all required fields first.";
      }
    }

    return "I'm here to help! Would you like to generate a certificate? Just say **'generate certificate'** to get started.";
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    // Welcome message
    if (messages.length === 0) {
      const welcomeMessage: Message = {
        id: "1",
        text: `Hi! I'm **HCO Certificate Assistant**.

${
  user
    ? `Welcome back, ${user.email}! 

**🎉 All Services Available:**

• **Verify certificates:** "verify certificate ABC-123"  
• **Upload images/PDFs for validation**
• **Ask general questions about certification**
`
    : `Welcome! 

**🎉 All Services Available:**

• **Verify certificates:** "verify certificate ABC-123"  
• **Upload images/PDFs for validation**
• **Ask general questions about certification**
`
}

**🆘 Support:** info@hcoltd.co.uk | +44 (0) 333 577 0902

**💡 Try asking:** "What is halal certification?" or "How do I get HCO certified?"`,
        sender: "assistant",
        timestamp: new Date(),
      };
      setMessages([welcomeMessage]);
    }
  }, [user, messages.length]);

  const handleSendMessage = async (text: string, files?: File[]) => {
    if (!text.trim() && (!files || files.length === 0)) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      text: text.trim(),
      sender: "user",
      timestamp: new Date(),
      image: files && files.length > 0 ? files[0] : undefined,
      imageUrl:
        files && files.length > 0 ? URL.createObjectURL(files[0]) : undefined,
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsTyping(true);

    try {
      let response: string;

      if (files && files.length > 0) {
        // Check if certificate generation is active first - prioritize certificate flow
        if (user && certificateService.isGenerationActive()) {
          // Handle file upload during certificate generation (CSV)
          response = handleCertificateFlow(text, files);
        } else {
          // Check file types
          const hasDataFiles = files.some(
            (file) =>
              file.type.includes("csv") ||
              file.type.includes("excel") ||
              file.type.includes("sheet")
          );
          const hasImageOrPdf = files.some(
            (file) =>
              file.type.startsWith("image/") || file.type === "application/pdf"
          );

          if (hasDataFiles) {
            // Handle CSV/Excel files for certificate generation
            if (user) {
              response = handleCertificateFlow(text, files);
            } else {
              response =
                "🔒 **Sign In Required**\n\nTo upload CSV/Excel files, please sign in first.\n\n**How to sign in:**\n1. Click the login button in the top navigation\n2. Sign in with your Microsoft account\n3. Return here and upload your files again";
            }
          } else if (hasImageOrPdf && files.length === 1) {
            // Handle single image/PDF upload for validation - allow without authentication
            response = await handleImageUpload(files[0]);
          } else {
            response =
              "❌ Unsupported file type or combination. Please upload:\n• Images (JPG, PNG, GIF) or PDFs for validation";
          }
        }
      } else if (user) {
        // For authenticated users, check if certificate generation is active first
        if (certificateService.isGenerationActive()) {
          // Handle certificate generation flow - collect data step by step
          response = handleCertificateFlow(text, undefined);
        } else {
          // Check if it's a new certificate generation request or final generation command
          const textLower = text.toLowerCase().trim();

          // Check for certificate generation or final generate command
          const wantsToGenerateCertificate =
            (textLower.includes("generate") &&
              textLower.includes("certificate")) ||
            (textLower.includes("create") &&
              textLower.includes("certificate")) ||
            (textLower.includes("want") && textLower.includes("certificate")) ||
            (textLower.includes("need") && textLower.includes("certificate"));

          const finalGenerateCommand =
            (textLower.includes("generate") &&
              (textLower.includes("yes") || textLower.includes("please"))) ||
            textLower === "generate" ||
            (textLower.includes("yes") && textLower.includes("generate"));

          if (
            wantsToGenerateCertificate ||
            (finalGenerateCommand && certificateService.getCertificateData())
          ) {
            // Handle certificate generation for authenticated users
            response = handleCertificateFlow(text, undefined);
          } else {
            // Send all other queries to backend for processing (download, verification, inquiry)
            response = await handleTextMessage(text);
          }
        }
      } else {
        // Handle queries for unauthenticated users
        // Check if user is trying to access protected features
        if (requiresAuthentication(text)) {
          // Show authentication required message for protected features
          response = `🔒 **Sign In Required**\n\nTo access this feature, please sign in first.\n\n**Your request:** ${text}\n\n**Protected features requiring sign-in:**\n• Certificate downloads\n• Certificate generation\n\n**Available without sign-in:**\n• Certificate verification with certificate numbers\n• General questions about certification\n• Image/PDF validation\n• Information about HCO services\n\n**How to sign in:**\n1. Click the login button in the top navigation\n2. Sign in with your Microsoft account\n3. Return here and try your request again`;
        } else {
          // Handle general text queries - allow without authentication
          response = await handleTextMessage(text);
        }
      }

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: response,
        sender: "assistant",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: `Error: ${
          error instanceof Error
            ? error.message
            : "Failed to process your request"
        }`,
        sender: "assistant",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className="min-h-screen bg-white">
      <div className="w-full bg-[#358743] text-white py-6 lg:py-10 text-center">
        <h2 className="text-xl sm:text-2xl lg:text-3xl font-semibold font-quicksand">
          HCO Assistant
        </h2>
        <p className="mt-2 lg:mt-3 text-xs sm:text-sm lg:text-base max-w-3xl mx-auto opacity-90 px-4 font-quicksand">
          Ask questions, validate certificates, or generate new ones.
        </p>
      </div>

      <div className="py-4 lg:py-10 px-2 sm:px-4 lg:px-8">
        <div className="max-w-5xl mx-auto space-y-4 lg:space-y-6">
          <div className="min-h-[75vh] lg:min-h-[80vh] bg-white rounded-none shadow-sm border border-[#e0efe4] flex flex-col">
            {/* Chat Header with HCO Icon */}
            <div className="flex items-center justify-between px-3 sm:px-6 py-3 sm:py-4 border-b border-[#e0efe4] bg-[#f7fbf8]">
              <div className="flex items-center gap-2 sm:gap-3">
                <div className="h-8 w-8 sm:h-10 sm:w-10 flex items-center justify-center rounded-full bg-[#e0efe4]">
                  <img src="/HCO-Logo.avif" alt="HCO" className="h-6 sm:h-8 w-auto" />
                </div>
                <div>
                  <h2 className="text-sm sm:text-lg font-semibold text-[#4f8f5e] font-quicksand">
                    HCO Assistant
                  </h2>
                  <p className="text-xs text-[#7aa487] font-quicksand hidden sm:block">
                    Ask questions, validate certificates, or generate new ones.
                  </p>
                </div>
              </div>
              {certificateService.isGenerationActive() && (
                <span className="text-xs px-2 sm:px-3 py-1 rounded-full bg-[#e8f5ed] text-[#2f5f3b] font-medium">
                  <span className="hidden sm:inline">Certificate input mode</span>
                  <span className="sm:hidden">Cert Mode</span>
                </span>
              )}
            </div>

            {certificateService.isGenerationActive() && (
              <div className="px-3 sm:px-6 py-3 bg-[#f9fcfa] border-b border-[#e0efe4] flex items-center justify-between text-xs text-[#4f8f5e]">
                <div className="flex items-center gap-2">
                  <span className="text-base sm:text-lg">📋</span>
                  <span className="text-xs sm:text-sm">
                    <span className="hidden sm:inline">Certificate Generation • </span>
                    {generationProgress}% Complete
                  </span>
                </div>
                <button
                  className="text-xs text-[#c85c5c] underline"
                  onClick={() => {
                    certificateService.reset();
                    setCertificateData({});
                    setGenerationProgress(0);
                    const resetMessage: Message = {
                      id: Date.now().toString(),
                      text: "Certificate generation cancelled. Say 'generate certificate' to start again.",
                      sender: "assistant",
                      timestamp: new Date(),
                    };
                    setMessages((prev) => [...prev, resetMessage]);
                  }}
                >
                  Cancel
                </button>
              </div>
            )}

            {/* Certificate Data Progress Panel */}
            {certificateService.isGenerationActive() &&
              Object.keys(certificateData).length > 0 && (
                <div className="px-3 sm:px-6 py-3 sm:py-4 bg-[#f7fbf8] border-b border-[#e0efe4] text-xs text-[#4f8f5e]">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-medium">
                      📋 Certificate Data Collected
                    </span>
                    <span className="text-[#7aa487]">
                      {generationProgress}% complete
                    </span>
                  </div>
                  <div className="grid gap-1 text-[11px] text-[#4f8f5e]">
                    {certificateData.certificate_no && (
                      <div>
                        ✅ Certificate No: {certificateData.certificate_no}
                      </div>
                    )}
                    {certificateData.company_name && (
                      <div>✅ Company: {certificateData.company_name}</div>
                    )}
                    {certificateData.company_reg_no && (
                      <div>
                        ✅ Registration: {certificateData.company_reg_no}
                      </div>
                    )}
                    {certificateData.issue_date && (
                      <div>✅ Issue Date: {certificateData.issue_date}</div>
                    )}
                    {(certificateData as any).certificate_type && (
                      <div>
                        ✅ Type:{" "}
                        {(certificateData as any).certificate_type
                          .replace("_", " ")
                          .toUpperCase()}
                      </div>
                    )}
                    {certificateData.standards && (
                      <div>✅ Standards: {certificateData.standards}</div>
                    )}
                    {certificateData.csv_files &&
                      certificateData.csv_files.length > 0 && (
                        <div>
                          ✅ Data Files:{" "}
                          {certificateData.csv_files
                            .map((file) => file.name)
                            .join(", ")}
                        </div>
                      )}
                  </div>
                  {generationProgress === 100 && (
                    <div className="mt-2 text-[11px] text-[#2f5f3b]">
                      🎉 All data collected! Ready to generate certificate.
                    </div>
                  )}
                </div>
              )}

            <div className="flex-1 overflow-y-auto px-2 sm:px-4 py-3 sm:py-4 bg-[#f9fcfa]">
              {messages.map((message) => (
                <ChatMessage key={message.id} message={message} />
              ))}
              {isTyping && (
                <div className="flex items-start gap-2 sm:gap-3 text-xs text-[#7aa487] px-2 py-1">
                  <div className="h-6 w-6 sm:h-7 sm:w-7 rounded-full bg-[#e0efe4] flex items-center justify-center">
                    <img
                      src="/HCO-Logo.avif"
                      alt="HCO"
                      className="h-4 sm:h-5 w-auto"
                    />
                  </div>
                  <div className="mt-1">
                    <span className="hidden sm:inline">HCO Assistant is thinking...</span>
                    <span className="sm:hidden">Thinking...</span>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            <div className="border-t border-[#e0efe4] bg-white px-2 sm:px-4 py-2 sm:py-3">
              <ChatInput onSendMessage={handleSendMessage} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatInterface;
