import React, { useState, useRef } from "react";
import ReactMarkdown from "react-markdown";
import { getApiUrl } from "../config/env";

interface User {
  email: string;
}

interface UploadCertificateProps {
  user?: User | null;
}

const UploadCertificate: React.FC<UploadCertificateProps> = () => {
  const [result, setResult] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);
  const [dragOver, setDragOver] = useState<boolean>(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Certificate number validation state
  const [certificateNumber, setCertificateNumber] = useState<string>("");
  const [numberLoading, setNumberLoading] = useState<boolean>(false);
  const [numberResult, setNumberResult] = useState<string>("");

  // Product verification state
  const [productVerifyCertificateNo, setProductVerifyCertificateNo] = useState<string>("");
  const [productNames, setProductNames] = useState<string[]>([""]);
  const [productCodes, setProductCodes] = useState<string[]>([""]);
  const [productVerifyLoading, setProductVerifyLoading] = useState<boolean>(false);
  const [productVerifyResult, setProductVerifyResult] = useState<string>("");

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = () => {
    setDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFile(files[0]);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFile(e.target.files[0]);
    }
  };

  const handleFile = async (file: File) => {
    // Validate file type (images and PDFs)
    if (!file.type.startsWith("image/") && file.type !== "application/pdf") {
      showResult("Please select a valid image or PDF file.", false);
      return;
    }

    // Validate file size (10MB limit)
    const maxSize = 10 * 1024 * 1024; // 10MB
    if (file.size > maxSize) {
      showResult("File size must be less than 10MB.", false);
      return;
    }

    // Validate file is not empty
    if (file.size === 0) {
      showResult("Please select a non-empty file.", false);
      return;
    }

    console.log('Processing file:', {
      name: file.name,
      type: file.type,
      size: file.size
    });

    setLoading(true);
    setResult("");

    try {
      // Convert file to base64
      const base64Data = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => {
          try {
            const result = reader.result as string;
            if (!result || typeof result !== 'string') {
              reject(new Error('Failed to read file as base64'));
              return;
            }
            
            // Remove the data URL prefix (e.g., "data:image/jpeg;base64," or "data:application/pdf;base64,")
            const base64Parts = result.split(",");
            if (base64Parts.length < 2) {
              reject(new Error('Invalid base64 format'));
              return;
            }
            
            const base64 = base64Parts[1];
            if (!base64 || base64.trim().length === 0) {
              reject(new Error('Empty base64 data'));
              return;
            }
            
            console.log('Base64 conversion successful, length:', base64.length);
            resolve(base64);
          } catch (error) {
            console.error('Error processing file:', error);
            reject(error);
          }
        };
        reader.onerror = () => {
          reject(new Error('Failed to read file'));
        };
        reader.readAsDataURL(file);
      });

      // Prepare the request payload
      const requestPayload = {
        image_data: base64Data,
        filename: file.name,
        content_type: file.type,
      };
      
      console.log('Sending request with payload:', {
        filename: requestPayload.filename,
        content_type: requestPayload.content_type,
        image_data_length: requestPayload.image_data.length
      });

      // Call the agent endpoint
      const response = await fetch(`${getApiUrl()}/image/upload`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(requestPayload),
      });

      console.log("Response status:", response.status);
      console.log(
        "Response headers:",
        Object.fromEntries(response.headers.entries())
      );

      if (!response.ok) {
        // Try to get error details from response
        let errorMessage = `HTTP error! status: ${response.status}`;
        try {
          const errorData = await response.text();
          console.error("Error response body:", errorData);
          if (errorData) {
            errorMessage = errorData;
          }
        } catch (e) {
          console.error("Failed to read error response:", e);
        }
        throw new Error(errorMessage);
      }

      const data = await response.json();
      console.log("Response data:", data);

      // Show validation result
      if (data.processed && data.message && data.message.includes("Certificate Verified")) {
        showResult(data.message, true);
      } else {
        // Handle error messages from backend
        const errorMessage = data.message || data.error || "Certificate is INVALID";
        showResult(errorMessage, false);
      }
    } catch (error) {
      console.error("Error:", error);
      showResult("Error validating certificate. Please try again.", false);
    } finally {
      setLoading(false);
    }
  };

  const handleCertificateNumberValidation = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!certificateNumber.trim()) {
      showNumberResult("Please enter a certificate number.", false);
      return;
    }

    setNumberLoading(true);
    setNumberResult("");

    try {
      console.log(
        "Frontend: Starting certificate validation for:",
        certificateNumber.trim()
      );

      // Call the backend endpoint for certificate number validation (with CORS)
      const response = await fetch(`${getApiUrl()}/certificate/verify`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          certificate_no: certificateNumber.trim(),
        }),
      });

      console.log("Frontend: Received response status:", response.status);
      console.log(
        "Frontend: Response headers:",
        Object.fromEntries(response.headers.entries())
      );

      if (!response.ok) {
        console.error("Frontend: HTTP error, status:", response.status);
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      console.log("Frontend: Parsed response data:", data);

      // Show validation result - check both the agent format and Flask format
      if (data.is_valid === true) {
        showNumberResult(data.message || "Certificate is VALID", true);
      } else if (data.is_valid === false) {
        showNumberResult(data.message || "Certificate is INVALID", false);
      } else {
        // Fallback for any other response format
        showNumberResult("Certificate validation completed", false);
      }
    } catch (error) {
      console.error("Frontend: Error validating certificate number:", error);
      showNumberResult(
        "Error validating certificate number. Please try again.",
        false
      );
    } finally {
      setNumberLoading(false);
    }
  };

  const showResult = (message: string, isValid: boolean) => {
    setResult(`${message}|${isValid ? "valid" : "invalid"}`);
  };

  const showNumberResult = (message: string, isValid: boolean) => {
    setNumberResult(`${message}|${isValid ? "valid" : "invalid"}`);
  };

  const showProductVerifyResult = (message: string, isValid: boolean) => {
    setProductVerifyResult(`${message}|${isValid ? "valid" : "invalid"}`);
  };

  const handleProductVerification = async (e: React.FormEvent) => {
    e.preventDefault();
    const certNo = productVerifyCertificateNo.trim();
    if (!certNo) {
      showProductVerifyResult("Please enter a certificate number.", false);
      return;
    }

    setProductVerifyLoading(true);
    setProductVerifyResult("");

    try {
      const cleanedNames = productNames.map((p) => p.trim()).filter(Boolean);
      const cleanedCodes = productCodes.map((c) => c.trim()).filter(Boolean);

      const response = await fetch(`${getApiUrl()}/certificate/verify-products`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          certificate_no: certNo,
          product_names: cleanedNames,
          product_codes: cleanedCodes,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();

      const verifiedNames: string[] = data.verified_product_names || [];
      const verifiedCodes: string[] = data.verified_product_codes || [];
      const certFound = Boolean(data.certificate_found);
      const allVerified = Boolean(data.verified);

      let resultState: "valid" | "invalid" | "partial";
      if (!certFound) {
        resultState = "invalid";
      } else if (allVerified) {
        resultState = "valid";
      } else if (verifiedNames.length > 0 || verifiedCodes.length > 0) {
        resultState = "partial";
      } else {
        resultState = "invalid";
      }

      const msg = String(data.message || "Product verification completed.");
      setProductVerifyResult(`${msg}|${resultState}`);
    } catch (error) {
      console.error("Error verifying products:", error);
      showProductVerifyResult(
        "Error verifying products. Please try again.",
        false
      );
    } finally {
      setProductVerifyLoading(false);
    }
  };

  const handleUploadAreaClick = () => {
    fileInputRef.current?.click();
  };

  const [message, type = "unknown"] = (result || "").split("|");
  const [numberMessage, numberType = "unknown"] = (numberResult || "").split("|");
  const [productVerifyMessage, productVerifyType = "unknown"] = (productVerifyResult || "").split("|");

  return (
    <div className="min-h-screen bg-white w-full">
      <div className="w-full bg-[#358743] text-white py-6 lg:py-10 text-center max-w-full">
        <h1 className="text-xl sm:text-2xl lg:text-3xl font-semibold font-quicksand px-4">
          Certificate Validation
        </h1>
        <p className="mt-2 lg:mt-3 text-xs sm:text-sm lg:text-base max-w-2xl mx-auto opacity-90 px-4 font-quicksand">
          Upload your certificate image or PDF, or enter a certificate number to verify
          its authenticity.
        </p>
      </div>

      <div className="py-6 lg:py-10 px-4 sm:px-6 lg:px-8">
        <div className="max-w-5xl mx-auto space-y-6 lg:space-y-10">
          {/* Certificate Number Validation Section */}
          <div className="bg-[#f7fbf8] rounded-none shadow-sm border border-[#e0efe4] p-4 sm:p-6 lg:p-8">
            <div className="flex items-start gap-3 sm:gap-4 mb-4 sm:mb-6">
              <div className="h-8 w-8 sm:h-10 sm:w-10 flex items-center justify-center rounded-full bg-[#e0efe4] text-[#4f8f5e]">
                <svg className="w-4 h-4 sm:w-6 sm:h-6" viewBox="0 0 24 24" fill="none">
                  <path
                    d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </div>
              <div>
                <h2 className="text-base sm:text-lg font-semibold text-[#4f8f5e] font-quicksand">
                  Validate by Certificate Number
                </h2>
                <p className="mt-1 text-xs sm:text-sm text-[#7aa487] font-quicksand">
                  Enter a certificate number to verify its authenticity.
                </p>
              </div>
            </div>

            <form onSubmit={handleCertificateNumberValidation} className="mt-4 sm:mt-6">
              <div className="w-full">
                <div className="flex flex-col">
                  <label
                    htmlFor="certificateNumber"
                    className="mb-2 text-xs sm:text-sm font-medium text-[#4f8f5e] font-quicksand"
                  >
                    Certificate Number <span className="text-[#4f8f5e]">*</span>
                  </label>
                  <div className="flex items-center bg-[#e8f0eb] text-[#4f8f5e] px-3 sm:px-4 h-10 sm:h-12 w-full">
                    <svg
                      width="16"
                      height="16"
                      viewBox="0 0 24 24"
                      fill="none"
                      className="mr-2 sm:mr-3 text-[#7aa487]"
                    >
                      <path
                        d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6Z"
                        stroke="currentColor"
                        strokeWidth="2"
                      />
                      <path
                        d="m14 2 6 6h-6V2Z"
                        stroke="currentColor"
                        strokeWidth="2"
                      />
                    </svg>
                    <input
                      type="text"
                      id="certificateNumber"
                      name="certificate_number"
                      value={certificateNumber}
                      onChange={(e) => setCertificateNumber(e.target.value)}
                      placeholder="e.g., HCO-2024-001"
                      required
                      className="flex-1 bg-transparent outline-none text-xs sm:text-sm placeholder-[#9bb7a4] font-quicksand"
                    />
                  </div>
                </div>
              </div>

              <div className="mt-4 sm:mt-6">
                <button
                  type="submit"
                  className="w-full sm:w-auto inline-flex items-center justify-center px-6 sm:px-8 h-10 sm:h-11 bg-[#3a8f43] hover:text-amber-100 text-white text-xs sm:text-sm font-medium font-quicksand tracking-wide hover:bg-[#3f724d] transition-colors disabled:bg-[#b8cbbf] disabled:cursor-not-allowed rounded-lg"
                  disabled={numberLoading || !certificateNumber.trim()}
                >
                  {numberLoading ? (
                    <>
                      <div className="mr-2 h-4 w-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      <span>Validating...</span>
                    </>
                  ) : (
                    <>
                      <span>Validate Certificate</span>
                      <svg
                        width="18"
                        height="18"
                        viewBox="0 0 24 24"
                        fill="none"
                        className="ml-2"
                      >
                        <path
                          d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                          stroke="currentColor"
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      </svg>
                    </>
                  )}
                </button>
              </div>
            </form>

            {numberLoading && (
              <div className="mt-6 flex items-start gap-3 text-[#4f8f5e] text-sm">
                <div className="h-5 w-5 border-2 border-[#4f8f5e] border-t-transparent rounded-full animate-spin mt-0.5" />
                <div>
                  <p className="font-medium font-quicksand">Validating Certificate Number</p>
                  <p className="text-[#7aa487] font-quicksand">
                    Please wait while we verify the certificate number...
                  </p>
                </div>
              </div>
            )}

            {numberResult && (
              <div
                className={`mt-6 border-l-4 px-4 py-3 text-sm ${
                  numberType === "valid"
                    ? "border-[#4f8f5e] bg-[#e8f5ed] text-[#2f5f3b]"
                    : "border-[#c85c5c] bg-[#fceced] text-[#8a3131]"
                }`}
              >
                <p className="font-semibold mb-1">
                  {numberType === "valid"
                    ? "Certificate Valid"
                    : "Certificate Invalid"}
                </p>
                <div className="prose prose-sm max-w-none">
                  <ReactMarkdown>{numberMessage}</ReactMarkdown>
                </div>
              </div>
            )}
          </div>

          {/* Product Verification Section */}
          <div className="bg-[#f7fbf8] rounded-none shadow-sm border border-[#e0efe4] p-4 sm:p-6 lg:p-8">
            <div className="flex items-start gap-3 sm:gap-4 mb-4 sm:mb-6">
              <div className="h-8 w-8 sm:h-10 sm:w-10 flex items-center justify-center rounded-full bg-[#e0efe4] text-[#4f8f5e]">
                <svg className="w-4 h-4 sm:w-6 sm:h-6" viewBox="0 0 24 24" fill="none">
                  <path
                    d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </div>
              <div>
                <h2 className="text-base sm:text-lg font-semibold text-[#4f8f5e] font-quicksand">
                  Product Verification
                </h2>
                <p className="mt-1 text-xs sm:text-sm text-[#7aa487] font-quicksand">
                  Verify product name/code against a certificate number.
                </p>
              </div>
            </div>

            <form onSubmit={handleProductVerification} className="mt-4 sm:mt-6 space-y-6">
              <div className="w-full">
                <label
                  htmlFor="productVerifyCertificateNo"
                  className="mb-2 text-xs sm:text-sm font-medium text-[#4f8f5e] font-quicksand"
                >
                  Certificate Number <span className="text-[#4f8f5e]">*</span>
                </label>
                <div className="flex items-center bg-[#e8f0eb] text-[#4f8f5e] px-3 sm:px-4 h-10 sm:h-12 w-full">
                  <input
                    type="text"
                    id="productVerifyCertificateNo"
                    value={productVerifyCertificateNo}
                    onChange={(e) => setProductVerifyCertificateNo(e.target.value)}
                    placeholder="e.g., HCO-2024-001"
                    required
                    className="flex-1 bg-transparent outline-none text-xs sm:text-sm placeholder-[#9bb7a4] font-quicksand"
                  />
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-xs sm:text-sm font-medium text-[#4f8f5e] font-quicksand">
                    Product Name(s)
                  </label>
                  <button
                    type="button"
                    onClick={() => setProductNames((prev) => [...prev, ""])}
                    className="inline-flex items-center justify-center px-3 h-9 bg-[#3a8f43] text-white text-xs font-medium font-quicksand hover:bg-[#3f724d]"
                  >
                    +
                  </button>
                </div>
                <div className="space-y-3">
                  {productNames.map((value, idx) => (
                    <div key={`pn_${idx}`} className="flex items-center gap-2">
                      <input
                        type="text"
                        value={value}
                        onChange={(e) =>
                          setProductNames((prev) => {
                            const next = [...prev];
                            next[idx] = e.target.value;
                            return next;
                          })
                        }
                        placeholder="Product name"
                        className="flex-1 h-10 sm:h-12 bg-[#e8f0eb] text-[#4f8f5e] px-4 text-xs sm:text-sm placeholder-[#9bb7a4] outline-none font-quicksand"
                      />
                      {productNames.length > 1 && (
                        <button
                          type="button"
                          onClick={() => setProductNames((prev) => prev.filter((_, i) => i !== idx))}
                          className="px-3 h-10 sm:h-12 bg-[#c85c5c] text-white text-xs font-medium font-quicksand"
                        >
                          -
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-xs sm:text-sm font-medium text-[#4f8f5e] font-quicksand">
                    Product Code(s)
                  </label>
                  <button
                    type="button"
                    onClick={() => setProductCodes((prev) => [...prev, ""])}
                    className="inline-flex items-center justify-center px-3 h-9 bg-[#3a8f43] text-white text-xs font-medium font-quicksand hover:bg-[#3f724d]"
                  >
                    +
                  </button>
                </div>
                <div className="space-y-3">
                  {productCodes.map((value, idx) => (
                    <div key={`pc_${idx}`} className="flex items-center gap-2">
                      <input
                        type="text"
                        value={value}
                        onChange={(e) =>
                          setProductCodes((prev) => {
                            const next = [...prev];
                            next[idx] = e.target.value;
                            return next;
                          })
                        }
                        placeholder="Product code"
                        className="flex-1 h-10 sm:h-12 bg-[#e8f0eb] text-[#4f8f5e] px-4 text-xs sm:text-sm placeholder-[#9bb7a4] outline-none font-quicksand"
                      />
                      {productCodes.length > 1 && (
                        <button
                          type="button"
                          onClick={() => setProductCodes((prev) => prev.filter((_, i) => i !== idx))}
                          className="px-3 h-10 sm:h-12 bg-[#c85c5c] text-white text-xs font-medium font-quicksand"
                        >
                          -
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <button
                  type="submit"
                  className="w-full sm:w-auto inline-flex items-center justify-center px-6 sm:px-8 h-10 sm:h-11 bg-[#3a8f43] hover:text-amber-100 text-white text-xs sm:text-sm font-medium font-quicksand tracking-wide hover:bg-[#3f724d] transition-colors disabled:bg-[#b8cbbf] disabled:cursor-not-allowed rounded-lg"
                  disabled={productVerifyLoading || !productVerifyCertificateNo.trim()}
                >
                  {productVerifyLoading ? "Verifying..." : "Verify Product(s)"}
                </button>
              </div>
            </form>

            {productVerifyResult && (
              <div
                className={`mt-6 border-l-4 px-4 py-3 text-sm ${
                  productVerifyType === "valid"
                    ? "border-[#4f8f5e] bg-[#e8f5ed] text-[#2f5f3b]"
                    : productVerifyType === "partial"
                    ? "border-[#c4960c] bg-[#fef9e7] text-[#7a5d00]"
                    : "border-[#c85c5c] bg-[#fceced] text-[#8a3131]"
                }`}
              >
                <p className="font-semibold mb-1">
                  {productVerifyType === "valid"
                    ? "✅ All Products Verified"
                    : productVerifyType === "partial"
                    ? "⚠️ Partial Verification"
                    : "❌ Products Not Verified"}
                </p>
                <div className="prose prose-sm max-w-none">
                  <ReactMarkdown>{productVerifyMessage}</ReactMarkdown>
                </div>
              </div>
            )}
          </div>

          {/* Image Upload Section */}
          <div className="bg-[#f7fbf8] rounded-none shadow-sm border border-[#e0efe4] p-4 sm:p-6 lg:p-8">
            <div className="flex items-start gap-3 sm:gap-4 mb-4 sm:mb-6">
              <div className="h-8 w-8 sm:h-10 sm:w-10 flex items-center justify-center rounded-full bg-[#e0efe4] text-[#4f8f5e]">
                <svg className="w-4 h-4 sm:w-6 sm:h-6" viewBox="0 0 24 24" fill="none">
                  <path
                    d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6Z"
                    stroke="currentColor"
                    strokeWidth="2"
                  />
                  <path
                    d="m14 2 6 6h-6V2Z"
                    stroke="currentColor"
                    strokeWidth="2"
                  />
                </svg>
              </div>
              <div>
                <h2 className="text-base sm:text-lg font-semibold text-[#4f8f5e] font-quicksand">
                  Validate by Certificate Image or PDF
                </h2>
                <p className="mt-1 text-xs sm:text-sm text-[#7aa487] font-quicksand">
                  Upload an image or PDF of your certificate for visual validation.
                </p>
              </div>
            </div>

            <div
              className={`mt-4 cursor-pointer border border-dashed border-[#c7ddcf] rounded-none bg-[#f9fcfa] px-4 sm:px-6 py-6 sm:py-8 text-center transition-colors ${
                dragOver ? "bg-[#e8f5ed] border-[#4f8f5e]" : ""
              }`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={handleUploadAreaClick}
            >
              <div className="flex flex-col items-center gap-2 sm:gap-3">
                <div className="h-10 w-10 sm:h-12 sm:w-12 rounded-full bg-[#e0efe4] flex items-center justify-center text-[#4f8f5e]">
                  <svg className="w-5 h-5 sm:w-6 sm:h-6" viewBox="0 0 24 24" fill="none">
                    <path
                      d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </div>
                <div className="text-xs sm:text-sm font-medium text-[#4f8f5e] font-quicksand">
                  Upload Certificate Image or PDF
                </div>
                <div className="text-xs text-[#7aa487] px-2">
                  {dragOver
                    ? "Drop your file here!"
                    : "Drag and drop your certificate image or PDF here, or click to browse"}
                </div>
                <div className="text-[10px] sm:text-[11px] text-[#9bb7a4] mt-1">
                  Supports JPG, PNG, GIF, PDF up to 10MB
                </div>
                <button
                  className="mt-3 sm:mt-4 inline-flex items-center justify-center px-4 sm:px-6 h-9 sm:h-10 border border-[#4f8f5e] text-[#4f8f5e] text-xs font-medium font-quicksand tracking-wide hover:bg-[#4f8f5e] hover:text-white transition-colors max-w-full"
                  type="button"
                >
                  <svg
                    width="18"
                    height="18"
                    viewBox="0 0 24 24"
                    fill="none"
                    className="mr-2"
                  >
                    <path
                      d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                  <span>Choose File</span>
                </button>
              </div>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*,.pdf,application/pdf"
                style={{ display: "none" }}
                onChange={handleFileSelect}
              />
            </div>

            {loading && (
              <div className="mt-6 flex items-start gap-3 text-[#4f8f5e] text-sm">
                <div className="h-5 w-5 border-2 border-[#4f8f5e] border-t-transparent rounded-full animate-spin mt-0.5" />
                <div>
                  <p className="font-medium font-quicksand">Validating Certificate</p>
                  <p className="text-[#7aa487] font-quicksand">
                    Please wait while we verify your certificate...
                  </p>
                </div>
              </div>
            )}

            {result && (
              <div
                className={`mt-6 border-l-4 px-4 py-3 text-sm ${
                  type === "valid"
                    ? "border-[#4f8f5e] bg-[#e8f5ed] text-[#2f5f3b]"
                    : "border-[#c85c5c] bg-[#fceced] text-[#8a3131]"
                }`}
              >
                <p className="font-semibold mb-1">
                  {type === "valid"
                    ? "Certificate Valid"
                    : "Certificate Invalid"}
                </p>
                <div className="prose prose-sm max-w-none">
                  <ReactMarkdown>{message}</ReactMarkdown>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default UploadCertificate;
