#!/usr/bin/env python3
"""
Generate sample certificates of each type with dummy data.
Outputs HTML files (and PDFs if WeasyPrint is available) into ./sample_output/.
"""
import os
import sys
import shutil
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))

from html_certificate_generator import (
    generate_html_certificate,
    generate_slaughterhouse_certificate_html,
    generate_export_certificate,
)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "sample_output")


def _save(filename: str, content, is_pdf=False):
    path = os.path.join(OUTPUT_DIR, filename)
    if is_pdf and isinstance(content, bytes):
        with open(path, "wb") as f:
            f.write(content)
    else:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content if isinstance(content, str) else content.decode("utf-8", errors="replace"))
    print(f"  ✅ Saved: {path}")


def generate_domestic():
    """Domestic Halal Certificate with annex pages."""
    print("\n📄 1. Domestic Halal Certificate (3-year, GAC + ENAS logos)")

    products = [
        {"product_code": f"PRD{i:03d}", "product_name": f"Sample Product {i} - Halal Certified Item"}
        for i in range(1, 16)
    ]

    issue = datetime.now().strftime("%Y-%m-%d")
    expiry = (datetime.now() + timedelta(days=365 * 3)).strftime("%Y-%m-%d")

    pdf_or_html = generate_html_certificate(
        certificate_no="HCO/SAMPLE/DOM/2026-001",
        company_name="Acme Foods Ltd T/A Acme Halal",
        company_reg_no="12345678",
        issue_date=issue,
        expiry_date=expiry,
        standards="UAE.S 2055-1/2015 Category CIII, GSO 2055-1/2015 Category CIII",
        company_address="123 Industrial Park, Birmingham, West Midlands, B1 1AA",
        pu="Unit 5, Acme Industrial Estate",
        au="",
        sow="Food Processing and Manufacturing",
        products=products,
        company_logo=None,
        validity_period="3",
        cert_num_footer="HCO/SAMPLE/DOM/2026-001",
        annex_layout_options={"columns": 2, "products_per_page": 10},
        domestic_logo_1="gac",
        domestic_logo_2="enas",
    )

    if isinstance(pdf_or_html, bytes) and pdf_or_html[:4] == b"%PDF":
        _save("1_domestic_certificate.pdf", pdf_or_html, is_pdf=True)
    else:
        _save("1_domestic_certificate.html", pdf_or_html)


def generate_domestic_1yr():
    """Domestic certificate with 1-year validity (surveillance audit re-issue)."""
    print("\n📄 2. Domestic Certificate (1-year surveillance, GAC only)")

    products = [
        {"product_code": f"BMS{7700 + i}", "product_name": f"DOLCETTO - Flavour Syrup Variant {i}"}
        for i in range(1, 8)
    ]

    issue = datetime.now().strftime("%Y-%m-%d")
    expiry = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")

    pdf_or_html = generate_html_certificate(
        certificate_no="HCO/SAMPLE/SUR/2026-002",
        company_name="Sweet Syrups International Ltd",
        company_reg_no="98765432",
        issue_date=issue,
        expiry_date=expiry,
        standards="HCO Halal Standard V7.3",
        company_address="Unit 12, Maple Business Park, London, E14 5AB",
        pu="",
        au="Head Office, Maple Business Park",
        sow="Manufacture and Distribution of Flavoured Syrups",
        products=products,
        validity_period="1",
        cert_num_footer="HCO/SAMPLE/SUR/2026-002",
        annex_layout_options={"columns": 2, "products_per_page": 10},
        domestic_logo_1="gac",
        domestic_logo_2="none",
    )

    if isinstance(pdf_or_html, bytes) and pdf_or_html[:4] == b"%PDF":
        _save("2_domestic_1yr_certificate.pdf", pdf_or_html, is_pdf=True)
    else:
        _save("2_domestic_1yr_certificate.html", pdf_or_html)


def generate_domestic_3col():
    """Domestic certificate with 3-column layout (code + name + packaging)."""
    print("\n📄 3. Domestic Certificate (3-column: Code | Name | Packaging)")

    products = [
        {
            "product_code": f"PKG{i:03d}",
            "product_name": f"Halal Snack Item {i}",
            "packaging_details": f"{100 + i * 50}g Pouch" if i % 2 == 0 else f"{i} x 250ml Bottle",
        }
        for i in range(1, 12)
    ]

    issue = datetime.now().strftime("%Y-%m-%d")
    expiry = (datetime.now() + timedelta(days=365 * 2)).strftime("%Y-%m-%d")

    pdf_or_html = generate_html_certificate(
        certificate_no="HCO/SAMPLE/PKG/2026-003",
        company_name="Global Snacks Ltd",
        company_reg_no="11223344",
        issue_date=issue,
        expiry_date=expiry,
        standards="UAE.S & GSO 2055-1, Category K",
        company_address="456 Commerce Road, Manchester, M1 2AB",
        pu="Factory A, Commerce Road",
        au="",
        sow="Snack Food Manufacturing and Packaging",
        products=products,
        validity_period="2",
        cert_num_footer="HCO/SAMPLE/PKG/2026-003",
        annex_layout_options={"columns": 3, "products_per_page": 10},
        domestic_logo_1="enas",
        domestic_logo_2="none",
    )

    if isinstance(pdf_or_html, bytes) and pdf_or_html[:4] == b"%PDF":
        _save("3_domestic_3col_certificate.pdf", pdf_or_html, is_pdf=True)
    else:
        _save("3_domestic_3col_certificate.html", pdf_or_html)


