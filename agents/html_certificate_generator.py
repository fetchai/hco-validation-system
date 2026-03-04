#!/usr/bin/env python3
"""
HTML-based Halal Certificate Generator
Generates certificates using HTML templates and converts them to PDF
"""

import os
import io
import base64
import html
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from openai import OpenAI


_HCO_LOGO_DATA_URI: Optional[str] = None


def _get_hco_logo_data_uri() -> str:
    global _HCO_LOGO_DATA_URI
    if _HCO_LOGO_DATA_URI:
        return _HCO_LOGO_DATA_URI

    logo_path = os.path.join(os.path.dirname(__file__), "HCO-Logo.png")
    try:
        with open(logo_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("ascii")
        _HCO_LOGO_DATA_URI = f"data:image/png;base64,{encoded}"
    except Exception:
        _HCO_LOGO_DATA_URI = ""
    return _HCO_LOGO_DATA_URI


def _build_export_logo_html(logo_option: str) -> str:
    opt = (logo_option or "").strip().lower()
    if opt in ("none", "no", "no_logo", "no-logo"):
        return ""

    if opt in ("enas", "en"):
        return '<img src="enas.webp" alt="ENAS" style="width: 80px; height: auto;" />'

    # Treat GAC as the existing GCC logo asset.
    if opt in ("gac", "gcc"):
        return '<img src="gcc-domestic-logo.jpg" alt="GAC" style="width: 80px; height: auto;" />'

    # Default (backwards-compatible): ENAS
    return '<img src="enas.webp" alt="ENAS" style="width: 80px; height: auto;" />'


def _build_export_signature_block_html(signature_option: str) -> str:
    opt = (signature_option or "").strip().lower()
    if opt in ("without", "no", "none", "false", "0"):
        return ""

    # Default to "with" when empty.
    return (
        '<div class="signature-block">'
        '<img class="signature-img" src="AmerRashid.png" alt="Signature" />'
        '<div class="signature-name">Dr. Amer Rashid</div>'
        '<div class="signature-title">Technical Director</div>'
        '</div>'
    )


def format_date_dmy(date_str: str) -> str:
    """
    Convert date from YYYY-MM-DD format to DD-MM-YYYY format.
    If the date is already in DD-MM-YYYY or another format, try to parse and convert it.
    """
    if not date_str:
        return date_str

    # Try different date formats
    formats_to_try = [
        '%Y-%m-%d',      # 2025-01-15
        '%d-%m-%Y',      # 15-01-2025 (already correct)
        '%d/%m/%Y',      # 15/01/2025
        '%Y/%m/%d',      # 2025/01/15
        '%m-%d-%Y',      # 01-15-2025
        '%m/%d/%Y',      # 01/15/2025
    ]

    for fmt in formats_to_try:
        try:
            parsed_date = datetime.strptime(date_str.strip(), fmt)
            return parsed_date.strftime('%d-%m-%Y')
        except ValueError:
            continue

    # If no format matched, return original
    return date_str


def format_date_non_meat_display(date_str: str) -> str:
    if not date_str:
        return date_str

    try:
        parsed = datetime.strptime(date_str.strip(), "%Y-%m-%d")
        if parsed.day == 1:
            return parsed.strftime("%B %Y")
        return parsed.strftime("%d-%m-%Y")
    except ValueError:
        return format_date_dmy(date_str)


def get_ordinal_suffix(day: int) -> str:
    """Get the ordinal suffix for a day number (st, nd, rd, th)."""
    if 11 <= day <= 13:
        return 'th'
    suffix_map = {1: 'st', 2: 'nd', 3: 'rd'}
    return suffix_map.get(day % 10, 'th')


def format_date_long(date_str: str) -> str:
    """
    Convert date to long format like "19th January 2025".
    """
    if not date_str:
        return date_str

    # Try different date formats
    formats_to_try = [
        '%Y-%m-%d',      # 2025-01-15
        '%d-%m-%Y',      # 15-01-2025
        '%d/%m/%Y',      # 15/01/2025
        '%Y/%m/%d',      # 2025/01/15
        '%m-%d-%Y',      # 01-15-2025
        '%m/%d/%Y',      # 01/15/2025
    ]

    for fmt in formats_to_try:
        try:
            parsed_date = datetime.strptime(date_str.strip(), fmt)
            day = parsed_date.day
            suffix = get_ordinal_suffix(day)
            # Format: "19th January 2025"
            return f"{day}{suffix} {parsed_date.strftime('%B %Y')}"
        except ValueError:
            continue

    # If no format matched, return original
    return date_str


def calculate_expiry_date(issue_date_str: str, validity_period: str) -> str:
    """
    Calculate expiry date based on issue date and validity period.
    Expiry date = issue date + validity_period years - 1 day.

    For example:
    - Issue: 19-01-2025, validity: 3 years → Expiry: 18-01-2028
    - Issue: 12-09-2025, validity: 2 years → Expiry: 11-09-2027

    Returns date in DD-MM-YYYY format.
    """
    if not issue_date_str:
        return ""

    # Try to parse validity_period as integer
    try:
        years = int(validity_period) if validity_period else 3
    except ValueError:
        years = 3

    # Try different date formats
    formats_to_try = [
        '%Y-%m-%d',      # 2025-01-15
        '%d-%m-%Y',      # 15-01-2025
        '%d/%m/%Y',      # 15/01/2025
        '%Y/%m/%d',      # 2025/01/15
        '%m-%d-%Y',      # 01-15-2025
        '%m/%d/%Y',      # 01/15/2025
    ]

    for fmt in formats_to_try:
        try:
            parsed_date = datetime.strptime(issue_date_str.strip(), fmt)
            # Add validity_period years
            try:
                # Try to replace year directly (handles Feb 29 edge case)
                expiry_date = parsed_date.replace(year=parsed_date.year + years)
            except ValueError:
                # If Feb 29 doesn't exist in target year, use Feb 28
                expiry_date = parsed_date.replace(year=parsed_date.year + years, day=28)

            # Subtract 1 day to get the actual expiry date
            expiry_date = expiry_date - timedelta(days=1)

            # Return in DD-MM-YYYY format
            return expiry_date.strftime('%d-%m-%Y')
        except ValueError:
            continue

    # If no format matched, return empty
    return ""

# Initialize OpenAI client
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY)





