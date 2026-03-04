import json
import os
import csv
import base64
import io
import time
from typing import Any

import requests
from openai import OpenAI
from dotenv import load_dotenv
from excel_client import read_certificates_from_excel, normalize_certificate_no

load_dotenv()

MAX_TOKENS = int(os.getenv("MAX_TOKENS") or "1024")

# OpenAI API configuration for CSV comparison
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_VISION_MODEL = os.getenv("OPENAI_VISION_MODEL") or "gpt-4o"

# Excel Online configuration for certificate validation
# Configuration is handled in excel_client.py

# Initialize OpenAI client
openai_client = OpenAI(
    api_key=OPENAI_API_KEY
)


def _extract_json_from_text(text: str) -> dict:
    if text is None:
        return {"raw_response": ""}

    cleaned = text.strip()

    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if len(lines) >= 2 and lines[0].startswith("```"):
            fence_lang = lines[0].strip().lower()
            if fence_lang in {"```", "```json"}:
                lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    start_candidates = [i for i in [cleaned.find("{"), cleaned.find("[")] if i != -1]
    if start_candidates:
        start = min(start_candidates)
        end_candidates = [i for i in [cleaned.rfind("}"), cleaned.rfind("]")] if i != -1]
        if end_candidates:
            end = max(end_candidates)
            snippet = cleaned[start : end + 1].strip()
            try:
                return json.loads(snippet)
            except json.JSONDecodeError:
                pass

    return {"raw_response": text}