def generate_slaughterhouse():
    """Slaughterhouse Certificate."""
    print("\n📄 4. Slaughterhouse Certificate")

    issue = datetime.now().strftime("%d-%m-%Y")
    expiry = (datetime.now() + timedelta(days=365 * 3)).strftime("%d-%m-%Y")

    html = generate_slaughterhouse_certificate_html(
        certificate_no="HCO/SAMPLE/SH/2026-004",
        company_name="Halal Meats Processing Ltd",
        company_reg_no="55667788",
        issue_date=issue,
        expiry_date=expiry,
        standards="HCO Halal Slaughter Standard V3.0",
        company_address="789 Abattoir Lane, Leicester, LE1 3CD",
        pu="Slaughterhouse Facility, Abattoir Lane",
        au="",
        sow="Halal Slaughter of Poultry and Ovine",
        pl="Chicken, Lamb, Goat",
        cert_num_footer="HCO/SAMPLE/SH/2026-004",
        company_logo=None,
        validity_period="3",
    )

    try:
        from weasyprint import HTML as WeasyprintHTML
        pdf_data = WeasyprintHTML(
            string=html, base_url=os.path.dirname(__file__)
        ).write_pdf(presentational_hints=True, optimize_images=True)
        _save("4_slaughterhouse_certificate.pdf", pdf_data, is_pdf=True)
    except Exception as e:
        print(f"  ⚠️  PDF conversion failed ({e}), saving HTML fallback")
        _save("4_slaughterhouse_certificate.html", html)


def generate_export_meat():
    """Meat Export Certificate."""
    print("\n📄 5. Meat Export Certificate")

    data = {
        "certificate_no": "HCO/SAMPLE/EM/2026-005",
        "issue_date": datetime.now().strftime("%Y-%m-%d"),
        "expiry_date": (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d"),
        "country_of_origin": "United Kingdom",
        "destination": "Kingdom of Saudi Arabia",
        "exporter_name": "British Halal Exports Ltd",
        "importer_name": "Al-Madinah Food Imports Co.",
        "slaughter_date": (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
        "producer_name": "Halal Meats Processing Ltd",
        "abattoir_address": "789 Abattoir Lane, Leicester, LE1 3CD",
        "gross_weight": "5,000 kg",
        "net_weight": "4,500 kg",
        "number_of_carcasses": "200",
        "number_of_boxes": "150",
        "batch_reference": "BATCH-2026-EM-001",
        "halal_cert_number": "HCO/SAMPLE/SH/2026-004",
        "vet_cert_number": "VET/UK/2026/12345",
        "destination_port": "Jeddah Islamic Port",
        "loading_port": "Port of Felixstowe",
        "flight_number": "BA1234",
        "meat_type": "Lamb - Whole Carcass",
        "awb_number": "AWB-2026-56789",
        "meat_condition": "Frozen",
        "inspector_name": "Dr. Ahmed Khan",
        "export_logo_option": "gac",
        "export_signature_option": "with",
    }

    result = generate_export_certificate("export_meat", data)
    if result.get("success"):
        pdf_data = result.get("pdf_bytes")
        if isinstance(pdf_data, bytes) and pdf_data[:4] == b"%PDF":
            _save("5_export_meat_certificate.pdf", pdf_data, is_pdf=True)
        elif pdf_data:
            _save("5_export_meat_certificate.html", pdf_data)
        else:
            print("  ⚠️  No output data returned")
    else:
        print(f"  ❌ Failed: {result.get('error', 'unknown')}")


def generate_export_non_meat():
    """Non-Meat Export Certificate."""
    print("\n📄 6. Non-Meat Export Certificate")

    products = [
        {
            "product_code": f"NM{i:03d}",
            "description": f"Halal Certified Food Product {i}",
            "quantity": f"{100 * i} units",
            "manufacture_date": (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
            "expiry_date": (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d"),
            "batch_number": f"BATCH-NM-{i:03d}",
            "gross_weight": f"{50 * i} kg",
            "net_weight": f"{45 * i} kg",
            "number_of_cases": f"{10 * i}",
        }
        for i in range(1, 7)
    ]

    data = {
        "certificate_no": "HCO/SAMPLE/ENM/2026-006",
        "issue_date": datetime.now().strftime("%Y-%m-%d"),
        "country_of_origin": "United Kingdom",
        "destination": "United Arab Emirates",
        "exporter_name": "UK Halal Foods Export Ltd",
        "importer_name": "Dubai Fine Foods Trading LLC",
        "shipment_mode": "Sea Freight",
        "invoice_no": "INV-2026-ENM-001",
        "vet_health_cert_no": "VHC/UK/2026/67890",
        "products": products,
        "export_products_per_page": 10,
        "export_logo_option": "enas",
        "export_signature_option": "with",
    }

    result = generate_export_certificate("export_non_meat", data)
    if result.get("success"):
        pdf_data = result.get("pdf_bytes")
        if isinstance(pdf_data, bytes) and pdf_data[:4] == b"%PDF":
            _save("6_export_non_meat_certificate.pdf", pdf_data, is_pdf=True)
        elif pdf_data:
            _save("6_export_non_meat_certificate.html", pdf_data)
        else:
            print("  ⚠️  No output data returned")
    else:
        print(f"  ❌ Failed: {result.get('error', 'unknown')}")


def main():
    print("=" * 60)
    print("  HCO Sample Certificate Generator")
    print("=" * 60)

    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"\nOutput directory: {OUTPUT_DIR}")

    generate_domestic()
    generate_domestic_1yr()
    generate_domestic_3col()
    generate_slaughterhouse()
    generate_export_meat()
    generate_export_non_meat()

    print("\n" + "=" * 60)
    print(f"  Done! Check {OUTPUT_DIR}/")
    print("=" * 60)


if __name__ == "__main__":
    main()