def generate_html_certificate(
    certificate_no: str,
    company_name: str,
    company_reg_no: str,
    issue_date: str,
    expiry_date: str,
    standards: str,
    company_address: str,
    pu: str,
    au: str,
    sow: str,
    products: List[Dict[str, Any]] = None,
    company_logo: Optional[Dict[str, Any]] = None,
    validity_period: str = "3",
    cert_num_footer: str = "",
    annex_layout_options: Optional[Dict[str, Any]] = None,
    domestic_logo_1: str = "gac",
    domestic_logo_2: str = "none",
) -> bytes:
    """
    Generate multi-page PDF certificate using HTML templates
    
    Returns:
        bytes: PDF data
    """
    if products is None:
        products = []

    # Format dates to DD-MM-YYYY format
    issue_date_formatted = format_date_dmy(issue_date)

    # Calculate expiry date dynamically if not provided or empty
    if not expiry_date or expiry_date.strip() == "":
        # Parse the issue date and add validity_period years, then subtract 1 day
        expiry_date_formatted = calculate_expiry_date(issue_date, validity_period)
    else:
        expiry_date_formatted = format_date_dmy(expiry_date)

    # Generate annex pages HTML (needed first to compute total page count)
    print(f"🔍 About to generate annex pages with {len(products)} products")
    annex_html_pages = generate_annex_pages_html(
        certificate_no, company_name, company_reg_no, issue_date_formatted,
        expiry_date_formatted, standards, products, validity_period=validity_period,
        cert_num_footer=cert_num_footer,
        annex_layout_options=annex_layout_options,
        watermark=True,
        domestic_logo_1=domestic_logo_1,
        domestic_logo_2=domestic_logo_2,
    )
    
    print(f"\U0001F4C4 Generated {len(annex_html_pages)} annex pages")

    total_pages_all = 1 + len(annex_html_pages)

    # Generate main certificate HTML (global page numbering)
    main_certificate_html = generate_main_certificate_html(
        certificate_no, company_name, company_reg_no, issue_date_formatted,
        expiry_date_formatted, issue_date_formatted, issue_date_formatted, standards, company_address, pu, au, sow,
        company_logo=company_logo,
        validity_period=validity_period,
        page_number=1,
        total_pages=total_pages_all,
        cert_num_footer=cert_num_footer,
        total_products=len(products),
        domestic_logo_1=domestic_logo_1,
        domestic_logo_2=domestic_logo_2,
    )
    
    # Combine all HTML pages
    all_html_pages = [main_certificate_html] + annex_html_pages

    # Defensive: avoid None pages breaking concatenation/PDF generation.
    # (WeasyPrint/pdfkit expect strings; a None here causes TypeError)
    cleaned_pages: List[str] = []
    for idx, page in enumerate(all_html_pages):
        if page is None:
            print(f"⚠️  Warning: HTML page {idx} is None; skipping")
            continue
        cleaned_pages.append(str(page))
    all_html_pages = cleaned_pages
    print(f"📄 Total pages for PDF: {len(all_html_pages)} (1 main + {len(annex_html_pages)} annex)")
    
    try:
        # Try weasyprint first (preferred method)
        try:
            # Set environment variables for library paths on macOS
            import os
            os.environ['DYLD_LIBRARY_PATH'] = '/opt/homebrew/lib:/usr/local/lib:' + os.environ.get('DYLD_LIBRARY_PATH', '')
            os.environ['PKG_CONFIG_PATH'] = '/opt/homebrew/lib/pkgconfig:/usr/local/lib/pkgconfig:' + os.environ.get('PKG_CONFIG_PATH', '')
            
            from weasyprint import HTML, CSS
            from weasyprint.text.fonts import FontConfiguration
            import tempfile
            
            # Combine HTML pages with proper page breaks
            combined_html = ""
            for i, html_content in enumerate(all_html_pages):
                # Extract body content only for pages after the first
                if i == 0:
                    combined_html += html_content
                else:
                    # Extract body content and add page break
                    import re
                    body_match = re.search(r'<body[^>]*>(.*?)</body>', html_content, re.DOTALL)
                    if body_match:
                        body_content = body_match.group(1)
                        combined_html += f'<div style="page-break-before: always;">{body_content}</div>'
            
            # Generate PDF using weasyprint with proper CSS for A4 pages
            html_doc = HTML(string=combined_html, base_url='.')
            pdf_data = html_doc.write_pdf(
                presentational_hints=True,
                optimize_images=True
            )
            
            print(f"Generated PDF using weasyprint: {len(pdf_data)} bytes")
            return pdf_data
            
        except ImportError:
            print("weasyprint not available, trying pdfkit...")
        except Exception as weasyprint_error:
            print(f"WeasyPrint failed: {weasyprint_error}")
            print("Trying alternative PDF generation methods...")
            
        # Fallback to pdfkit if available
        try:
            import pdfkit
            
            # Convert to PDF
            options = {
                'page-size': 'A4',
                'margin-top': '0',
                'margin-right': '0', 
                'margin-bottom': '0',
                'margin-left': '0',
                'encoding': "UTF-8",
                'no-outline': None,
                'enable-local-file-access': None
            }
            
            # Create temporary HTML files for each page
            temp_files = []
            for i, html_content in enumerate(all_html_pages):
                temp_file = f"/tmp/cert_page_{i}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
                with open(temp_file, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                temp_files.append(temp_file)
            
            # Generate PDF from all HTML files
            pdf_data = pdfkit.from_file(temp_files, False, options=options)
            
            # Clean up temporary files
            for temp_file in temp_files:
                try:
                    os.unlink(temp_file)
                except Exception:
                    pass
            
            print(f"Generated PDF using pdfkit: {len(pdf_data)} bytes")
            return pdf_data
            
        except ImportError:
            print("pdfkit not available either")
            
        # Try playwright for PDF generation
        try:
            from playwright.sync_api import sync_playwright
            
            print("Using playwright for HTML to PDF conversion...")
            
            # Create combined HTML with all pages
            combined_html = ""
            for i, html_content in enumerate(all_html_pages):
                if i == 0:
                    combined_html += html_content
                else:
                    # Extract body content and add page break
                    import re
                    body_match = re.search(r'<body[^>]*>(.*?)</body>', html_content, re.DOTALL)
                    if body_match:
                        body_content = body_match.group(1)
                        combined_html += f'<div style="page-break-before: always;">{body_content}</div>'
            
            # Use playwright to convert HTML to PDF
            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    page = browser.new_page()
                    page.set_content(combined_html, wait_until='networkidle')
                    
                    # Wait for any images to load
                    page.wait_for_timeout(1000)
                    
                    pdf_data = page.pdf(
                        format='A4',
                        margin={'top': '10mm', 'right': '10mm', 'bottom': '10mm', 'left': '10mm'},
                        print_background=True,
                        prefer_css_page_size=True
                    )
                    browser.close()
                
                print(f"Generated PDF using playwright: {len(pdf_data)} bytes")
                
                # Verify PDF data is valid
                if pdf_data and len(pdf_data) > 100 and pdf_data.startswith(b'%PDF'):
                    print("✅ Valid PDF generated")
                    return pdf_data
                else:
                    print("❌ Invalid PDF data generated - falling back to HTML")
                    
            except Exception as pdf_error:
                print(f"Playwright PDF generation failed: {pdf_error}")
                
        except ImportError:
            print("Playwright not available")
        
        # Fallback: return HTML content and let the caller handle it
        print("Falling back to HTML output...")
        combined_html = ""
        for i, html_content in enumerate(all_html_pages):
            if i == 0:
                combined_html += html_content
            else:
                # Extract body content and add page break
                import re
                body_match = re.search(r'<body[^>]*>(.*?)</body>', html_content, re.DOTALL)
                if body_match:
                    body_content = body_match.group(1)
                    combined_html += f'<div style="page-break-before: always;">{body_content}</div>'
        
        return combined_html.encode('utf-8')
        
    except Exception as e:
        print(f"Error in PDF generation: {e}")
        # Return None to indicate failure instead of HTML content
        return None



def generate_main_certificate_html(
    certificate_no: str,
    company_name: str,
    company_reg_no: str,
    issue_date: str,
    expiry_date: str,
    original_approval_date: str,
    current_cycle_start_date: str,
    standards: str,
    company_address: str,
    pu: str,
    au: str,
    sow: str,
    company_logo: Optional[Dict[str, Any]] = None,
    validity_period: str = "3",
    page_number: int = 1,
    total_pages: int = 1,
    cert_num_footer: str = "",
    total_products: int = 0,
    domestic_logo_1: str = "gac",
    domestic_logo_2: str = "none",
) -> str:

    # Format dates to long format (e.g., "19th January 2025")
    original_approval_date_long = format_date_long(original_approval_date)
    current_cycle_start_date_long = format_date_long(current_cycle_start_date)
    expiry_date_long = format_date_long(expiry_date)

    # Create dynamic validity text based on validity_period
    validity_years = validity_period if validity_period else "3"
    try:
        validity_int = int(validity_years)
    except ValueError:
        validity_int = 3

    validity_text = ""
    if validity_int >= 3:
        validity_text = f"(The certificate validity is {validity_years} year{'s' if validity_years != '1' else ''}, subject to annual surveillance audits)"

    cert_num_footer_safe = html.escape((cert_num_footer or "").strip())

    hco_logo_data_uri = _get_hco_logo_data_uri()

    logo_1_html = _build_export_logo_html(domestic_logo_1)
    logo_2_html = _build_export_logo_html(domestic_logo_2)
    logo_parts = [h for h in [logo_1_html, logo_2_html] if h]
    if logo_parts:
        logos_joined = '&nbsp;&nbsp;'.join(logo_parts)
        gcc_logo_html = f'<td class="sig-cell-center" style="text-align: center; vertical-align: middle; width: 34%;">{logos_joined}</td>'
        sig_cell_width = "33%"
    else:
        gcc_logo_html = ""
        sig_cell_width = "50%"

    # Generate table rows
    table_rows = ""

    # Company logo (optional). If provided, embed as a data URI so WeasyPrint can render it.
    company_logo_html = '<div class="no-logo">HCO</div>'
    try:
        if isinstance(company_logo, dict):
            logo_b64 = (company_logo.get("data") or "").strip()
            if logo_b64:
                # If the frontend already sent a data URI, keep it. Otherwise build one.
                if logo_b64.startswith("data:"):
                    logo_src = logo_b64
                else:
                    content_type = (company_logo.get("content_type") or "image/png").strip() or "image/png"
                    logo_src = f"data:{content_type};base64,{logo_b64}"
                company_logo_html = f'<img class="company-logo-img" src="{logo_src}" alt="Company Logo" />'
    except Exception:
        # Fallback to placeholder if any parsing fails
        company_logo_html = '<div class="no-logo">HCO</div>'
    
    # Determine what to show for PU/AU
    pu_au_content = ""
    section_label = "SoW"
    
    if pu:
        pu_au_content += f'<div class="pu-line"><strong>PU:</strong> {pu}</div>'
        section_label = "PU & SoW"
    elif au:
        pu_au_content += f'<div class="au-line"><strong>AU:</strong> {au}</div>'
        section_label = "AU & SoW"
    else:
        # If neither PU nor AU is provided, show company address as PU
        pu_au_content += f'<div class="pu-line"><strong>PU:</strong> {company_address}</div>'
        section_label = "PU & SoW"
    
    pu_au_content += f'<div class="sow-line"><strong>SoW:</strong> {sow}</div>'
    
    # Row 1: PU/AU & SoW with company logo
    table_rows += f"""
        <tr>
            <td class="code-column">
                <div class="pu-sow-label">{section_label}</div>
                <div class="company-logo">
                    {company_logo_html}
                </div>
            </td>
            <td class="description-column">
                {pu_au_content}
            </td>
        </tr>"""
    
    # Row 2: PL with Annex reference
    table_rows += f"""
        <tr>
            <td class="code-column">
                <div class="pl-label">PL</div>
                <div class="company-logo">
                    {company_logo_html}
                </div>
            </td>
            <td class="description-column">
                <div class="annex-reference">Please see attached Annex A - approved list of Halal products.</div>
            </td>
        </tr>"""
    
    cert_num_footer_safe = html.escape((cert_num_footer or "").strip())

    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Halal Certificate</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        @page {{
            size: A4;
            margin: 0;
        }}

        body {{
            font-family: 'Georgia', 'Times New Roman', serif;
            background-color: #ffffff;
            padding: 0;
            margin: 0;
        }}

        .certificate-container {{
            width: 210mm;
            height: 297mm;
            margin: 0 auto;
            background: #ffffff;
            border: 6px solid #0a2b20;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
            padding: 8mm;
            position: relative;
            overflow: hidden;
            page-break-inside: avoid;
        }}

        .certificate-container::before {{
            content: "";
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-image: url('{hco_logo_data_uri}');
            background-repeat: no-repeat;
            background-position: center;
            background-size: 65% auto;
            opacity: 0.13;
            pointer-events: none;
            z-index: 0;
        }}

        /* Decorative corner elements */
        .corner-decoration {{
            position: absolute;
            width: 50px;
            height: 50px;
            border: 2px solid #90c850;
        }}

        .corner-decoration.top-left {{
            top: 12px;
            left: 12px;
            border-right: none;
            border-bottom: none;
        }}

        .corner-decoration.top-right {{
            top: 12px;
            right: 12px;
            border-left: none;
            border-bottom: none;
        }}

        .corner-decoration.bottom-left {{
            bottom: 12px;
            left: 12px;
            border-right: none;
            border-top: none;
        }}

        .corner-decoration.bottom-right {{
            bottom: 12px;
            right: 12px;
            border-left: none;
            border-top: none;
        }}

        /* Subtle pattern overlay */
        .pattern-overlay {{
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            opacity: 0.015;
            background-image:
                repeating-linear-gradient(45deg, transparent, transparent 40px, #1a4d3a 40px, #1a4d3a 41px);
            pointer-events: none;
        }}

        .content-wrapper {{
            position: relative;
            z-index: 2;
            height: 100%;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }}

        .main-content {{
            flex: 1 1 auto;
            min-height: 0;
        }}

        .header {{
            text-align: center;
            margin-bottom: 8px;
        }}

        .logo-container {{
            display: inline-block;
            margin-bottom: 5px;
        }}

        .hco-logo {{
            width: auto;
            height: 55px;
            display: block;
        }}

        .title {{
            font-size: 36px;
            font-weight: 400;
            color: #1a4d3a;
            letter-spacing: 5px;
            margin-bottom: 5px;
            text-transform: uppercase;
            font-family: 'Georgia', serif;
        }}

        .cert-header-row {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin: 14px 20px 6px 20px;
        }}

        .issue-date {{
            font-size: 10px;
            color: #1a4d3a;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-weight: 700;
            text-align: left;
            margin: 0;
            padding-top: 2px;
        }}

        .cert-info {{
            text-align: right;
            font-size: 12px;
            color: #333;
            font-family: 'Arial', sans-serif;
            margin: 0;
        }}

        .cert-info-item {{
            padding: 1px 0;
            line-height: 1.4;
        }}

        .cert-info-item .label {{
            font-weight: 700;
            color: #1a4d3a;
        }}

        .auth-text {{
            text-align: center;
            font-size: 14px;
            font-weight: 400;
            margin: 8px 0;
            color: #444;
            font-style: italic;
        }}

        .company-info {{
            text-align: center;
            margin: 8px 0;
            padding: 8px 30px;
        }}

        .company-line {{
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            font-size: 21px;
            font-weight: 600;
            color: #1a4d3a;
            margin: 6px auto;
            padding: 6px 0;
            border-bottom: 2px solid #1a4d3a;
            width: 65%;
            letter-spacing: 0.5px;
            
        }}
        .company-logo-head {{
            align-self: flex-start;
        }}

        .company-reg-display {{
            font-size: 10px;
            margin: 6px auto;
            font-style: italic;
            color: #777;
            font-weight: 400;
        }}

        .registered-text {{
            font-weight: 500;
            font-size: 13px;
            margin: 8px 0 6px 0;
            color: #555;
        }}

        .company-address {{
            font-size: 11px;
            margin: 6px auto;
            width: 75%;
            font-weight: 400;
            color: #555;
            line-height: 1.5;
            overflow-wrap: anywhere;
            word-break: break-word;
        }}

        .description-text {{
            font-size: 10px;
            line-height: 1.6;
            margin: 8px 40px;
            text-align: center;
            color: #444;
            padding: 8px 20px;
            overflow-wrap: anywhere;
            word-break: break-word;
        }}

        .section-divider {{
            border: none;
            border-top: 1px solid #ddd;
            margin: 8px 40px;
        }}

        .products-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 10px 0;
            font-family: 'Arial', sans-serif;
            table-layout: fixed;
        }}

        .products-table th {{
            background: #1a4d3a;
            color: white;
            padding: 6px 8px;
            text-align: center;
            font-weight: 600;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 1px;
            border: 1px solid #0a2b20;
        }}

        .products-table td {{
            border: 1px solid #464646;
            padding: 8px;
            background: transparent;
            overflow-wrap: anywhere;
            word-break: break-word;
            hyphens: auto;
        }}

        .products-table .code-column {{
            width: 30%;
            text-align: center;
            vertical-align: middle;
            background: transparent;
        }}

        .products-table .description-column {{
            width: 70%;
            text-align: left;
            vertical-align: top;
        }}

        .pu-sow-label, .pl-label {{
            font-weight: 600;
            font-size: 12px;
            margin-bottom: 6px;
            color: #1a4d3a;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .company-logo {{
            margin-top: 6px;
            text-align: center;
        }}

        .company-logo-img {{
            display: inline-block;
            max-width: 60px;
            max-height: 28px;
            width: auto;
            height: auto;
            object-fit: contain;
        }}

        .no-logo {{
            background: #1a4d3a;
            color: white;
            padding: 5px 12px;
            border-radius: 3px;
            font-size: 9px;
            font-weight: 600;
            text-align: center;
            display: inline-block;
            letter-spacing: 1.5px;
        }}

        .pu-line, .au-line, .sow-line {{
            margin-bottom: 6px;
            font-size: 11px;
            line-height: 1.4;
            color: #444;
            overflow-wrap: anywhere;
            word-break: break-word;
        }}

        .pu-line strong, .au-line strong, .sow-line strong {{
            color: #1a4d3a;
            font-weight: 600;
        }}

        .annex-reference {{
            font-size: 11px;
            line-height: 1.4;
            font-style: italic;
            color: #666;
        }}

        /* Footer Section */
        .footer-section {{
            flex: 0 0 auto;
            padding-top: 8px;
            margin-top: auto;
        }}

        .signature-table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 6px;
        }}

        .signature-table td {{
            vertical-align: bottom;
            width: 50%;
        }}

        .sig-cell-left {{
            text-align: left;
            padding-left: 30px;
        }}

        .sig-cell-right {{
            text-align: right;
            padding-right: 30px;
        }}

        .signature-block {{
            display: inline-block;
            width: 180px;
            text-align: center;
        }}

        .signature-img {{
            width: 90px;
            height: auto;
            display: block;
            margin: 0 auto 5px;
        }}

        .signature-name {{
            font-style: normal;
            font-size: 11px;
            margin-bottom: 2px;
            color: #1a4d3a;
            font-weight: 600;
        }}

        .signature-title {{
            font-size: 9px;
            color: #777;
            font-weight: 400;
        }}

        .bottom-footer {{
            text-align: center;
            font-family: 'Arial', sans-serif;
            padding-top: 4px;
        }}

        .dates-section {{
            margin-bottom: 4px;
        }}

        .date-line {{
            font-size: 11px;
            color: #000;
            margin: 2px 0;
            line-height: 1.5;
        }}

        .date-line .label {{
            font-weight: 700;
            color: #1a4d3a;
        }}

        .date-line .value {{
            font-weight: 400;
            color: #333;
        }}

        .validity-text {{
            font-size: 9px;
            color: #666;
            margin: 4px 0;
            font-style: italic;
        }}

        .recognition-text {{
            font-size: 6px;
            color: #333;
            font-weight: 600;
            margin: 4px 0;
            white-space: nowrap;
        }}

        .company-details {{
            font-size: 9px;
            color: #333;
            margin: 3px 0;
            line-height: 1.4;
        }}

        .contact-details {{
            font-size: 9px;
            color: #333;
            margin: 3px 0;
        }}

        .website {{
            font-size: 9px;
            color: #90c850;
            font-weight: 700;
            letter-spacing: 0.5px;
            margin-top: 2px;
        }}

        .verification-section {{
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 6px 0 2px 0;
            padding: 4px 0;
            border-top: 1px solid #ddd;
        }}

        .qr-code {{
            width: 45px;
            height: 45px;
            margin-right: 10px;
        }}

        .verification-text {{
            font-size: 7px;
            color: #555;
            text-align: left;
            line-height: 1.4;
        }}

        .verification-text a {{
            color: #1a4d3a;
            text-decoration: none;
            font-weight: 600;
        }}

        /* Print styles */
        @media print {{
            body {{
                background-color: white;
                padding: 0;
                margin: 0;
            }}

            .certificate-container {{
                box-shadow: none;
                margin: 0;
                page-break-after: avoid;
                page-break-inside: avoid;
            }}
        }}
    </style>