def _pdf_pages_to_base64_images(pdf_bytes: bytes, max_pages: int = 3, dpi: int = 200) -> list[str]:
    """Convert PDF pages to base64-encoded PNG images for Vision API analysis."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        print("PyMuPDF not installed. Install with: pip install PyMuPDF")
        return []

    images = []
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        for page_num in range(min(len(doc), max_pages)):
            page = doc[page_num]
            zoom = dpi / 72
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            img_bytes = pix.tobytes("png")
            images.append(base64.b64encode(img_bytes).decode("utf-8"))
        doc.close()
    except Exception as e:
        print(f"Error converting PDF to images: {e}")
    return images


def _analyze_certificate_pdf_with_openai(pdf_b64: str) -> dict:
    """Extract certificate data from a PDF by converting pages to images and using Vision API."""
    if OPENAI_API_KEY is None or OPENAI_API_KEY == "your_openai_api_key_here":
        return {"error": "You need to provide an OPENAI_API_KEY environment variable"}

    try:
        pdf_bytes = base64.b64decode(pdf_b64)
    except Exception as e:
        return {"error": f"Invalid PDF base64 data: {e}"}

    page_images = _pdf_pages_to_base64_images(pdf_bytes)
    if not page_images:
        return {"error": "Could not extract any pages from the PDF. The file may be corrupted or empty."}

    prompt = (
        "Extract the following information from this certificate PDF and return as JSON: "
        "certificate_no, issue_date, company_reg_no, company_name. "
        "If any field is not found, return null for that field. Be precise and concise."
    )

    content_parts: list[dict] = [{"type": "text", "text": prompt}]
    for img_b64 in page_images:
        content_parts.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{img_b64}"}
        })

    try:
        response = openai_client.chat.completions.create(
            model=OPENAI_VISION_MODEL,
            messages=[
                {"role": "system", "content": "Be precise and concise. Always return valid JSON."},
                {"role": "user", "content": content_parts},
            ],
            temperature=0.0,
            max_tokens=MAX_TOKENS,
        )
        result_text = response.choices[0].message.content or ""
        return _extract_json_from_text(result_text)
    except Exception as e:
        return {"error": f"PDF analysis API request failed: {e}"}


def _is_pdf_mime(mime_type: str) -> bool:
    """Check if a MIME type indicates a PDF."""
    return mime_type.lower() in ("application/pdf", "pdf")


def _analyze_certificate_image_with_openai(*, image_b64: str, mime_type: str) -> dict:
    if OPENAI_API_KEY is None or OPENAI_API_KEY == "your_openai_api_key_here":
        return {"error": "You need to provide an OPENAI_API_KEY environment variable"}

    if not mime_type or not mime_type.startswith("image/") or mime_type == "image":
        mime_type = "image/jpeg"

    if not image_b64:
        return {"error": "No image data to process"}

    prompt = (
        "Extract the following information from this certificate image and return as JSON: "
        "certificate_no, issue_date, company_reg_no, company_name. "
        "If any field is not found, return null for that field. Be precise and concise."
    )

    image_data_url = f"data:{mime_type};base64,{image_b64}"

    try:
        response = openai_client.chat.completions.create(
            model=OPENAI_VISION_MODEL,
            messages=[
                {"role": "system", "content": "Be precise and concise. Always return valid JSON."},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_data_url}},
                    ],
                },
            ],
            temperature=0.0,
            max_tokens=MAX_TOKENS,
        )

        result_text = response.choices[0].message.content or ""
        return _extract_json_from_text(result_text)
    except Exception as e:
        return {"error": f"API request failed: {e}. Please try again or contact support."}

def extract_certificate_data_from_url(image_url: str = None, image_base64: str = None, mime_type: str = "image/jpeg") -> dict:
    """Extract certificate data from image URL or base64 data using OpenAI"""
    if OPENAI_API_KEY is None or OPENAI_API_KEY == "your_openai_api_key_here":
        return {"error": "You need to provide an OPENAI_API_KEY environment variable"}
    
    try:
        # First check if image_url is provided
        if image_url:
            # Check if image_url is actually base64 data
            if image_url.startswith('data:') or len(image_url) > 1000:  # Likely base64
                # Remove data URL prefix if present
                if image_url.startswith('data:'):
                    parts = image_url.split(',', 1)
                    image_data = parts[1] if len(parts) > 1 else image_url
                else:
                    image_data = image_url
            else:
                # Fetch the file from URL and convert to base64
                response = requests.get(image_url, timeout=30)
                response.raise_for_status()
                image_data = base64.b64encode(response.content).decode('utf-8')
                # Detect mime from response headers if not explicitly set or generic
                resp_content_type = response.headers.get('content-type', '').split(';')[0].strip()
                if not mime_type or mime_type == "image/jpeg":
                    if resp_content_type:
                        mime_type = resp_content_type
        # If no image_url, check for base64 data
        elif image_base64:
            if image_base64.startswith('data:'):
                parts = image_base64.split(',', 1)
                image_data = parts[1] if len(parts) > 1 else image_base64
            else:
                image_data = image_base64
        else:
            return {"error": "Either image_url or image_base64 must be provided"}
        
        if _is_pdf_mime(mime_type):
            return _analyze_certificate_pdf_with_openai(pdf_b64=image_data)
        return _analyze_certificate_image_with_openai(image_b64=image_data, mime_type=mime_type)
            
    except requests.exceptions.Timeout:
        return {"error": "The request timed out. Please try again."}
    except requests.exceptions.RequestException as e:
        print(f"DEBUG: Request exception: {e}")
        msg = str(e)
        if any(k in msg for k in [" 429 ", " 500 ", " 502 ", " 503 ", " 504 ", " 529 ", "timed out", "Connection aborted", "Connection reset", "Temporary failure"]):
            return {"error": "Temporary upstream service error. Please try again in a few moments."}
        return {"error": f"API request failed: {e}. Please try again or contact support."}
    except Exception as e:
        print(f"DEBUG: General exception: {e}")
        return {"error": f"Certificate data extraction failed: {str(e)}"}

def extract_certificate_data(image_content: str, mime_type: str) -> dict:
    """Extract certificate data from image or PDF using OpenAI"""
    if OPENAI_API_KEY is None or OPENAI_API_KEY == "your_openai_api_key_here":
        return {"error": "You need to provide an OPENAI_API_KEY environment variable"}
    
    try:
        if _is_pdf_mime(mime_type):
            print(f"DEBUG: Routing to PDF analysis pipeline (mime: {mime_type})")
            return _analyze_certificate_pdf_with_openai(pdf_b64=image_content)
        return _analyze_certificate_image_with_openai(image_b64=image_content, mime_type=mime_type)
            
    except requests.exceptions.Timeout:
        return {"error": "The request timed out. Please try again."}
    except requests.exceptions.RequestException as e:
        print(f"DEBUG: Request exception: {e}")
        msg = str(e)
        if any(k in msg for k in [" 429 ", " 500 ", " 502 ", " 503 ", " 504 ", " 529 ", "timed out", "Connection aborted", "Connection reset", "Temporary failure"]):
            return {"error": "Temporary upstream service error. Please try again in a few moments."}
        return {"error": f"API request failed: {e}. Please try again or contact support."}
    except Exception as e:
        print(f"DEBUG: General exception: {e}")
        return {"error": f"Certificate data extraction failed: {str(e)}"}

def validate_certificate_in_sheets(certificate_data: dict) -> dict:
    """Validate certificate against Excel Online database using OpenAI for intelligent comparison"""
    if OPENAI_API_KEY is None or OPENAI_API_KEY == "your_openai_api_key_here":
        return {"valid": False, "reason": "You need to provide an OPENAI_API_KEY environment variable"}
    
    try:
        # Read data from Excel Online
        print(f"DEBUG: Reading certificates from Excel Online database")
        sheets_records = read_certificates_from_excel()
        print(f"DEBUG: Found {len(sheets_records) if sheets_records else 0} records in Excel Online")
        
        if not sheets_records:
            print(f"DEBUG: Excel Online validation failed - no records found")
            return {"valid": False, "reason": "Excel Online is empty or inaccessible"}
        
        # Use OpenAI to intelligently compare extracted data with Google Sheets records
        try:
            comparison_prompt = f"""
You are a certificate validation expert. Compare the extracted certificate data with the Excel Online database records to determine if this is a valid certificate.

Only compare these 4 fields: certificate_no, issue_date, company_reg_no, company_name

Extracted Certificate Data:
{json.dumps(certificate_data, indent=2)}

Excel Online Database Records:
{json.dumps(sheets_records, indent=2)}

Instructions:
1. Focus ONLY on these 4 fields: certificate_no, issue_date, company_reg_no, company_name
2. Look for exact or close matches in certificate numbers, company names, registration numbers
3. Consider date formats might vary (e.g., "2024-01-15" vs "Jan 15, 2024" vs "16 Dec 2024")
4. Company names might have slight variations (e.g., "ABC Corp" vs "ABC Corporation" vs "ABC Ltd")
5. Certificate numbers should match closely (consider formatting differences)
6. Return a JSON response with: {{"valid": true/false, "reason": "explanation", "matched_record": {{...}} or null}}

Be precise and thorough in your comparison of these 4 fields only.
"""

            print(f"DEBUG: Using OpenAI for intelligent certificate comparison")
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Be precise and concise. Always return valid JSON."},
                    {"role": "user", "content": comparison_prompt}
                ],
                temperature=0.2,
                max_tokens=1000
            )
            
            result = response.choices[0].message.content or ""
            print(f"DEBUG: OpenAI validation response: {result}")
            
            try:
                validation_result = json.loads(result)
                print(f"DEBUG: Parsed OpenAI validation result: {validation_result}")
                return validation_result
            except json.JSONDecodeError:
                print(f"DEBUG: Failed to parse OpenAI response, falling back to simple validation")
                # Fallback to simple certificate number matching
                return simple_sheets_validation(certificate_data, sheets_records)
                
        except Exception as e:
            print(f"DEBUG: OpenAI validation failed with error: {e}, falling back to simple validation")
            # Fallback to simple certificate number matching
            return simple_sheets_validation(certificate_data, sheets_records)
        
    except Exception as e:
        return {"valid": False, "reason": f"Error validating certificate: {str(e)}"}

def normalize_certificate_no(cert_no: str) -> str:
    """Normalize certificate number by replacing various dash characters with standard hyphen"""
    if not cert_no:
        return ""
    # Replace em-dash, en-dash, and other dash variants with standard hyphen
    return cert_no.replace('–', '-').replace('—', '-').replace('―', '-').strip()

def simple_sheets_validation(certificate_data: dict, sheets_records: list) -> dict:
    """Simple fallback validation by certificate number matching"""
    extracted_cert_no = normalize_certificate_no(str(certificate_data.get('certificate_no', '')))
    print(f"DEBUG: Simple validation - Looking for certificate number: '{extracted_cert_no}'")
    
    for row in sheets_records:
        db_cert_no = normalize_certificate_no(str(row.get('certificate_no', '')))
        if extracted_cert_no and db_cert_no == extracted_cert_no:
            print(f"DEBUG: Simple validation - MATCH FOUND: '{db_cert_no}' matches '{extracted_cert_no}'")
            return {
                "valid": True, 
                "reason": "Certificate number found in database",
                "matched_record": row
            }
    
    print(f"DEBUG: Simple validation - NO MATCH FOUND for certificate number: '{extracted_cert_no}'")
    return {"valid": False, "reason": "Certificate not found in database"}

def _validate_extracted_certificate(extracted_data: dict) -> dict:
    """Validate extracted certificate data using the unified verify_certificate flow
    (DB + Excel Graph), falling back to the Excel Online sheet comparison."""
    cert_no = extracted_data.get("certificate_no")
    if not cert_no:
        return {"valid": False, "reason": "No certificate number extracted"}

    try:
        from agent import verify_certificate
        is_valid, verified_data = verify_certificate(cert_no)
        if is_valid:
            return {
                "valid": True,
                "reason": "Certificate found in database",
                "matched_record": verified_data,
            }
    except Exception as e:
        print(f"DEBUG: verify_certificate unavailable or failed: {e}")

    # Fallback to Excel Online sheet comparison
    return validate_certificate_in_sheets(extracted_data)


def get_image_analysis(
    content: list[dict[str, Any]], tool: dict[str, Any] | None = None
) -> str | None:
    """Process certificate image or PDF and validate it"""
    extracted_data = None
    validation_result = None
    
    for item in content:
        mime_type = item.get("mime_type", "")
        is_image = mime_type.startswith("image/")
        is_pdf = _is_pdf_mime(mime_type)
        if item.get("type") == "resource" and (is_image or is_pdf):
            file_type_label = "PDF" if is_pdf else "image"
            print(f"DEBUG: Starting certificate extraction from {file_type_label} base64 content")
            extracted_data = extract_certificate_data_from_url(
                image_base64=item.get("contents", ""), 
                mime_type=mime_type
            )
            print(f"DEBUG: Certificate extraction result: {extracted_data}")
            
            if extracted_data and "error" not in extracted_data:
                print(f"DEBUG: Starting validation (DB → Excel Graph → Excel Online)")
                validation_result = _validate_extracted_certificate(extracted_data)
                print(f"DEBUG: Validation result: {validation_result}")
            else:
                print(f"DEBUG: Skipping validation due to extraction error")
            break
        elif item.get("type") == "image_url":
            image_url = item["image_url"]["url"]
            mime_type = item.get("mime_type", "image/jpeg")
            
            print(f"DEBUG: Starting certificate extraction from URL: {image_url}")
            extracted_data = extract_certificate_data_from_url(
                image_url=image_url, 
                mime_type=mime_type
            )
            print(f"DEBUG: Certificate extraction result: {extracted_data}")
            
            if extracted_data and "error" not in extracted_data:
                print(f"DEBUG: Starting validation (DB → Excel Graph → Excel Online)")
                validation_result = _validate_extracted_certificate(extracted_data)
                print(f"DEBUG: Validation result: {validation_result}")
            else:
                print(f"DEBUG: Skipping validation due to extraction error")
            break
    
    if not extracted_data:
        return "No certificate image or PDF found to process."
    
    if "error" in extracted_data:
        error_msg = extracted_data['error']
        print(f"DEBUG: Error in extraction: {error_msg}")
        
        # Provide a helpful fallback message
        if "400 Client Error" in error_msg or "API request failed" in error_msg:
            return f"❌ **Certificate Analysis Failed**\n\nI'm having trouble analyzing this certificate right now. This could be due to:\n\n• Image/PDF format or size issues\n• Temporary API service problems\n• Image quality or resolution\n\nPlease try:\n1. Using a clearer, higher resolution image or PDF\n2. Uploading a different format (JPG, PNG, PDF)\n3. Trying again in a few minutes\n\nFor immediate assistance, contact HCO at info@hcoltd.co.uk or +44 (0) 333 577 0902."
        else:
            return f"Error processing image: {error_msg}"
    
    # Format human-friendly response
    print(f"DEBUG: Final verification decision - Validation result: {validation_result}")
    if validation_result and validation_result.get('valid', False):
        company_name = extracted_data.get('company_name', 'Unknown Company')
        issue_date = extracted_data.get('issue_date', 'Unknown Date')
        certificate_no = extracted_data.get('certificate_no', 'Unknown Certificate')
        
        print(f"DEBUG: ✅ CERTIFICATE VERIFIED - Company: {company_name}, Date: {issue_date}, Cert No: {certificate_no}")
        response = f"✅ **Certificate Verified!**\n\n"
        response += f"This is a valid HCO certificate for **{company_name}**, issued on **{issue_date}**.\n\n"
        response += f"Certificate Number: {certificate_no}"
    else:
        reason = validation_result.get('reason', 'Unknown reason') if validation_result else 'No validation performed'
        print(f"DEBUG: ❌ CERTIFICATE NOT VERIFIED - Reason: {reason}")
        response = f"❌ **Certificate Not Valid**\n\n"
        response += "This certificate is not valid. If you need a valid HCO certificate, please apply at https://www.hcoltd.co.uk/registration or contact HCO directly for assistance at info@hcoltd.co.uk or +44 (0) 333 577 0902."
    
    return response