</head>
<body>
    <div class="certificate-container">
        <!-- Decorative corners -->
        <div class="corner-decoration top-left"></div>
        <div class="corner-decoration top-right"></div>
        <div class="corner-decoration bottom-left"></div>
        <div class="corner-decoration bottom-right"></div>

        <!-- Pattern overlay -->
        <div class="pattern-overlay"></div>

        <div class="content-wrapper">
            <!-- Main Content -->
            <div class="main-content">
                <div class="header">
                    <div class="logo-container">
                        <img class="hco-logo" src="HCO-Logo.png" alt="HCO Logo">
                    </div>

                    <div class="title">Halal Certificate</div>

                    <div class="cert-header-row">
                        <div class="issue-date">Issue Date: {issue_date}</div>
                        <div class="cert-info">
                            <div class="cert-info-item"><span class="label">Certificate No:</span> {certificate_no}</div>
                            <div class="cert-info-item standard"><span class="label">Standard:</span> {standards}</div>
                        </div>
                    </div>

                    <div class="auth-text">This is to authenticate that</div>
                </div>

                <div class="company-info">
                    <div class="company-line">
                    <div class="company-logo company-logo-head">{company_logo_html}</div>
                    {company_name}
                    </div>
                    <div class="company-reg-display">(Company Register Number: {company_reg_no})</div>
                    <div class="registered-text">registered at</div>
                    <div class="company-address">{company_address}</div>
                </div>

                <div class="description-text">
                    is certified for the following products and its production facilities according to <strong>{standards}</strong><br>
                    Islamic dietary regulations, UK Good Manufacturing Practices (GMP), HACCP and HCO's relevant standard.
                </div>

                <hr class="section-divider">

                <table class="products-table">
                    <thead>
                        <tr>
                            <th style="width: 30%;">Code</th>
                            <th style="width: 70%;">Description</th>
                        </tr>
                    </thead>
                    <tbody>
                        {table_rows}
                    </tbody>
                </table>

                <div class="halal-disclaimer" style="text-align: left; font-size: 9px; color: #555; margin: 8px 0; font-style: italic;">
                    *All approved and named products with a Halal Logo are permissible for Muslim consumption.
                </div>
            </div>

            <!-- Footer Section -->
            <div class="footer-section">
                <table class="signature-table">
                    <tr>
                        <td class="sig-cell-left" style="width: {sig_cell_width};">
                            <div class="signature-block">
                                <img class="signature-img" src="khalid.png" alt="Signature">
                                <div class="signature-name">Dr Mohammad Khalid</div>
                                <div class="signature-title">Member of Sharia Board</div>
                            </div>
                        </td>
                        {gcc_logo_html}
                        <td class="sig-cell-right" style="width: {sig_cell_width};">
                            <div class="signature-block">
                                <img class="signature-img" src="babar.png" alt="Signature">
                                <div class="signature-name">Babar Iqbal</div>
                                <div class="signature-title">CEO</div>
                            </div>
                        </td>
                    </tr>
                </table>

                <div class="bottom-footer">
                    <div class="dates-section">
                        <div class="date-line"><span class="label">Original Approval Date:</span> <span class="value">{original_approval_date_long}</span></div>
                        <div class="date-line"><span class="label">Current Cycle Start Date:</span> <span class="value">{current_cycle_start_date_long}</span></div>
                        <div class="date-line"><span class="label">Expiry Date:</span> <span class="value">{expiry_date_long}</span></div>
                    </div>
                    <div class="validity-text">{validity_text}</div>
                    <div class="recognition-text">HCO is recognised by GSO & SMIIC (GAC), SFDA, SASO, MOIAT, MOPH (Qatar), MUIS(Singapore), CICOT (Thailand), IMANOR (Morocco) & has other collaborations globally.</div>
                    <div class="company-details">Halal Certification Organisation Limited, 34 Mornington Road, Birmingham, West Midlands, B66 2JE</div>
                    <div class="contact-details">T: +44 (0)333 5770902 E: info@hcoltd.co.uk</div>
                    <div class="website">www.hcoltd.co.uk</div>
                    <div
            style="
              text-align: center;
              font-size: 9px;
              color: #555;
              margin: 8px 0;
              font-style: italic;
              display: flex;
              gap: 10px;
              justify-content: space-between;
              align-items: center;
              width: 100%;
            "
          >
            <p>{cert_num_footer_safe}</p>
            <p>Reg No. 10321924</p>
            <p>VAT No. 273 575 085</p>
            <p>Page {page_number} of {total_pages}</p>
          </div>
                    <div class="verification-section">
                        <img class="qr-code" src="qr.png" alt="QR Code">
                        <div class="verification-text">
                            To verify this certificate (Certificate No: {certificate_no}), please scan the QR code<br>
                            or visit <a href="https://www.hcoltd.co.uk/certificatevalidation">www.hcoltd.co.uk/certificatevalidation</a>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>"""

    return html_template


def generate_annex_pages_html(
    certificate_no: str,
    company_name: str,
    company_reg_no: str,
    issue_date: str,
    expiry_date: str,
    standards: str,
    products: List[Dict[str, Any]],
    validity_period: str = "3",
    cert_num_footer: str = "",
    annex_layout_options: Optional[Dict[str, Any]] = None,
    watermark: bool = True,
    domestic_logo_1: str = "gac",
    domestic_logo_2: str = "none",
) -> List[str]:
    """Generate annex pages HTML for products"""

    # Create dynamic validity text based on validity_period
    validity_years = validity_period if validity_period else "3"
    try:
        validity_int = int(validity_years)
    except ValueError:
        validity_int = 3

    validity_text = ""
    if validity_int >= 3:
        validity_text = f"(The certificate validity is {validity_years} year{'s' if validity_years != '1' else ''}, subject to annual surveillance audits)"

    cert_num_footer_safe = html.escape((cert_num_footer or "").strip())

    logo_1_html = _build_export_logo_html(domestic_logo_1)
    logo_2_html = _build_export_logo_html(domestic_logo_2)
    logo_parts = [h for h in [logo_1_html, logo_2_html] if h]
    if logo_parts:
        logos_joined = '&nbsp;&nbsp;'.join(logo_parts)
        gcc_logo_html = f'<td class="sig-cell-center" style="text-align: center; vertical-align: middle; width: 34%;">{logos_joined}</td>'
        sig_cell_width = "33%"
    else:
        gcc_logo_html = ""
        sig_cell_width = "50%"

    print(f"🔍 Annex generation - received {len(products)} products")
    if products:
        print(f"📋 Sample product: {products[0]}")
    
    if not products:
        print("⚠️  No products found - skipping annex generation")
        return []

    def _extract_product_code_and_name(product: Any) -> tuple[str, str]:
        product_name = ""
        product_code = ""

        if isinstance(product, dict):
            if 'product_code' in product:
                product_code = str(product['product_code']).strip()
            if 'product_name' in product:
                product_name = str(product['product_name']).strip()

            if not product_code or not product_name:
                for key, value in product.items():
                    key_lower = str(key).lower()
                    if 'name' in key_lower or 'product' in key_lower or 'description' in key_lower:
                        product_name = str(value).strip()
                    elif 'code' in key_lower or 'sku' in key_lower or key_lower in {'id', 'item_id', 'product_id'}:
                        candidate = str(value).strip()
                        if candidate and any(ch.isalnum() for ch in candidate) and ' ' not in candidate:
                            product_code = candidate

            if len(product) == 1 and not product_name:
                only_key = list(product.keys())[0]
                only_val = list(product.values())[0]
                only_key_lower = str(only_key).lower()
                if 'name' in only_key_lower or 'product' in only_key_lower or 'description' in only_key_lower:
                    product_name = str(only_val).strip()
                else:
                    product_name = str(only_val).strip()
                product_code = ""

        return product_code, product_name

    total_products = len(products)

    extracted_pairs = [_extract_product_code_and_name(p) for p in products]
    has_any_product_code = any(bool(code) for code, _ in extracted_pairs)

    requested_products_per_page = None
    requested_rows = None
    requested_columns = None
    if isinstance(annex_layout_options, dict):
        requested_products_per_page = annex_layout_options.get("products_per_page")
        requested_rows = annex_layout_options.get("rows")
        requested_columns = annex_layout_options.get("columns")

    def _safe_int(value: Any) -> Optional[int]:
        try:
            if value is None:
                return None
            return int(value)
        except Exception:
            return None

    requested_products_per_page_int = _safe_int(requested_products_per_page)
    requested_rows_int = _safe_int(requested_rows)
    requested_columns_int = _safe_int(requested_columns)

    if not has_any_product_code:
        annex_layout = "name_only"

        if requested_columns_int and requested_columns_int > 0:
            name_columns = requested_columns_int
        else:
            if total_products > 60:
                name_columns = 4
            elif total_products > 40:
                name_columns = 3
            else:
                name_columns = 3

        if requested_rows_int and requested_rows_int > 0:
            rows_per_column = requested_rows_int
        else:
            rows_per_column = 10

        products_per_page = name_columns * rows_per_column
    else:
        # If product codes exist, always print Product Code + Product Name in Annex A.
        # Use 2-column table for smaller product lists; switch to 4-column (two-up) only for larger lists.

        has_any_packaging = any(
            isinstance(p, dict) and bool(str(p.get("packaging_details", "")).strip())
            for p in products
        )

        if requested_columns_int and requested_columns_int == 3:
            annex_layout = "code_name_packaging"
        elif has_any_packaging and (not requested_columns_int or requested_columns_int == 3):
            annex_layout = "code_name_packaging"
        elif requested_columns_int and requested_columns_int >= 4:
            annex_layout = "code_name_4col"
        elif requested_columns_int and requested_columns_int == 2:
            annex_layout = "code_name_2col"
        else:
            if total_products > 60:
                annex_layout = "code_name_4col"
            else:
                annex_layout = "code_name_2col"

        if requested_products_per_page_int and requested_products_per_page_int > 0:
            products_per_page = requested_products_per_page_int
        else:
            if annex_layout == "code_name_packaging":
                products_per_page = 10
            elif annex_layout == "code_name_4col":
                products_per_page = 20
            else:
                products_per_page = 10

        name_columns = 0
        rows_per_column = 0

    total_pages = (total_products + products_per_page - 1) // products_per_page
    annex_pages = []

    # ANNEX_STYLE_CONFIG controls ALL Annex table sizing.
    #
    # How it works:
    # - Pick a "bucket" based on total number of products in the annex (total_products).
    # - Within that bucket, pick a layout style based on annex_layout:
    #   - "code_name_2col": 2-column table (Product Code | Product Name)
    #   - "code_name_4col": 4-column table (Code/Name + Code/Name) (two products per row)
    #   - "name_only": product name only (multi-column)
    # - Styles are selected only from the buckets below (based on total_products).
    # - Finally clamp values to safe min/max.
    #
    # Units:
    # - cell_fs/header_fs are in pixels (px)
    # - pad_y/pad_x are in pixels (px)
    ANNEX_STYLE_CONFIG: Dict[str, Any] = {
        "buckets": [
            {
                # 121+ products: smallest sizing to avoid footer overlap on dense annex pages.
                "min": 121,
                "max": 10**9,
                "styles": {
                    # cell_fs: <td> font size, header_fs: <th> font size
                    # pad_y: vertical cell padding (top/bottom), pad_x: horizontal padding (left/right)
                    "code_name_4col": {"cell_fs": 12, "header_fs": 13, "pad_y": 5, "pad_x": 5},
                    "code_name_packaging": {"cell_fs": 11, "header_fs": 12, "pad_y": 4, "pad_x": 5},
                    "code_name_2col": {"cell_fs": 14, "header_fs": 15, "pad_y": 5, "pad_x": 6},
                    "name_only": {"cell_fs": 11, "header_fs": 12, "pad_y": 3, "pad_x": 3},
                },
            },
            {
                # 61-120 products: medium-small sizing.
                "min": 61,
                "max": 120,
                "styles": {
                    "code_name_4col": {"cell_fs": 12, "header_fs": 13, "pad_y": 7, "pad_x": 7},
                    "code_name_packaging": {"cell_fs": 12, "header_fs": 13, "pad_y": 5, "pad_x": 5},
                   "code_name_2col": {"cell_fs": 14, "header_fs": 15, "pad_y": 5, "pad_x": 6},
                    "name_only": {"cell_fs": 11, "header_fs": 12, "pad_y": 3, "pad_x": 3},
                },
            },
            {
                # 0-60 products: largest sizing (most readable) while still fitting above the footer.
                "min": 0,
                "max": 60,
                "styles": {
                    "code_name_4col": {"cell_fs": 9, "header_fs": 10, "pad_y": 3, "pad_x": 4},
                    "code_name_packaging": {"cell_fs": 13, "header_fs": 14, "pad_y": 5, "pad_x": 6},
                    "code_name_2col": {"cell_fs": 14, "header_fs": 15, "pad_y": 5, "pad_x": 6},
                    "name_only": {"cell_fs": 10, "header_fs": 11, "pad_y": 3, "pad_x": 3},
                },
            },
        ],
        "clamp": {
            # Hard limits to prevent unreadably small or excessively large values.
            "cell_fs": {"min": 5, "max": 18},
            "header_fs": {"min": 7, "max": 22},
            "pad_y": {"min": 1, "max": 12},
            "pad_x": {"min": 2, "max": 12},
        },
    }

    def _compute_page_table_style(
        *,
        total_products: int,
        annex_layout: str,
        page_products: List[Dict[str, Any]]
    ) -> tuple[int, int, int, int]:
        page_pairs = [_extract_product_code_and_name(p) for p in page_products]
        max_code_len = max((len(code or "") for code, _ in page_pairs), default=0)
        max_name_len = max((len(name or "") for _, name in page_pairs), default=0)
        page_count = len(page_products)

        bucket = next(
            (
                b
                for b in ANNEX_STYLE_CONFIG["buckets"]
                if b["min"] <= total_products <= b["max"]
            ),
            ANNEX_STYLE_CONFIG["buckets"][-1],
        )

        styles_for_layout = bucket["styles"].get(annex_layout) or bucket["styles"].get("name_only")
        cell_fs = int(styles_for_layout["cell_fs"])
        header_fs = int(styles_for_layout["header_fs"])
        pad_y = int(styles_for_layout["pad_y"])
        pad_x = int(styles_for_layout["pad_x"])

        clamp = ANNEX_STYLE_CONFIG["clamp"]
        cell_fs = max(int(clamp["cell_fs"]["min"]), min(int(clamp["cell_fs"]["max"]), cell_fs))
        header_fs = max(int(clamp["header_fs"]["min"]), min(int(clamp["header_fs"]["max"]), header_fs))
        pad_y = max(int(clamp["pad_y"]["min"]), min(int(clamp["pad_y"]["max"]), pad_y))
        pad_x = max(int(clamp["pad_x"]["min"]), min(int(clamp["pad_x"]["max"]), pad_x))

        return cell_fs, header_fs, pad_y, pad_x
    
    for page_idx in range(total_pages):
        hco_logo_data_uri = _get_hco_logo_data_uri()
        start_idx = page_idx * products_per_page
        end_idx = min(start_idx + products_per_page, len(products))
        page_products = products[start_idx:end_idx]

        (
            table_cell_font_size_px,
            table_header_font_size_px,
            table_cell_padding_y_px,
            table_cell_padding_x_px,
        ) = _compute_page_table_style(
            total_products=total_products,
            annex_layout=annex_layout,
            page_products=page_products,
        )

        print(
            f"📐 Annex style applied: layout={annex_layout}, total_products={total_products}, "
            f"page_products={len(page_products)}, cell_fs={table_cell_font_size_px}px, "
            f"header_fs={table_header_font_size_px}px, pad_y={table_cell_padding_y_px}px, pad_x={table_cell_padding_x_px}px"
        )
        
        annex_letter = 'A'  # Always use Annex A for all pages

        print(
            f"📋 Annex {annex_letter} (Page {page_idx + 1}): Adding {len(page_products)} products "
            f"(layout={annex_layout}, per_page={products_per_page})"
        )

        product_rows = ""
        products_table_head = ""

        if annex_layout == "code_name_packaging":
            products_table_head = f"""
                        <tr>
                            <th style=\"font-size: {table_header_font_size_px}px;\">Product Code</th>
                            <th style=\"font-size: {table_header_font_size_px}px;\">Product Name</th>
                            <th style=\"font-size: {table_header_font_size_px}px;\">Packaging Details</th>
                        </tr>"""

            for i, product in enumerate(page_products):
                product_code, product_name = _extract_product_code_and_name(product)
                packaging = ""
                if isinstance(product, dict):
                    packaging = str(product.get("packaging_details", "")).strip()

                product_rows += f"""
            <tr>
                <td class=\"code-cell\" style=\"font-size: {table_cell_font_size_px}px; line-height: 1.15; padding: {table_cell_padding_y_px}px {table_cell_padding_x_px}px;\">{product_code if product_code else 'N/A'}</td>
                <td class=\"name-cell\" style=\"font-size: {table_cell_font_size_px}px; line-height: 1.15; padding: {table_cell_padding_y_px}px {table_cell_padding_x_px}px;\">{product_name if product_name else 'N/A'}</td>
                <td class=\"packaging-cell\" style=\"font-size: {table_cell_font_size_px}px; line-height: 1.15; padding: {table_cell_padding_y_px}px {table_cell_padding_x_px}px;\">{packaging}</td>
            </tr>"""

        elif annex_layout == "code_name_4col":
            products_table_head = f"""
                        <tr>
                            <th style=\"font-size: {table_header_font_size_px}px;\">Product Code</th>
                            <th style=\"font-size: {table_header_font_size_px}px;\">Product Name</th>
                            <th style=\"font-size: {table_header_font_size_px}px;\">Product Code</th>
                            <th style=\"font-size: {table_header_font_size_px}px;\">Product Name</th>
                        </tr>"""

            for row_start in range(0, len(page_products), 2):
                left_code, left_name = _extract_product_code_and_name(page_products[row_start])
                right_code, right_name = ("", "")
                if row_start + 1 < len(page_products):
                    right_code, right_name = _extract_product_code_and_name(page_products[row_start + 1])

                product_rows += f"""
            <tr>
                <td class=\"code-cell\" style=\"font-size: {table_cell_font_size_px}px; line-height: 1.05; padding: {table_cell_padding_y_px}px {table_cell_padding_x_px}px;\">{left_code if left_code else 'N/A'}</td>
                <td class=\"name-cell\" style=\"font-size: {table_cell_font_size_px}px; line-height: 1.05; padding: {table_cell_padding_y_px}px {table_cell_padding_x_px}px;\">{left_name if left_name else 'N/A'}</td>
                <td class=\"code-cell\" style=\"font-size: {table_cell_font_size_px}px; line-height: 1.05; padding: {table_cell_padding_y_px}px {table_cell_padding_x_px}px;\">{right_code if right_code else ''}</td>
                <td class=\"name-cell\" style=\"font-size: {table_cell_font_size_px}px; line-height: 1.05; padding: {table_cell_padding_y_px}px {table_cell_padding_x_px}px;\">{right_name if right_name else ''}</td>
            </tr>"""

        elif annex_layout == "name_only":
            products_table_head = """
                        <tr>
            """ + "".join(["<th style=\"font-size: {table_header_font_size_px}px;\">Product Name</th>".format(table_header_font_size_px=table_header_font_size_px) for _ in range(name_columns)]) + """
                        </tr>"""

            extracted_names: List[str] = []
            for product in page_products:
                _, product_name = _extract_product_code_and_name(product)
                extracted_names.append(product_name if product_name else 'N/A')

            columns: List[List[str]] = []
            for col_idx in range(name_columns):
                col_start = col_idx * rows_per_column
                col_end = min(col_start + rows_per_column, len(extracted_names))
                columns.append(extracted_names[col_start:col_end])

            for row_idx in range(rows_per_column):
                row_cells = ""
                for col_idx in range(name_columns):
                    value = columns[col_idx][row_idx] if row_idx < len(columns[col_idx]) else ""
                    row_cells += (
                        f"<td class=\"name-only-cell\" style=\"font-size: {table_cell_font_size_px}px; "
                        f"line-height: 1.05; padding: {table_cell_padding_y_px}px {table_cell_padding_x_px}px;\">{value}</td>"
                    )
                product_rows += f"""
            <tr>
                {row_cells}
            </tr>"""

        else:
            products_table_head = f"""
                        <tr>
                            <th style=\"font-size: {table_header_font_size_px}px;\">Product Code</th>
                            <th style=\"font-size: {table_header_font_size_px}px;\">Product Name</th>
                        </tr>"""

            for i, product in enumerate(page_products):
                product_number = start_idx + i + 1
                product_code, product_name = _extract_product_code_and_name(product)

                print(f"Processing product {product_number}: code='{product_code}', name='{product_name}'")
                print(f"Original product data: {product}")

                product_rows += f"""
            <tr>
                <td class=\"code-cell\" style=\"font-size: {table_cell_font_size_px}px; line-height: 1.15; padding: {table_cell_padding_y_px}px {table_cell_padding_x_px}px;\">{product_code if product_code else 'N/A'}</td>
                <td class=\"name-cell\" style=\"font-size: {table_cell_font_size_px}px; line-height: 1.15; padding: {table_cell_padding_y_px}px {table_cell_padding_x_px}px;\">{product_name if product_name else 'N/A'}</td>
            </tr>"""
        
        annex_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Halal Certificate Annex {annex_letter}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        @page {{
            size: A4;
            margin: 0;
        }}

        body {{
            font-family: 'Georgia', 'Times New Roman', serif;
            background-color: #ffffff;
            padding: 0;
            margin: 0;
        }}

        .certificate-container {{
            width: 210mm;
            height: 297mm;
            margin: 0 auto;
            background: #ffffff;
            border: 6px solid #0a2b20;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
            padding: 12mm;
            position: relative;
            overflow: hidden;
            page-break-inside: avoid;
            page-break-before: always;
            box-sizing: border-box;
        }}

        .content-wrapper {{
            position: relative;
            z-index: 2;
            height: 100%;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }}

        .annex-main {{
            flex: 1 1 auto;
            min-height: 0;
        }}

        .certificate-container::before {{
            content: "";
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-image: url('{hco_logo_data_uri}');
            background-repeat: no-repeat;
            background-position: center;
            background-size: 65% auto;
            opacity: 0.13;
            pointer-events: none;
            z-index: 0;
        }}

        /* Decorative corner elements */
        .corner-decoration {{
            position: absolute;
            width: 60px;
            height: 60px;
            border: 2px solid #90c850;
        }}

        .corner-decoration.top-left {{
            top: 15px;
            left: 15px;
            border-right: none;
            border-bottom: none;
        }}

        .corner-decoration.top-right {{
            top: 15px;
            right: 15px;
            border-left: none;
            border-bottom: none;
        }}

        .corner-decoration.bottom-left {{
            bottom: 15px;
            left: 15px;
            border-right: none;
            border-top: none;
        }}

        .corner-decoration.bottom-right {{
            bottom: 15px;
            right: 15px;
            border-left: none;
            border-top: none;
        }}

        /* Subtle pattern overlay */
        .pattern-overlay {{
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            opacity: 0.015;
            background-image:
                repeating-linear-gradient(45deg, transparent, transparent 40px, #1a4d3a 40px, #1a4d3a 41px);
            pointer-events: none;
            z-index: 0;
        }}

        .title {{
            font-size: 28px;
            font-weight: 400;
            color: #1a4d3a;
            letter-spacing: 4px;
            margin-bottom: 6px;
            text-transform: uppercase;
            font-family: 'Georgia', serif;
        }}

        .cert-header-row {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin: 10px 20px 4px 20px;
        }}

        .issue-date {{
            font-size: 10px;
            color: #1a4d3a;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-weight: 700;
            text-align: left;
            margin: 0;
            padding-top: 2px;
        }}

        .cert-info {{
            text-align: right;
            font-size: 10px;
            color: #333;
            font-family: 'Arial', sans-serif;
            margin: 0;
        }}

        .cert-info-item {{
            padding: 1px 0;
            line-height: 1.4;
        }}

        .cert-info-item .label {{
            font-weight: 700;
            color: #1a4d3a;
        }}

        .company-info {{
            text-align: center;
            margin: 8px 0;
            padding: 6px 40px;
            align-self: stretch;
            width: 100%;
        }}

        .company-line {{
            font-size: 16px;
            font-weight: 600;
            color: #1a4d3a;
            margin: 4px auto;
            padding: 4px 0;
            border-bottom: 2px solid #1a4d3a;
            width: 65%;
            letter-spacing: 0.5px;
        }}

        .company-reg-display {{
            font-size: 9px;
            margin: 4px auto;
            font-style: italic;
            color: #777;
            font-weight: 400;
        }}

        .annex-title {{
            font-weight: 700;
            font-size: 22px;
            text-align: center;
            margin: 10px auto;
            padding: 8px 30px;
            color: #1a4d3a;
            letter-spacing: 2px;
            text-transform: uppercase;
            border-top: 2px solid #1a4d3a;
            border-bottom: 2px solid #1a4d3a;
            width: 40%;
            display: block;
            box-sizing: border-box;
            font-family: 'Georgia', serif;
        }}

        .products-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 10px 0;
            font-family: 'Arial', sans-serif;
            align-self: stretch;
        }}

        .products-table th {{
            background: #1a4d3a;
            color: white;
            padding: 4px 6px;
            text-align: center;
            font-weight: 600;
            font-size: {table_header_font_size_px}px;
            text-transform: uppercase;
            letter-spacing: 1px;
            border: 1px solid #0a2b20;
        }}

        .products-table td {{
            border: 1px solid #464646;
            padding: {table_cell_padding_y_px}px {table_cell_padding_x_px}px;
            background: white;
            font-size: {table_cell_font_size_px}px;
            line-height: 1.15;
            color: #444;
        }}

        .products-table.products-table--code_name_4col td {{
            padding: {table_cell_padding_y_px}px {table_cell_padding_x_px}px;
            line-height: 1.1;
            font-size: {table_cell_font_size_px}px;
        }}

        .products-table tr {{
            page-break-inside: avoid;
        }}

        .products-table.products-table--2col td:first-child {{
            text-align: center;
            width: 30%;
            font-weight: 600;
            background: #fafafa;
            color: #1a4d3a;
        }}

        .products-table.products-table--code_name_2col td:first-child {{
            text-align: center;
            width: 30%;
            font-weight: 600;
            background: #fafafa;
            color: #1a4d3a;
        }}

        .products-table.products-table--code_name_2col td:nth-child(2) {{
            width: 70%;
            text-align: left;
        }}

        .products-table.products-table--code_name_packaging td:first-child {{
            text-align: center;
            width: 20%;
            font-weight: 600;
            background: #fafafa;
            color: #1a4d3a;
        }}

        .products-table.products-table--code_name_packaging td:nth-child(2) {{
            width: 45%;
            text-align: left;
        }}

        .products-table.products-table--code_name_packaging td:nth-child(3) {{
            width: 35%;
            text-align: left;
        }}

        .products-table td.code-cell {{
            text-align: center;
            font-weight: 600;
            background: #fafafa;
            color: #1a4d3a;
            width: 20%;
        }}

        .products-table td.name-cell {{
            text-align: left;
            width: 30%;
        }}

        .products-table td.packaging-cell {{
            text-align: left;
        }}

        .products-table td.name-only-cell {{
            text-align: left;
            width: 25%;
        }}

        /* Signature row (use table layout for consistent PDF rendering) */
        .signature-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 14px;
            page-break-inside: avoid;
        }}

        .signature-table td {{
            vertical-align: bottom;
            width: 50%;
        }}

        .sig-cell-left {{
            text-align: left;
            padding-left: 40px;
        }}

        .sig-cell-right {{
            text-align: right;
            padding-right: 40px;
        }}

        .signature-block {{
            display: inline-block;
            width: 150px;
            text-align: center;
        }}

        .signature-img {{
            width: 70px;
            height: auto;
            display: block;
            margin: 0 auto 4px;
        }}

        .signature-logo {{
            width: 80px;
            height: 50px;
            background: #1a4d3a;
            border-radius: 4px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: 600;
            margin: 0 auto 8px;
            font-size: 16px;
            letter-spacing: 1px;
            font-family: 'Arial', sans-serif;
        }}

        .signature-line {{
            width: 100px;
            height: 1px;
            background: #333;
            margin: 0 auto 4px;
        }}

        .signature-name {{
            font-style: normal;
            font-size: 9px;
            margin-bottom: 2px;
            color: #1a4d3a;
            font-weight: 600;
        }}

        .signature-title {{
            font-size: 8px;
            color: #777;
            font-weight: 400;
        }}

        .annex-footer {{
            flex: 0 0 auto;
            padding-top: 8px;
            margin-top: auto;
        }}

        .bottom-footer {{
            margin-top: 6px;
            text-align: center;
            font-family: 'Arial', sans-serif;
            padding-top: 6px;
        }}

        .validity-text {{
            font-size: 8px;
            color: #666;
            margin: 4px 0;
            font-style: italic;
        }}

        .recognition-text {{
            font-size: 6px;
            color: #333;
            font-weight: 600;
            margin: 4px 0;
            white-space: nowrap;
        }}

        .company-details {{
            font-size: 7px;
            color: #333;
            margin: 3px 0;
            line-height: 1.3;
        }}

        .contact-details {{
            font-size: 7px;
            color: #333;
            margin: 3px 0;
        }}

        .website {{
            font-size: 8px;
            color: #90c850;
            font-weight: 700;
            letter-spacing: 0.5px;
            margin-top: 3px;
        }}

        .footer-meta-table {{
            display: flex;
            justify-content: space-between;
            width: 100%;
            border-collapse: collapse;
            margin: 6px 0 2px 0;
            font-family: 'Arial', sans-serif;
            font-size: 7px;
            color: #555;
            font-style: normal;
            line-height: 1.2;
            table-layout: fixed;
        }}

        .footer-meta-table td {{
            padding: 0;
            vertical-align: top;
            white-space: nowrap;
        }}

        .footer-meta-table .footer-cert {{
            width: 15%;
            text-align: left;
            overflow: hidden;
            text-overflow: ellipsis;
        }}

        .footer-meta-table .footer-reg {{
            width: 35%;
            text-align: center;
        }}

        .footer-meta-table .footer-vat {{
            width: 30%;
            text-align: center;
        }}

        .footer-meta-table .footer-page {{
            width: 20%;
            text-align: right;
        }}

        .verification-section {{
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 4px 0 2px 0;
            padding: 4px 0;
            border-top: 1px solid #ddd;
        }}

        .qr-code {{
            width: 35px;
            height: 35px;
            margin-right: 8px;
        }}

        .verification-text {{
            font-size: 6px;
            color: #555;
            text-align: left;
            line-height: 1.4;
        }}

        .verification-text a {{
            color: #1a4d3a;
            text-decoration: none;
            font-weight: 600;
        }}

        /* Print styles */
        @media print {{
            body {{
                background-color: white;
                padding: 0;
                margin: 0;
            }}

            .certificate-container {{
                box-shadow: none;
                margin: 0;
                page-break-after: avoid;
                page-break-inside: avoid;
            }}
        }}
    </style>
</head>
<body>
    <div class="certificate-container">
        <!-- Decorative corners -->
        <div class="corner-decoration top-left"></div>
        <div class="corner-decoration top-right"></div>
        <div class="corner-decoration bottom-left"></div>
        <div class="corner-decoration bottom-right"></div>
        
        <!-- Pattern overlay -->
        <div class="pattern-overlay"></div>

        <div class="content-wrapper">
            <div class="annex-main">
                <div class="header">
                    <div class="logo-container">
                        <img class="hco-logo" src="HCO-Logo.png" alt="HCO Logo">
                    </div>
                    
                    <div class="title">Halal Certificate</div>
                    <div class="cert-header-row">
                        <div class="issue-date">Issue Date: {issue_date}</div>
                        <div class="cert-info">
                            <div class="cert-info-item"><span class="label">Certificate No:</span> {certificate_no}</div>
                            <div class="cert-info-item standard"><span class="label">Standard:</span> {standards}</div>
                        </div>
                    </div>
                
                </div>

                <div class="company-info">
                    <div class="company-line">{company_name}</div>
                    <div class="company-reg-display">(Company Register Number: {company_reg_no})</div>
                </div>

                <div class="annex-title" style="text-align: center; width: 100%; display: block; font-size: 22px; font-weight: 700; margin: 10px 0; padding: 8px 0; color: #1a4d3a; letter-spacing: 2px; text-transform: uppercase;">Annex {annex_letter}</div>

                <table class="products-table products-table--{annex_layout}">
                    <thead>
                        {products_table_head}
                    </thead>
                    <tbody>
                        {product_rows}
                    </tbody>
                </table>
            </div>

            <div class="annex-footer">
            <table class="signature-table">
                <tr>
                    <td class="sig-cell-left" style="width: {sig_cell_width};">
                        <div class="signature-block">
                            <img class="signature-img" src="khalid.png" alt="Signature">
                            <div class="signature-name">Dr Mohammad Khalid</div>
                            <div class="signature-title">Member of Sharia Board</div>
                        </div>
                    </td>
                    {gcc_logo_html}
                    <td class="sig-cell-right" style="width: {sig_cell_width};">
                        <div class="signature-block">
                            <img class="signature-img" src="babar.png" alt="Signature">
                            <div class="signature-name">Babar Iqbal</div>
                            <div class="signature-title">CEO</div>
                        </div>
                    </td>
                </tr>
            </table>

            <div class="bottom-footer">
                <div class="validity-text">{validity_text}</div>
                <div class="recognition-text">HCO is recognised by GSO & SMIIC (GAC), SFDA, SASO, MOIAT, MOPH (Qatar), MUIS(Singapore), CICOT (Thailand), IMANOR (Morocco) & has other collaborations globally.</div>
                <div class="company-details">Halal Certification Organisation Limited, 34 Mornington Road, Birmingham, West Midlands, B66 2JE</div>
                <div class="contact-details">T: +44 (0)333 5770902 E: info@hcoltd.co.uk</div>
                <div class="website">www.hcoltd.co.uk</div>
                <div
        style="
          text-align: center;
          font-size: 9px;
          color: #555;
          margin: 8px 0;
          font-style: italic;
          display: flex;
          gap: 10px;
          justify-content: space-between;
          align-items: center;
          width: 100%;
        "
      >
        <p>{cert_num_footer_safe}</p>
        <p>Reg No. 10321924</p>
        <p>VAT No. 273 575 085</p>
        <p>Page {page_idx + 2} of {total_pages + 1}</p>
      </div>
                <div class="verification-section">
                    <img class="qr-code" src="qr.png" alt="QR Code">
                    <div class="verification-text">
                        To verify this certificate, please scan the QR code<br>
                        or visit <a href="https://www.hcoltd.co.uk/certificatevalidation">www.hcoltd.co.uk/certificatevalidation</a>
                    </div>
                </div>
            </div>
        </div>
        </div>
    </div>
</body>
</html>"""

        annex_pages.append(annex_html)
    
    return annex_pages


def generate_certificate_with_html_templates(
    certificate_no: str,
    company_name: str,
    company_reg_no: str,
    issue_date: str,
    expiry_date: str,
    standards: str,
    company_address: str,
    pu: str = "",
    au: str = "",
    sow: str = "",
    validity_period: str = "1",
    csv_files: List = None,
    company_logo: Optional[Dict[str, Any]] = None,
    cert_num_footer: str = "",
    annex_layout_options: Optional[Dict[str, Any]] = None,
    domestic_logo_1: str = "gac",
    domestic_logo_2: str = "none",
) -> Dict[str, Any]:
    """
    Generate certificate using HTML templates
    """
    import csv
    from datetime import datetime
    
    try:
        # Process CSV files to get products
        products = []
        print(f"🔍 Processing {len(csv_files) if csv_files else 0} CSV files")
        excel_extracted_name_only = False
        if csv_files:
            for csv_file in csv_files:
                try:
                    filename = csv_file.filename.lower()
                    
                    if filename.endswith('.xlsx') or filename.endswith('.xls'):
                        # Handle Excel files using the new generic OpenAI-powered extraction
                        try:
                            # Get binary content for Excel files
                            content = csv_file.read()
                            if not isinstance(content, bytes):
                                print(f"Warning: Expected binary content for Excel file, got {type(content)}")
                                if isinstance(content, str):
                                    content = content.encode('utf-8')
                            
                            print(f"Processing Excel file: {csv_file.filename}, content size: {len(content)} bytes")

                            def _normalize_excel_name(value: str) -> str:
                                return ''.join(ch for ch in (value or '').lower() if ch.isalnum())

                            pandas_products = []
                            pandas_name_only = False
                            try:
                                import pandas as pd
                                xl = pd.ExcelFile(io.BytesIO(content))
                                sheet_map = {_normalize_excel_name(s): s for s in xl.sheet_names}
                                target_candidates = [
                                    _normalize_excel_name('final producsts names'),
                                    _normalize_excel_name('final products names'),
                                    _normalize_excel_name('final product names'),
                                ]

                                sheet_to_use = None
                                for cand in target_candidates:
                                    if cand in sheet_map:
                                        sheet_to_use = sheet_map[cand]
                                        break

                                if sheet_to_use:
                                    raw_df = pd.read_excel(io.BytesIO(content), sheet_name=sheet_to_use, header=None)

                                    header_row_idx = None
                                    for i in range(min(60, len(raw_df))):
                                        row_values = [
                                            str(v).replace('\n', ' ').strip()
                                            for v in raw_df.iloc[i].tolist()
                                            if str(v).strip() and str(v).strip().lower() != 'nan'
                                        ]
                                        row_norm = ' '.join(row_values).lower()
                                        if 'product code' in row_norm and 'product name' in row_norm:
                                            header_row_idx = i
                                            break

                                    if header_row_idx is None:
                                        header_row_idx = 0

                                    # Build the dataframe from the detected header row explicitly.
                                    header_values = [str(v).replace('\n', ' ').strip() for v in raw_df.iloc[header_row_idx].tolist()]
                                    df = raw_df.iloc[header_row_idx + 1:].copy()
                                    df.columns = header_values
                                    df = df.dropna(how='all')

                                    # Normalize column names (remove newlines, trim)
                                    df.columns = [str(c).replace('\n', ' ').strip() for c in df.columns]

                                    if df.shape[1] > 0:
                                        col_norm = {_normalize_excel_name(str(c)): str(c) for c in df.columns}

                                        name_col = None
                                        code_col = None
                                        packaging_col = None

                                        # Prefer exact "productcode" / "productname" matches if present
                                        for norm, original in col_norm.items():
                                            if norm == 'productcode' or norm.endswith('productcode'):
                                                code_col = original
                                            if norm == 'productname' or norm.endswith('productname'):
                                                name_col = original
                                            if norm in ('packagingdetails', 'packaging', 'packagingdetail', 'packingdetails', 'packing'):
                                                packaging_col = original

                                        # Otherwise fallback to fuzzy detection
                                        for norm, original in col_norm.items():
                                            if name_col is None and ('name' in norm or 'productname' in norm or norm.endswith('product')):
                                                name_col = original
                                            if code_col is None and ('code' in norm or 'sku' in norm or norm.endswith('id')):
                                                code_col = original
                                            if packaging_col is None and ('packaging' in norm or 'packing' in norm):
                                                packaging_col = original

                                        if name_col is None:
                                            name_col = list(df.columns)[0]

                                        if code_col and code_col != name_col:
                                            use_cols = [code_col, name_col]
                                            if packaging_col and packaging_col not in use_cols:
                                                use_cols.append(packaging_col)

                                            cleaned = df[use_cols].copy()
                                            cleaned[code_col] = cleaned[code_col].fillna('').astype(str).map(lambda x: x.strip())
                                            cleaned[name_col] = cleaned[name_col].fillna('').astype(str).map(lambda x: x.strip())
                                            if packaging_col:
                                                cleaned[packaging_col] = cleaned[packaging_col].fillna('').astype(str).map(lambda x: x.strip())

                                            cleaned = cleaned[(cleaned[name_col] != '') & (cleaned[name_col].str.lower() != 'nan')]
                                            cleaned = cleaned[(cleaned[code_col] != '') & (cleaned[code_col].str.lower() != 'nan')]

                                            for _, row in cleaned.iterrows():
                                                product_entry: Dict[str, str] = {
                                                    'product_code': str(row[code_col]).strip(),
                                                    'product_name': str(row[name_col]).strip(),
                                                }
                                                if packaging_col:
                                                    product_entry['packaging_details'] = str(row[packaging_col]).strip()
                                                pandas_products.append(product_entry)
                                        else:
                                            pandas_name_only = True
                                            cleaned = df[[name_col]].copy()
                                            cleaned[name_col] = cleaned[name_col].fillna('').astype(str).map(lambda x: x.strip())
                                            cleaned = cleaned[(cleaned[name_col] != '') & (cleaned[name_col].str.lower() != 'nan')]
                                            for _, row in cleaned.iterrows():
                                                pandas_products.append({
                                                    'product_name': str(row[name_col]).strip(),
                                                })
                                else:
                                    print("⚠️  Pandas: target sheet 'final producsts names' not found; falling back")
                            except ImportError:
                                print("⚠️  Pandas not installed; falling back to OpenAI extraction")
                            except Exception as pandas_error:
                                print(f"⚠️  Pandas Excel parsing failed: {pandas_error}; falling back")

                            if pandas_products:
                                products.extend(pandas_products)
                                excel_extracted_name_only = excel_extracted_name_only or pandas_name_only
                                print(f"✅ Pandas extracted {len(pandas_products)} products from sheet (name_only={pandas_name_only})")
                                continue
                            
                            # Use the new generic process_files_with_openai function
                            from agent import process_files_with_openai
                            
                            # Prepare file data for processing
                            file_data = {
                                'filename': csv_file.filename,
                                'content': content
                            }
                            
                            # Extract products using the new generic method
                            extracted_products = process_files_with_openai([file_data])
                            
                            print(f"Extracted {len(extracted_products)} products from {csv_file.filename}")
                            
                            # Convert to the expected format
                            for product in extracted_products:
                                if 'product_code' in product and 'product_name' in product:
                                    code_str = str(product['product_code']).strip()
                                    name_str = str(product['product_name']).strip()
                                    
                                    # Create product dictionary in expected format
                                    product_dict = {'product_code': code_str, 'product_name': name_str}
                                    products.append(product_dict)
                                    print(f"✅ Extracted: {code_str} -> {name_str}")
                                else:
                                    print(f"⚠️  Skipping invalid product: {product}")
                            
                            print(f"Successfully extracted {len(extracted_products)} products using OpenAI")
                                    
                        except Exception as e:
                            print(f"Error processing Excel file {csv_file.filename}: {e}")
                            print("Excel file processing failed, will continue without products")
                    
                    else:
                        # Handle CSV files
                        content = csv_file.read()
                        if isinstance(content, bytes):
                            content = content.decode('utf-8')
                        
                        csv_file.seek(0)
                        
                        # Try common delimiters instead of sniffing
                        delimiters = [',', ';', '\t', '|']
                        success = False
                        
                        for delimiter in delimiters:
                            try:
                                lines = content.splitlines()
                                if lines:
                                    reader = csv.DictReader(lines, delimiter=delimiter)
                                    temp_products = []
                                    
                                    for row in reader:
                                        product = {}
                                        for key, value in row.items():
                                            if key and value:
                                                product[key.strip()] = str(value).strip()
                                        if product:
                                            temp_products.append(product)
                                    
                                    if temp_products:
                                        products.extend(temp_products)
                                        success = True
                                        break
                                        
                            except Exception:
                                continue
                        
                        if not success:
                            print(f"Could not parse CSV file {csv_file.filename} with any delimiter")
                            
                except Exception as e:
                    print(f"Error processing file {csv_file.filename}: {e}")
        
        # Generate certificate ID
        certificate_id = f"{certificate_no}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Format PU/AU text
        pu_au_text = ""
        if pu:
            pu_au_text = f"On basis of PU: {pu}"
        elif au:
            pu_au_text = f"On basis of AU: {au}"
        
        print(f"📊 Total products processed: {len(products)}")
        
        # TEMPORARY: Add sample products for testing if no products were extracted
        if len(products) == 0:
            print("⚠️  No products extracted from files, adding sample products for testing...")
            sample_products = [
                {'product_code': 'TEST001', 'product_name': 'Sample Product 1'},
                {'product_code': 'TEST002', 'product_name': 'Sample Product 2'},
                {'product_code': 'TEST003', 'product_name': 'Sample Product 3'},
                {'product_code': 'TEST004', 'product_name': 'Sample Product 4'},
                {'product_code': 'TEST005', 'product_name': 'Sample Product 5'},
                {'product_code': 'TEST006', 'product_name': 'Sample Product 6'},
                {'product_code': 'TEST007', 'product_name': 'Sample Product 7'},
                {'product_code': 'TEST008', 'product_name': 'Sample Product 8'},
            ]
            products.extend(sample_products)
            print(f"✅ Added {len(sample_products)} sample products for testing (will generate {(len(sample_products) + 4) // 5} annex pages)")
        
        # Generate PDF using HTML templates
        pdf_data = generate_html_certificate(
            certificate_no=certificate_no,
            company_name=company_name,
            company_reg_no=company_reg_no,
            issue_date=issue_date,
            expiry_date=expiry_date,
            standards=standards,
            company_address=company_address,
            pu=pu,
            au=au,
            sow=sow,
            products=products,
            company_logo=company_logo,
            validity_period=validity_period,
            cert_num_footer=cert_num_footer,
            annex_layout_options=annex_layout_options,
            domestic_logo_1=domestic_logo_1,
            domestic_logo_2=domestic_logo_2,
        )
        
        # Handle PDF generation success or failure gracefully
        pdf_generation_success = False
        final_pdf_data = None
        
        if pdf_data:
            # Check if we got HTML instead of PDF
            is_pdf = pdf_data.startswith(b'%PDF') if isinstance(pdf_data, bytes) else False
            
            if is_pdf:
                pdf_generation_success = True
                final_pdf_data = pdf_data
                print("✅ PDF generated successfully")
            else:
                # We got HTML, try to convert it using a simple method
                print("Got HTML content, attempting alternative PDF generation...")
                try:
                    # Set environment variables for library paths
                    import os
                    os.environ['DYLD_LIBRARY_PATH'] = '/opt/homebrew/lib:/usr/local/lib:' + os.environ.get('DYLD_LIBRARY_PATH', '')
                    
                    # Try to use weasyprint if available
                    from weasyprint import HTML
                    html_string = pdf_data.decode('utf-8') if isinstance(pdf_data, bytes) else pdf_data
                    final_pdf_data = HTML(string=html_string).write_pdf()
                    pdf_generation_success = True
                    print(f"✅ Generated PDF using weasyprint fallback: {len(final_pdf_data)} bytes")
                except (ImportError, Exception) as e:
                    # PDF generation failed, but we'll still save the certificate metadata
                    print(f"❌ PDF generation failed: {e}")
                    print("⚠️  Continuing without PDF - certificate metadata will be saved")
                    
                    # Save HTML file for manual conversion
                    html_filename = f"certificate_{certificate_no.replace('/', '_')}.html"
                    try:
                        with open(html_filename, 'wb') as f:
                            f.write(pdf_data)
                        print(f"📄 Saved HTML file: {html_filename}")
                    except Exception as html_error:
                        print(f"Failed to save HTML file: {html_error}")
        else:
            print("❌ No data returned from PDF generation")
            print("⚠️  Continuing without PDF - certificate will be uploaded to OneDrive")

        # Upload to OneDrive instead of database
        pdf_filename = f"certificate_{certificate_no.replace('/', '_')}.pdf"
        onedrive_success = False
        onedrive_web_url = None

        if final_pdf_data:
            try:
                from microsoft_graph import get_access_token, upload_bytes_to_shared_folder
                import os

                folder_share_url = os.getenv("HCO_ONEDRIVE_FOLDER_SHARE_URL") or os.getenv("ONEDRIVE_FOLDER_SHARE_URL")
                if folder_share_url:
                    from microsoft_graph import get_download_url_from_upload_result
                    token = get_access_token()
                    upload_result = upload_bytes_to_shared_folder(
                        folder_share_url=folder_share_url,
                        filename=pdf_filename,
                        content=final_pdf_data,
                        token=token,
                        content_type="application/pdf"
                    )
                    onedrive_success = True
                    if isinstance(upload_result, dict):
                        try:
                            # Try to get direct download URL first
                            onedrive_web_url = get_download_url_from_upload_result(upload_result, token)
                        except Exception as e:
                            # Fallback to webUrl if download URL fails
                            onedrive_web_url = upload_result.get("webUrl")
                            print(f"⚠️  Could not get direct download URL, using webUrl: {e}")
                    print(f"✅ Certificate uploaded to OneDrive: {pdf_filename}")
                    if onedrive_web_url:
                        print(f"✅ OneDrive download URL: {onedrive_web_url}")
                else:
                    print("⚠️  OneDrive not configured - certificate PDF not uploaded")
            except Exception as upload_error:
                print(f"❌ Failed to upload to OneDrive: {upload_error}")

        product_codes = [
            str(p.get("product_code", "")).strip()
            for p in products
            if isinstance(p, dict) and str(p.get("product_code", "")).strip()
        ]
        product_names = [
            str(p.get("product_name", "")).strip()
            for p in products
            if isinstance(p, dict) and str(p.get("product_name", "")).strip()
        ]

        return {
            "success": True,
            "certificate_id": certificate_id,
            "certificate_no": certificate_no,
            "num_products": len(products),
            "products": products,
            "products_code": ",".join(product_codes),
            "products_name": ",".join(product_names),
            "storage": "onedrive" if onedrive_success else "none",
            "pdf_generated": pdf_generation_success,
            "pdf_uploaded": onedrive_success,
            "pdf_bytes": final_pdf_data if pdf_generation_success else None,
            "onedrive_web_url": onedrive_web_url if onedrive_success else None,
            "message": f"Certificate generated. PDF: {'✅ Generated and uploaded' if (pdf_generation_success and onedrive_success) else '❌ Failed or not uploaded'}"
        }
        
    except Exception as e:
        print(f"Error generating HTML certificate: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def generate_meat_export_certificate_html(data: Dict[str, Any]) -> str:
    """
    Generate HTML for meat export certificate using the template.
    """
    # Read the template
    template_path = os.path.join(os.path.dirname(__file__), 'templates', 'certificate_templates', 'meat_export_certificate.html')

    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            html_template = f.read()
    except FileNotFoundError:
        print(f"Template not found at {template_path}, using inline template")
        # Fallback to inline template if file not found
        html_template = _get_meat_export_template_inline()

    # Replace placeholders with actual data
    export_logo_html = _build_export_logo_html(data.get("export_logo_option"))
    signature_block_html = _build_export_signature_block_html(data.get("export_signature_option"))

    replacements = {
        '{country_of_origin}': data.get('country_of_origin', ''),
        '{exporter_name}': data.get('exporter_name', ''),
        '{destination}': data.get('destination', ''),
        '{certificate_no}': data.get('certificate_no', ''),
        '{standard}': data.get('standards', ''),
        '{issue_date}': format_date_dmy(data.get('issue_date', '')),
        '{certificate_issue_date}': format_date_dmy(data.get('issue_date', '')),
        '{importer_name}': data.get('importer_name', ''),
        '{cert_num_footer}': html.escape((data.get('cert_num_footer', '') or '').strip()),
        '{page_number}': data.get('page_number', 1),
        '{total_pages}': data.get('total_pages', 1),
        '{slaughter_date}': format_date_dmy(data.get('slaughter_date', '')),
        '{expiry_date}': format_date_dmy(data.get('expiry_date', '')),
        '{abattoir_address}': data.get('abattoir_address', ''),
        '{gross_weight}': data.get('gross_weight', ''),
        '{number_of_carcasses}': data.get('number_of_carcasses', ''),
        '{net_weight}': data.get('net_weight', ''),
        '{number_of_boxes}': data.get('number_of_boxes', ''),
        '{batch_reference}': data.get('batch_reference', ''),
        '{halal_cert_number}': data.get('halal_cert_number', ''),
        '{vet_cert_number}': data.get('vet_cert_number', ''),
        '{destination_port}': data.get('destination_port', ''),
        '{loading_port}': data.get('loading_port', ''),
        '{flight_number}': data.get('flight_number', ''),
        '{meat_type}': data.get('meat_type', ''),
        '{awb_number}': data.get('awb_number', ''),
        '{meat_condition}': data.get('meat_condition', ''),
        '{inspector_name}': data.get('inspector_name', ''),
        '{export_logo_html}': export_logo_html,
        '{signature_block_html}': signature_block_html,
    }

    for placeholder, value in replacements.items():
        html_template = html_template.replace(placeholder, str(value) if value else '')

    return html_template


def generate_non_meat_export_certificate_html(data: Dict[str, Any]) -> str:
    """
    Generate HTML for non-meat export certificate using the template.
    """
    # Read the template
    template_path = os.path.join(os.path.dirname(__file__), 'templates', 'certificate_templates', 'non_meat_export_certificate.html')

    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            html_template = f.read()
    except FileNotFoundError:
        print(f"Template not found at {template_path}, using inline template")
        html_template = _get_non_meat_export_template_inline()

    export_logo_html = _build_export_logo_html(data.get("export_logo_option"))
    signature_block_html = _build_export_signature_block_html(data.get("export_signature_option"))

    # Replace header placeholders
    replacements = {
        '{country_of_origin}': data.get('country_of_origin', ''),
        '{destination}': data.get('destination', ''),
        '{importer_name}': data.get('importer_name', ''),
        '{exporter_name}': data.get('exporter_name', ''),
        '{certificate_no}': data.get('certificate_no', ''),
        '{standard}': data.get('standards', ''),
        '{shipment_mode}': data.get('shipment_mode', ''),
        '{invoice_no}': data.get('invoice_no', ''),
        '{vet_cert_no}': data.get('vet_health_cert_no', ''),
        '{issue_date}': format_date_dmy(data.get('issue_date', '')),
        '{cert_num_footer}': html.escape((data.get('cert_num_footer', '') or '').strip()),
        '{page_number}': data.get('page_number', 1),
        '{total_pages}': data.get('total_pages', 1),
        '{export_logo_html}': export_logo_html,
        '{signature_block_html}': signature_block_html,
    }

    for placeholder, value in replacements.items():
        html_template = html_template.replace(placeholder, str(value) if value else '')

    # Generate product table rows
    products = data.get('products_override', None)
    if products is None:
        products = data.get('products', [])
    table_rows = ""

    for product in products:
        if not product.get('description'):
            continue

        # Format dates
        mfg_date = format_date_non_meat_display(product.get('manufacture_date', ''))
        exp_date = format_date_non_meat_display(product.get('expiry_date', ''))
        date_display = f"{mfg_date} / {exp_date}" if mfg_date or exp_date else ""

        # Format weights
        gross_w = product.get('gross_weight', '')
        net_w = product.get('net_weight', '')
        weight_display = f"{gross_w} kg / {net_w} kg" if gross_w or net_w else ""

        table_rows += f"""
                <tr>
                    <td class="code-cell">{product.get('product_code', '')}</td>
                    <td class="description-cell">{product.get('description', '')}</td>
                    <td class="quantity-cell">{product.get('quantity', '')}</td>
                    <td class="date-cell">{date_display}</td>
                    <td class="batch-cell">{product.get('batch_number', '')}</td>
                    <td class="weight-cell">{weight_display}</td>
                    <td class="number-cell">{product.get('number_of_cases', '')}</td>
                </tr>"""

    html_template = html_template.replace('{table_rows}', table_rows)

    return html_template


def _get_meat_export_template_inline() -> str:
    """Inline fallback template for meat export certificate."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Halal Export Certificate - Meat</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20mm; }
        .header { text-align: center; border-bottom: 3px solid #000; padding-bottom: 15px; }
        .main-title { font-size: 36px; font-weight: bold; }
        .info-value { background-color: #00FFFF; padding: 4px 12px; font-weight: 600; }
    </style>
</head>
<body>
    <div class="header">
        <div class="main-title">HALAL EXPORT CERTIFICATE</div>
    </div>
    <p>Certificate No: {certificate_no}</p>
    <p>Country of Origin: {country_of_origin}</p>
    <p>Exporter: {exporter_name}</p>
    <p>Destination: {destination}</p>
    <p>Importer: {importer_name}</p>
    <p>Meat Type: {meat_type}</p>
    <p>Condition: {meat_condition}</p>
</body>
</html>"""


def _get_non_meat_export_template_inline() -> str:
    """Inline fallback template for non-meat export certificate."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Halal Export Certificate - Non-Meat</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20mm; }
        .header { text-align: center; border-bottom: 3px solid #000; padding-bottom: 15px; }
        .main-title { font-size: 36px; font-weight: bold; }
        .info-value { background-color: #00FFFF; padding: 4px 12px; font-weight: 600; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { border: 1px solid #000; padding: 8px; text-align: center; }
    </style>
</head>
<body>
    <div class="header">
        <div class="main-title">HALAL EXPORT CERTIFICATE</div>
    </div>
    <p>Certificate No: {certificate_no}</p>
    <p>Country of Origin: {country_of_origin}</p>
    <p>Destination: {destination}</p>
    <table>
        <thead>
            <tr><th>Code</th><th>Description</th><th>Qty</th><th>Dates</th><th>Batch</th><th>Weight</th><th>Cases</th></tr>
        </thead>
        <tbody>{table_rows}</tbody>
    </table>
</body>
</html>"""


def generate_slaughterhouse_certificate_html(
    certificate_no: str,
    company_name: str,
    company_reg_no: str,
    issue_date: str,
    expiry_date: str,
    standards: str,
    company_address: str,
    pu: str,
    au: str,
    sow: str,
    pl: str = "",  # Product List content - passed from frontend
    cert_num_footer: str = "",  # Custom footer text
    company_logo: Optional[Dict[str, Any]] = None,
    validity_period: str = "3",
) -> str:
    """
    Generate HTML for slaughterhouse certificate.
    Similar to main certificate but:
    - No Annex page (no product list)
    - No GCC logo
    - Different date format at bottom: "Expiry / Renewal Date of Certificate: 08th September 2026"
    - No Original Approval Date or Current Cycle Start Date at bottom
    """

    # Format dates
    issue_date_formatted = format_date_dmy(issue_date)
    expiry_date_long = format_date_long(expiry_date)

    validity_years = validity_period if validity_period else "3"
    try:
        validity_int = int(validity_years)
    except ValueError:
        validity_int = 3

    validity_text = ""
    if validity_int >= 3:
        validity_text = (
            f"(The certificate validity is {validity_years} year{'s' if validity_years != '1' else ''}, "
            "subject to annual surveillance audits)"
        )

    cert_num_footer_raw = (cert_num_footer or "").strip()

    # Never render this phrase on slaughterhouse certificates.
    cert_num_footer_raw = cert_num_footer_raw.replace(
        "This statement is valid only for 3-year certificates",
        "",
    ).strip()

    if validity_int < 3:
        cert_num_footer_raw = (
            cert_num_footer_raw.replace(
                "The certificate validity is 3 years, subject to annual surveillance audits",
                "",
            )
            .strip()
        )

    cert_num_footer_safe = html.escape(cert_num_footer_raw)

    hco_logo_data_uri = _get_hco_logo_data_uri()

    # Company logo (optional)
    company_logo_html = '<div class="no-logo">HCO</div>'
    try:
        if isinstance(company_logo, dict):
            logo_b64 = (company_logo.get("data") or "").strip()
            if logo_b64:
                if logo_b64.startswith("data:"):
                    logo_src = logo_b64
                else:
                    content_type = (company_logo.get("content_type") or "image/png").strip() or "image/png"
                    logo_src = f"data:{content_type};base64,{logo_b64}"
                company_logo_html = f'<img class="company-logo-img" src="{logo_src}" alt="Company Logo" />'
    except Exception:
        company_logo_html = '<div class="no-logo">HCO</div>'

    # Determine what to show for PU/AU - content must come from frontend, no fallback
    pu_au_content = ""
    section_label = "SoW"

    if pu:
        pu_au_content += f'<div class="pu-line"><strong>PU:</strong> {pu}</div>'
        section_label = "PU & SoW"
    elif au:
        pu_au_content += f'<div class="au-line"><strong>AU:</strong> {au}</div>'
        section_label = "AU & SoW"
    # No fallback to company_address - PU/AU must be provided from frontend

    pu_au_content += f'<div class="sow-line"><strong>SoW:</strong> {sow}</div>'

    # Row 1: PU/AU & SoW with company logo
    table_rows = f"""
        <tr>
            <td class="code-column">
                <div class="pu-sow-label">{section_label}</div>
                <div class="company-logo">
                    {company_logo_html}
                </div>
            </td>
            <td class="description-column">
                {pu_au_content}
            </td>
        </tr>"""

    # Row 2: PL (Product List) - content passed from frontend
    if pl:
        table_rows += f"""
        <tr>
            <td class="code-column">
                <div class="pl-label">PL</div>
                <div class="company-logo">
                    {company_logo_html}
                </div>
            </td>
            <td class="description-column">
                <div class="pl-content">{pl}</div>
            </td>
        </tr>"""

    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Slaughterhouse Halal Certificate</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        @page {{
            size: A4;
            margin: 0;
        }}

        body {{
            font-family: 'Georgia', 'Times New Roman', serif;
            background-color: #ffffff;
            padding: 0;
            margin: 0;
        }}

        .certificate-container {{
            width: 210mm;
            height: 297mm;
            margin: 0 auto;
            background: #ffffff;
            border: 6px solid #0a2b20;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
            padding: 8mm;
            position: relative;
            overflow: hidden;
            page-break-inside: avoid;
        }}

        .certificate-container::before {{
            content: "";
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-image: url('{hco_logo_data_uri}');
            background-repeat: no-repeat;
            background-position: center;
            background-size: 65% auto;
            opacity: 0.13;
            pointer-events: none;
            z-index: 0;
        }}

        .corner-decoration {{
            position: absolute;
            width: 50px;
            height: 50px;
            border: 2px solid #90c850;
        }}

        .corner-decoration.top-left {{
            top: 12px;
            left: 12px;
            border-right: none;
            border-bottom: none;
        }}

        .corner-decoration.top-right {{
            top: 12px;
            right: 12px;
            border-left: none;
            border-bottom: none;
        }}

        .corner-decoration.bottom-left {{
            bottom: 12px;
            left: 12px;
            border-right: none;
            border-top: none;
        }}

        .corner-decoration.bottom-right {{
            bottom: 12px;
            right: 12px;
            border-left: none;
            border-top: none;
        }}

        .pattern-overlay {{
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            opacity: 0.015;
            background-image:
                repeating-linear-gradient(45deg, transparent, transparent 40px, #1a4d3a 40px, #1a4d3a 41px);
            pointer-events: none;
            z-index: 0;
        }}

        .content-wrapper {{
            position: relative;
            z-index: 2;
            height: 100%;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }}

        .main-content {{
            flex: 0 0 auto;
        }}

        .header {{
            text-align: center;
            margin-bottom: 8px;
        }}

        .logo-container {{
            display: inline-block;
            margin-bottom: 5px;
        }}

        .hco-logo {{
            width: auto;
            height: 55px;
            display: block;
        }}

        .title {{
            font-size: 36px;
            font-weight: 400;
            color: #1a4d3a;
            letter-spacing: 5px;
            margin-bottom: 5px;
            text-transform: uppercase;
            font-family: 'Georgia', serif;
        }}

        .cert-header-row {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin: 14px 20px 6px 20px;
        }}

        .issue-date {{
            font-size: 10px;
            color: #1a4d3a;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-weight: 700;
            text-align: left;
            margin: 0;
            padding-top: 2px;
        }}

        .cert-info {{
            text-align: right;
            font-size: 12px;
            color: #333;
            font-family: 'Arial', sans-serif;
            margin: 0;
        }}

        .cert-info-item {{
            padding: 1px 0;
            line-height: 1.4;
        }}

        .cert-info-item .label {{
            font-weight: 700;
            color: #1a4d3a;
        }}

        .auth-text {{
            text-align: center;
            font-size: 14px;
            font-weight: 400;
            margin: 8px 0;
            color: #444;
            font-style: italic;
        }}

        .company-info {{
            text-align: center;
            margin: 8px 0;
            padding: 8px 30px;
        }}

        .company-line {{
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            font-size: 21px;
            font-weight: 600;
            color: #1a4d3a;
            margin: 6px auto;
            padding: 6px 0;
            border-bottom: 2px solid #1a4d3a;
            width: 65%;
            letter-spacing: 0.5px;
        }}

        .company-logo-head {{
            align-self: flex-start;
        }}

        .company-reg-display {{
            font-size: 10px;
            margin: 6px auto;
            font-style: italic;
            color: #777;
            font-weight: 400;
        }}

        .registered-text {{
            font-weight: 500;
            font-size: 13px;
            margin: 8px 0 6px 0;
            color: #555;
        }}

        .company-address {{
            font-size: 11px;
            margin: 6px auto;
            width: 75%;
            font-weight: 400;
            color: #555;
            line-height: 1.5;
        }}

        .description-text {{
            font-size: 10px;
            line-height: 1.6;
            margin: 8px 40px;
            text-align: center;
            color: #444;
            padding: 8px 20px;
        }}

        .section-divider {{
            border: none;
            border-top: 1px solid #ddd;
            margin: 8px 40px;
        }}

        .products-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 10px 0;
            font-family: 'Arial', sans-serif;
        }}

        .products-table th {{
            background: #1a4d3a;
            color: white;
            padding: 8px 12px;
            text-align: center;
            font-weight: 600;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 1px;
            border: 1px solid #0a2b20;
        }}

        .products-table td {{
            border: 1px solid #464646;
            padding: 10px;
            background: transparent;
        }}

        .products-table .code-column {{
            width: 30%;
            text-align: center;
            vertical-align: middle;
            background: transparent;
        }}

        .products-table .description-column {{
            width: 70%;
            text-align: left;
            vertical-align: top;
        }}

        .pu-sow-label, .pl-label {{
            font-weight: 600;
            font-size: 12px;
            margin-bottom: 6px;
            color: #1a4d3a;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .company-logo {{
            margin-top: 6px;
            text-align: center;
        }}

        .company-logo-img {{
            display: inline-block;
            max-width: 60px;
            max-height: 28px;
            width: auto;
            height: auto;
            object-fit: contain;
        }}

        .no-logo {{
            background: #1a4d3a;
            color: white;
            padding: 5px 12px;
            border-radius: 3px;
            font-size: 9px;
            font-weight: 600;
            text-align: center;
            display: inline-block;
            letter-spacing: 1.5px;
        }}

        .pu-line, .au-line, .sow-line {{
            margin-bottom: 6px;
            font-size: 11px;
            line-height: 1.4;
            color: #444;
        }}

        .pu-line strong, .au-line strong, .sow-line strong {{
            color: #1a4d3a;
            font-weight: 600;
        }}

        .pl-content {{
            font-size: 11px;
            line-height: 1.4;
            color: #444;
            overflow-wrap: anywhere;
            word-break: break-word;
        }}

        .footer-section {{
            flex: 0 0 auto;
            padding-top: 8px;
            margin-top: auto;
        }}

        .signature-table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 6px;
        }}

        .signature-table td {{
            vertical-align: bottom;
            width: 50%;
        }}

        .sig-cell-left {{
            text-align: left;
            padding-left: 30px;
        }}

        .sig-cell-right {{
            text-align: right;
            padding-right: 30px;
        }}

        .signature-block {{
            display: inline-block;
            width: 180px;
            text-align: center;
        }}

        .signature-img {{
            width: 90px;
            height: auto;
            display: block;
            margin: 0 auto 5px;
        }}

        .signature-name {{
            font-style: normal;
            font-size: 11px;
            margin-bottom: 2px;
            color: #1a4d3a;
            font-weight: 600;
        }}

        .signature-title {{
            font-size: 9px;
            color: #777;
            font-weight: 400;
        }}

        .bottom-footer {{
            text-align: center;
            font-family: 'Arial', sans-serif;
            padding-top: 4px;
        }}

        .dates-section {{
            margin-bottom: 4px;
        }}

        .date-line {{
            font-size: 11px;
            color: #000;
            margin: 2px 0;
            line-height: 1.5;
        }}

        .date-line .label {{
            font-weight: 700;
            color: #1a4d3a;
        }}

        .date-line .value {{
            font-weight: 400;
            color: #333;
        }}

        .validity-text {{
            font-size: 9px;
            color: #666;
            margin: 4px 0;
            font-style: italic;
        }}

        .recognition-text {{
            font-size: 6px;
            color: #333;
            font-weight: 600;
            margin: 4px 0;
            white-space: nowrap;
        }}

        .company-details {{
            font-size: 9px;
            color: #333;
            margin: 3px 0;
            line-height: 1.4;
        }}

        .contact-details {{
            font-size: 9px;
            color: #333;
            margin: 3px 0;
        }}

        .website {{
            font-size: 9px;
            color: #90c850;
            font-weight: 700;
            letter-spacing: 0.5px;
            margin-top: 2px;
        }}

        .verification-section {{
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 6px 0 2px 0;
            padding: 4px 0;
            border-top: 1px solid #ddd;
        }}

        .qr-code {{
            width: 45px;
            height: 45px;
            margin-right: 10px;
        }}

        .verification-text {{
            font-size: 7px;
            color: #555;
            text-align: left;
            line-height: 1.4;
        }}

        .verification-text a {{
            color: #1a4d3a;
            text-decoration: none;
            font-weight: 600;
        }}

        @media print {{
            body {{
                background-color: white;
                padding: 0;
                margin: 0;
            }}

            .certificate-container {{
                box-shadow: none;
                margin: 0;
                page-break-after: avoid;
                page-break-inside: avoid;
            }}
        }}
    </style>
</head>
<body>
    <div class="certificate-container">
        <div class="corner-decoration top-left"></div>
        <div class="corner-decoration top-right"></div>
        <div class="corner-decoration bottom-left"></div>
        <div class="corner-decoration bottom-right"></div>

        <div class="pattern-overlay"></div>

        <div class="content-wrapper">
            <div class="main-content">
                <div class="header">
                    <div class="logo-container">
                        <img class="hco-logo" src="HCO-Logo.png" alt="HCO Logo">
                    </div>

                    <div class="title">Halal Certificate</div>

                    <div class="cert-header-row">
                        <div class="issue-date">Issue Date: {issue_date_formatted}</div>
                        <div class="cert-info">
                            <div class="cert-info-item"><span class="label">Certificate No:</span> {certificate_no}</div>
                            <div class="cert-info-item standard"><span class="label">Standard:</span> {standards}</div>
                        </div>
                    </div>

                    <div class="auth-text">This is to authenticate that</div>
                </div>

                <div class="company-info">
                    <div class="company-line">
                    <div class="company-logo company-logo-head">{company_logo_html}</div>
                    {company_name}
                    </div>
                    <div class="company-reg-display">(Company Register Number: {company_reg_no})</div>
                    <div class="registered-text">registered at</div>
                    <div class="company-address">{company_address}</div>
                </div>

                <div class="description-text">
                    is certified for the following scope of work and its production facilities according to <strong>{standards}</strong><br>
                    Islamic dietary regulations, UK Good Manufacturing Practices (GMP), HACCP and HCO's relevant standard.
                </div>

                <hr class="section-divider">

                <table class="products-table">
                    <thead>
                        <tr>
                            <th style="width: 30%;">Code</th>
                            <th style="width: 70%;">Description</th>
                        </tr>
                    </thead>
                    <tbody>
                        {table_rows}
                    </tbody>
                </table>

                <div class="halal-disclaimer" style="text-align: left; font-size: 9px; color: #555; margin: 8px 0; font-style: italic;">
                    *All approved and named products with a Halal Logo are permissible for Muslim consumption.
                </div>
            </div>

            <div class="footer-section">
                <table class="signature-table">
                    <tr>
                        <td class="sig-cell-left" style="width: 50%;">
                            <div class="signature-block">
                                <img class="signature-img" src="khalid.png" alt="Signature">
                                <div class="signature-name">Dr Mohammad Khalid</div>
                                <div class="signature-title">Member of Sharia Board</div>
                            </div>
                        </td>
                        <td class="sig-cell-right" style="width: 50%;">
                            <div class="signature-block">
                                <img class="signature-img" src="babar.png" alt="Signature">
                                <div class="signature-name">Babar Iqbal</div>
                                <div class="signature-title">CEO</div>
                            </div>
                        </td>
                    </tr>
                </table>

                <div class="bottom-footer">
                    <div class="dates-section">
                        <div class="date-line"><span class="label">Expiry / Renewal Date of Certificate:</span> <span class="value">{expiry_date_long}</span></div>
                    </div>
                    <div class="validity-text">{validity_text}</div>
                    <div class="recognition-text">HCO is recognised by GSO & SMIIC (GAC), SFDA, SASO, MOIAT, MOPH (Qatar), MUIS(Singapore), CICOT (Thailand), IMANOR (Morocco) & has other collaborations globally.</div>
                    <div class="company-details">Halal Certification Organisation Limited, 34 Mornington Road, Birmingham, West Midlands, B66 2JE</div>
                    <div class="contact-details">T: +44 (0)333 5770902 E: info@hcoltd.co.uk</div>
                    <div class="website">www.hcoltd.co.uk</div>
                    <div
            style="
              text-align: center;
              font-size: 9px;
              color: #555;
              margin: 8px 0;
              font-style: italic;
              display: flex;
              gap: 10px;
              justify-content: space-between;
              align-items: center;
              width: 100%;
            "
          >
            <p>{cert_num_footer_safe}</p>
            <p>Reg No. 10321924</p>
            <p>VAT No. 273 575 085</p>
            <p>Page 1 of 1</p>
          </div>
                    <div class="verification-section">
                        <img class="qr-code" src="qr.png" alt="QR Code">
                        <div class="verification-text">
                            To verify this certificate, please scan the QR code<br>
                            or visit <a href="https://www.hcoltd.co.uk/certificatevalidation">www.hcoltd.co.uk/certificatevalidation</a>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>"""

    return html_template


def generate_slaughterhouse_certificate(
    certificate_no: str,
    company_name: str,
    company_reg_no: str,
    issue_date: str,
    expiry_date: str,
    standards: str,
    company_address: str,
    pu: str = "",
    au: str = "",
    sow: str = "",
    pl: str = "",  # Product List content
    validity_period: str = "3",
    company_logo: Optional[Dict[str, Any]] = None,
    cert_num_footer: str = "",
) -> Dict[str, Any]:
    """
    Generate slaughterhouse certificate (single page, no annex).

    Returns:
        Dict with success status and PDF data
    """
    from datetime import datetime

    try:
        # Calculate expiry date if not provided
        if not expiry_date or expiry_date.strip() == "":
            expiry_date_formatted = calculate_expiry_date(issue_date, validity_period)
        else:
            expiry_date_formatted = format_date_dmy(expiry_date)

        # Generate HTML content
        html_content = generate_slaughterhouse_certificate_html(
            certificate_no=certificate_no,
            company_name=company_name,
            company_reg_no=company_reg_no,
            issue_date=issue_date,
            expiry_date=expiry_date_formatted,
            standards=standards,
            company_address=company_address,
            pu=pu,
            au=au,
            sow=sow,
            pl=pl,
            cert_num_footer=cert_num_footer,
            company_logo=company_logo,
            validity_period=validity_period,
        )

        # Convert HTML to PDF
        pdf_data = None
        pdf_generation_success = False

        # Try weasyprint first
        try:
            os.environ['DYLD_LIBRARY_PATH'] = '/opt/homebrew/lib:/usr/local/lib:' + os.environ.get('DYLD_LIBRARY_PATH', '')
            os.environ['PKG_CONFIG_PATH'] = '/opt/homebrew/lib/pkgconfig:/usr/local/lib/pkgconfig:' + os.environ.get('PKG_CONFIG_PATH', '')

            from weasyprint import HTML
            pdf_data = HTML(string=html_content, base_url=os.path.dirname(__file__)).write_pdf(
                presentational_hints=True,
                optimize_images=True
            )
            pdf_generation_success = True
            print(f"Generated slaughterhouse certificate PDF using weasyprint: {len(pdf_data)} bytes")
        except ImportError:
            print("weasyprint not available, trying playwright...")
        except Exception as e:
            print(f"WeasyPrint failed: {e}")

        # Fallback to playwright
        if not pdf_generation_success:
            try:
                from playwright.sync_api import sync_playwright

                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    page = browser.new_page()
                    page.set_content(html_content, wait_until='networkidle')
                    page.wait_for_timeout(1000)

                    pdf_data = page.pdf(
                        format='A4',
                        margin={'top': '0mm', 'right': '0mm', 'bottom': '0mm', 'left': '0mm'},
                        print_background=True,
                        prefer_css_page_size=True
                    )
                    browser.close()

                if pdf_data and len(pdf_data) > 100 and pdf_data.startswith(b'%PDF'):
                    pdf_generation_success = True
                    print(f"Generated slaughterhouse certificate PDF using playwright: {len(pdf_data)} bytes")
            except ImportError:
                print("Playwright not available")
            except Exception as e:
                print(f"Playwright failed: {e}")

        if not pdf_generation_success:
            pdf_data = html_content.encode('utf-8')
            print("Falling back to HTML output for slaughterhouse certificate")

        # Generate certificate ID
        certificate_id = f"{certificate_no}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Upload to OneDrive
        safe_cert_no = certificate_no.replace("/", "_").replace("\\", "_")
        pdf_filename = f"certificate_{safe_cert_no}.pdf"
        onedrive_success = False
        onedrive_web_url = None

        upload_filename = pdf_filename
        upload_content_type = "application/pdf"
        upload_content = pdf_data

        # If PDF generation failed, we still upload the HTML fallback for traceability.
        if not pdf_generation_success:
            upload_filename = f"certificate_{safe_cert_no}.html"
            upload_content_type = "text/html"
            upload_content = html_content.encode("utf-8")

        if upload_content:
            try:
                from microsoft_graph import get_access_token, upload_bytes_to_shared_folder, get_download_url_from_upload_result

                folder_share_url = os.getenv("HCO_ONEDRIVE_FOLDER_SHARE_URL") or os.getenv("ONEDRIVE_FOLDER_SHARE_URL")
                if folder_share_url:
                    token = get_access_token()
                    upload_result = upload_bytes_to_shared_folder(
                        folder_share_url=folder_share_url,
                        filename=upload_filename,
                        content=upload_content,
                        token=token,
                        content_type=upload_content_type,
                    )
                    onedrive_success = True
                    if isinstance(upload_result, dict):
                        try:
                            onedrive_web_url = get_download_url_from_upload_result(upload_result, token)
                        except Exception:
                            onedrive_web_url = upload_result.get("webUrl")
                    print(f"Slaughterhouse certificate uploaded to OneDrive: {upload_filename}")
            except Exception as e:
                print(f"Failed to upload slaughterhouse certificate to OneDrive: {e}")

        return {
            "success": True,
            "certificate_id": certificate_id,
            "certificate_no": certificate_no,
            "certificate_type": "slaughterhouse",
            "storage": "onedrive" if onedrive_success else "none",
            "pdf_generated": pdf_generation_success,
            "pdf_uploaded": onedrive_success,
            "pdf_bytes": pdf_data if pdf_generation_success else None,
            "onedrive_web_url": onedrive_web_url,
            "message": f"Slaughterhouse certificate generated. PDF: {'Generated and uploaded' if (pdf_generation_success and onedrive_success) else 'Failed or not uploaded'}"
        }

    except Exception as e:
        print(f"Error generating slaughterhouse certificate: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e)
        }


def generate_export_certificate(
    certificate_type: str,
    data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate export certificate (meat or non-meat) and return PDF data.

    Args:
        certificate_type: 'export_meat' or 'export_non_meat'
        data: Dictionary containing all certificate data

    Returns:
        Dict with success status and PDF data
    """
    from datetime import datetime

    try:
        # Generate HTML based on certificate type
        html_pages: List[str] = []
        if certificate_type == 'export_meat':
            html_pages = [generate_meat_export_certificate_html(data)]
        elif certificate_type == 'export_non_meat':
            all_products = data.get('products', [])
            if not isinstance(all_products, list):
                all_products = []
            products_per_page = int(data.get('export_products_per_page') or 10)
            if products_per_page <= 0:
                products_per_page = 10
            total_pages = max(1, (len(all_products) + products_per_page - 1) // products_per_page)
            for page_idx in range(total_pages):
                page_products = all_products[page_idx * products_per_page:(page_idx + 1) * products_per_page]
                page_data = dict(data)
                page_data['products_override'] = page_products
                page_data['page_number'] = page_idx + 1
                page_data['total_pages'] = total_pages
                html_pages.append(generate_non_meat_export_certificate_html(page_data))
        else:
            return {"success": False, "error": f"Unknown certificate type: {certificate_type}"}

        # Combine pages into single HTML document with page breaks (WeasyPrint-friendly)
        html_content = ""
        for i, page_html in enumerate(html_pages):
            if not page_html:
                continue
            if i == 0:
                html_content += page_html
            else:
                import re
                body_match = re.search(r'<body[^>]*>(.*?)</body>', page_html, re.DOTALL)
                if body_match:
                    body_content = body_match.group(1)
                    html_content += f'<div style="page-break-before: always;">{body_content}</div>'

        # Convert HTML to PDF
        pdf_data = None
        pdf_generation_success = False

        # Try weasyprint first
        try:
            os.environ['DYLD_LIBRARY_PATH'] = '/opt/homebrew/lib:/usr/local/lib:' + os.environ.get('DYLD_LIBRARY_PATH', '')
            os.environ['PKG_CONFIG_PATH'] = '/opt/homebrew/lib/pkgconfig:/usr/local/lib/pkgconfig:' + os.environ.get('PKG_CONFIG_PATH', '')

            from weasyprint import HTML
            pdf_data = HTML(string=html_content, base_url=os.path.dirname(__file__)).write_pdf(
                presentational_hints=True,
                optimize_images=True
            )
            pdf_generation_success = True
            print(f"Generated export certificate PDF using weasyprint: {len(pdf_data)} bytes")
        except ImportError:
            print("weasyprint not available, trying playwright...")
        except Exception as e:
            print(f"WeasyPrint failed: {e}")

        # Fallback to playwright
        if not pdf_generation_success:
            try:
                from playwright.sync_api import sync_playwright

                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    page = browser.new_page()
                    page.set_content(html_content, wait_until='networkidle')
                    page.wait_for_timeout(1000)

                    pdf_data = page.pdf(
                        format='A4',
                        margin={'top': '0mm', 'right': '0mm', 'bottom': '0mm', 'left': '0mm'},
                        print_background=True,
                        prefer_css_page_size=True
                    )
                    browser.close()

                if pdf_data and len(pdf_data) > 100 and pdf_data.startswith(b'%PDF'):
                    pdf_generation_success = True
                    print(f"Generated export certificate PDF using playwright: {len(pdf_data)} bytes")
            except ImportError:
                print("Playwright not available")
            except Exception as e:
                print(f"Playwright failed: {e}")

        if not pdf_generation_success:
            # Return HTML as fallback
            pdf_data = html_content.encode('utf-8')
            print("Falling back to HTML output for export certificate")

        # Generate certificate ID
        certificate_id = f"{data.get('certificate_no', 'EXPORT')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Upload to OneDrive
        pdf_filename = f"certificate_{data.get('certificate_no', 'export').replace('/', '_')}.pdf"
        onedrive_success = False
        onedrive_web_url = None

        upload_filename = pdf_filename
        upload_content_type = "application/pdf"
        upload_content = pdf_data

        # If PDF generation failed, we still upload the HTML fallback for traceability.
        if not pdf_generation_success:
            upload_filename = f"certificate_{data.get('certificate_no', 'export').replace('/', '_')}.html"
            upload_content_type = "text/html"
            upload_content = html_content.encode("utf-8")

        if upload_content:
            try:
                from microsoft_graph import get_access_token, upload_bytes_to_shared_folder, get_download_url_from_upload_result

                folder_share_url = os.getenv("HCO_ONEDRIVE_FOLDER_SHARE_URL") or os.getenv("ONEDRIVE_FOLDER_SHARE_URL")
                if folder_share_url:
                    token = get_access_token()
                    upload_result = upload_bytes_to_shared_folder(
                        folder_share_url=folder_share_url,
                        filename=upload_filename,
                        content=upload_content,
                        token=token,
                        content_type=upload_content_type,
                    )
                    onedrive_success = True
                    if isinstance(upload_result, dict):
                        try:
                            onedrive_web_url = get_download_url_from_upload_result(upload_result, token)
                        except Exception:
                            onedrive_web_url = upload_result.get("webUrl")
                    print(f"Export certificate uploaded to OneDrive: {upload_filename}")
            except Exception as e:
                print(f"Failed to upload export certificate to OneDrive: {e}")

        return {
            "success": True,
            "certificate_id": certificate_id,
            "certificate_no": data.get('certificate_no', ''),
            "certificate_type": certificate_type,
            "storage": "onedrive" if onedrive_success else "none",
            "pdf_generated": pdf_generation_success,
            "pdf_uploaded": onedrive_success,
            "pdf_bytes": pdf_data if pdf_generation_success else None,
            "onedrive_web_url": onedrive_web_url,
            "message": f"Export certificate generated. PDF: {'Generated and uploaded' if (pdf_generation_success and onedrive_success) else 'Failed or not uploaded'}"
        }

    except Exception as e:
        print(f"Error generating export certificate: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e)
        }
