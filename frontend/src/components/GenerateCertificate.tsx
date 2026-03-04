import React, { useEffect, useState } from "react";
import * as XLSX from "xlsx";
import { getApiUrl } from "../config/env";
import { authService } from "../services/authService";

// Certificate category types
type CertificateCategory = "domestic" | "export_meat" | "export_non_meat" | "slaughterhouse";

type ExportLogoOption = "" | "enas" | "gac" | "none";
type DomesticLogoOption = "gac" | "enas" | "none";
type ExportSignatureOption = "" | "with" | "without";

interface FormData {
  // Common fields
  issue_date: string;
  certificate_no: string;
  standards: string;
  certificate_category: CertificateCategory;
  cert_num_footer: string;

  // Halal Certificate fields (existing)
  company_name: string;
  company_address: string;
  pu: string;
  au: string;
  sow: string;
  pl: string;  // Product List content (used for slaughterhouse certificates)
  validity_period: "1" | "2" | "3";
  company_reg_no: string;
  csv_files: File[];
  company_logo: File | null;
  domestic_logo_1: DomesticLogoOption;
  domestic_logo_2: DomesticLogoOption;

  // Export Certificate fields (common)
  country_of_origin: string;
  destination: string;
  exporter_name: string;
  importer_name: string;

  // Export Certificate options
  export_logo_option: ExportLogoOption;
  export_signature_option: ExportSignatureOption;

  // Meat Export specific fields
  slaughter_date: string;
  producer_name: string;
  expiry_date: string;
  abattoir_address: string;
  gross_weight: string;
  number_of_carcasses: string;
  net_weight: string;
  number_of_boxes: string;
  batch_reference: string;
  halal_cert_number: string;
  vet_cert_number: string;
  destination_port: string;
  loading_port: string;
  flight_number: string;
  meat_type: string;
  awb_number: string;
  meat_condition: string;
  inspector_name: string;

  // Non-Meat Export specific fields
  shipment_mode: string;
  invoice_no: string;
  vet_health_cert_no: string;
  products: ProductRow[];
  export_products_per_page: number;
}

interface ProductRow {
  product_code: string;
  description: string;
  quantity: string;
  manufacture_date: string;
  expiry_date: string;
  batch_number: string;
  gross_weight: string;
  net_weight: string;
  number_of_cases: string;
}

interface GenerateResult {
  success?: boolean;
  status?: string;
  certificate_id?: string;
  message?: string;
  download_url?: string;
}

interface DownloadData {
  certificate_no: string;
  file_type: "pdf";
}

 type DomesticProductSchema = "name_only" | "code_name" | "code_name_packaging";

 type ParsedDomesticRow = {
   product_name: string;
   product_code?: string;
   packaging_details?: string;
 };

interface InputFieldProps {
  label: string;
  name: string;
  value: string;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  required?: boolean;
  placeholder?: string;
  type?: string;
  disabled?: boolean;
  warningText?: string;
}

interface TextareaFieldProps {
  label: string;
  name: string;
  value: string;
  onChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
  rows?: number;
  required?: boolean;
  placeholder?: string;
  warningText?: string;
}

const InputField: React.FC<InputFieldProps> = ({
  label,
  name,
  value,
  onChange,
  required,
  placeholder,
  type = "text",
  disabled,
  warningText,
}) => (
  <div className="flex flex-col">
    <label className="text-xs sm:text-sm font-medium text-[#4f8f5e] mb-2 font-quicksand">
      {label} {required && <span className="text-[#4f8f5e]">*</span>}
    </label>
    <input
      type={type}
      name={name}
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      required={required}
      disabled={disabled}
      className={`h-10 sm:h-12 px-3 sm:px-4 text-xs sm:text-sm placeholder-[#9bb7a4] outline-none font-quicksand ${
        disabled
          ? "bg-[#e8f0eb]/60 text-[#4f8f5e]/60 cursor-not-allowed"
          : "bg-[#e8f0eb] text-[#4f8f5e]"
      }`}
    />
    {warningText ? (
      <div className="mt-1 text-[11px] leading-4 text-[#b45309] font-quicksand">
        {warningText}
      </div>
    ) : null}
  </div>
);

const TextareaField: React.FC<TextareaFieldProps> = ({
  label,
  name,
  value,
  onChange,
  rows = 3,
  required,
  placeholder,
  warningText,
}) => (
  <div className="flex flex-col">
    <label className="text-xs sm:text-sm font-medium text-[#4f8f5e] mb-2 font-quicksand">
      {label} {required && <span className="text-[#4f8f5e]">*</span>}
    </label>
    <textarea
      name={name}
      value={value}
      onChange={onChange}
      rows={rows}
      required={required}
      placeholder={placeholder}
      className="bg-[#e8f0eb] text-[#4f8f5e] px-3 sm:px-4 py-2 sm:py-3 text-xs sm:text-sm placeholder-[#9bb7a4] outline-none font-quicksand"
    />
    {warningText ? (
      <div className="mt-1 text-[11px] leading-4 text-[#b45309] font-quicksand">
        {warningText}
      </div>
    ) : null}
  </div>
);

const emptyProductRow: ProductRow = {
  product_code: "",
  description: "",
  quantity: "",
  manufacture_date: "",
  expiry_date: "",
  batch_number: "",
  gross_weight: "",
  net_weight: "",
  number_of_cases: "",
};

const GenerateCertificate: React.FC = () => {
  const [formData, setFormData] = useState<FormData>({
    // Common fields
    issue_date: new Date().toISOString().split("T")[0],
    certificate_no: "",
    standards: "",
    certificate_category: "domestic",
    cert_num_footer: "",

    // Halal Certificate fields
    company_name: "",
    company_address: "",
    pu: "",
    au: "",
    sow: "",
    pl: "",
    validity_period: "1",
    company_reg_no: "",
    csv_files: [],
    company_logo: null,
    domestic_logo_1: "gac",
    domestic_logo_2: "none",

    // Export Certificate fields
    country_of_origin: "",
    destination: "",
    exporter_name: "",
    importer_name: "",

    // Export Certificate options
    export_logo_option: "enas",
    export_signature_option: "with",

    // Meat Export fields
    slaughter_date: "",
    producer_name: "",
    expiry_date: "",
    abattoir_address: "",
    gross_weight: "",
    number_of_carcasses: "",
    net_weight: "",
    number_of_boxes: "",
    batch_reference: "",
    halal_cert_number: "",
    vet_cert_number: "",
    destination_port: "",
    loading_port: "",
    flight_number: "",
    meat_type: "",
    awb_number: "",
    meat_condition: "",
    inspector_name: "",

    // Non-Meat Export fields
    shipment_mode: "",
    invoice_no: "",
    vet_health_cert_no: "",
    products: [{ ...emptyProductRow }],
    export_products_per_page: 10,
  });

  const [exportProductsPerPageInput, setExportProductsPerPageInput] = useState<string>(
    String(formData.export_products_per_page || 10)
  );

  useEffect(() => {
    setExportProductsPerPageInput(String(formData.export_products_per_page || 10));
  }, [formData.export_products_per_page]);

  const exportProductsPerPagePreview = (() => {
    if (/^\d+$/.test(exportProductsPerPageInput)) {
      const parsed = Number.parseInt(exportProductsPerPageInput, 10);
      return Number.isFinite(parsed) ? parsed : (formData.export_products_per_page || 10);
    }
    return formData.export_products_per_page || 10;
  })();

  const [result, setResult] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);
  const [dragOver, setDragOver] = useState<boolean>(false);

  const [nonMeatProductInputMode, setNonMeatProductInputMode] = useState<"manual" | "docx">("manual");
  const [nonMeatDocxFile, setNonMeatDocxFile] = useState<File | null>(null);
  const [nonMeatDocxParsing, setNonMeatDocxParsing] = useState<boolean>(false);
  const [nonMeatDocxError, setNonMeatDocxError] = useState<string>("");

   const [domesticSchema, setDomesticSchema] = useState<DomesticProductSchema | null>(null);
   const [domesticParsedRows, setDomesticParsedRows] = useState<ParsedDomesticRow[]>([]);
   const [domesticParseError, setDomesticParseError] = useState<string>("");
   const [domesticParsing, setDomesticParsing] = useState<boolean>(false);
   const [domesticLayout, setDomesticLayout] = useState<{
     rows: number;
     columns: number;
     products_per_page: number;
   }>({
     rows: 5,
     columns: 2,
     products_per_page: 10,
   });

   const [domesticColumnsInput, setDomesticColumnsInput] = useState<string>(
     String(domesticLayout.columns)
   );

   useEffect(() => {
     setDomesticColumnsInput(String(domesticLayout.columns));
   }, [domesticLayout.columns]);

   const [domesticRowsInput, setDomesticRowsInput] = useState<string>(
     String(domesticLayout.rows)
   );

   useEffect(() => {
     setDomesticRowsInput(String(domesticLayout.rows));
   }, [domesticLayout.rows]);

   const [domesticProductsPerPageInput, setDomesticProductsPerPageInput] = useState<string>(
     String(domesticLayout.products_per_page)
   );

   useEffect(() => {
     setDomesticProductsPerPageInput(String(domesticLayout.products_per_page));
   }, [domesticLayout.products_per_page]);

  const domesticProductsPerPageLimit = domesticLayout.columns === 3 ? 10 : domesticLayout.columns === 2 ? 10 : 16;

  const domesticColumnsPreview = (() => {
    if (/^\d+$/.test(domesticColumnsInput)) {
      const parsed = Number.parseInt(domesticColumnsInput, 10);
      return Number.isFinite(parsed) ? parsed : domesticLayout.columns;
    }
    return domesticLayout.columns;
  })();

  const domesticRowsPreview = (() => {
    if (/^\d+$/.test(domesticRowsInput)) {
      const parsed = Number.parseInt(domesticRowsInput, 10);
      return Number.isFinite(parsed) ? parsed : domesticLayout.rows;
    }
    return domesticLayout.rows;
  })();

  const domesticProductsPerPagePreview = (() => {
    if (/^\d+$/.test(domesticProductsPerPageInput)) {
      const parsed = Number.parseInt(domesticProductsPerPageInput, 10);
      return Number.isFinite(parsed) ? parsed : domesticLayout.products_per_page;
    }
    return domesticLayout.products_per_page;
  })();

  const domesticLayoutWarnings = {
    columns: domesticColumnsPreview > 4,
    rows: domesticRowsPreview > 10,
    productsPerPage:
      domesticSchema !== "name_only" &&
      domesticProductsPerPagePreview > domesticProductsPerPageLimit,
  };

  // Download state
  const [downloadData, setDownloadData] = useState<DownloadData>({
    certificate_no: "",
    file_type: "pdf",
  });
  const [downloadResult, setDownloadResult] = useState<string>("");
  const [downloadLoading, setDownloadLoading] = useState<boolean>(false);
  const [downloadUrl, setDownloadUrl] = useState<string>("");

  const puHasValue = Boolean((formData.pu || "").trim());
  const auHasValue = Boolean((formData.au || "").trim());

  const exporterLen = (formData.exporter_name || "").trim().length;
  const importerLen = (formData.importer_name || "").trim().length;
  const companyAddressLen = (formData.company_address || "").trim().length;
  const abattoirAddressLen = (formData.abattoir_address || "").trim().length;

  const exporterWarning =
    exporterLen > 90
      ? `Warning: Exporter exceeds 90 characters (${exporterLen}). This may cause overlapping in the certificate.`
      : "";
  const importerWarning =
    importerLen > 90
      ? `Warning: Importer exceeds 90 characters (${importerLen}). This may cause overlapping in the certificate.`
      : "";
  const companyAddressWarning =
    companyAddressLen > 120
      ? `Warning: Address exceeds 120 characters (${companyAddressLen}). This may cause overlapping in the certificate.`
      : "";
  const abattoirAddressWarning =
    abattoirAddressLen > 120
      ? `Warning: Address exceeds 120 characters (${abattoirAddressLen}). This may cause overlapping in the certificate.`
      : "";

  const handleInputChange = (
    e: React.ChangeEvent<
      HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement
    >
  ) => {
    const { name, value } = e.target;

    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const renderExportOptions = () => (
    <div className="bg-[#f7fbf8] border border-[#e0efe4] p-6 sm:p-8 shadow-sm">
      <h3 className="text-lg font-semibold text-[#4f8f5e] font-quicksand mb-6">
        Export Options
      </h3>

      <div className="grid gap-6 md:grid-cols-2">
        <div className="flex flex-col">
          <label className="text-xs sm:text-sm font-medium text-[#4f8f5e] mb-2 font-quicksand">
            Logo
          </label>
          <select
            name="export_logo_option"
            value={formData.export_logo_option}
            onChange={handleInputChange}
            className="h-10 sm:h-12 bg-[#e8f0eb] text-[#4f8f5e] px-3 sm:px-4 text-xs sm:text-sm outline-none font-quicksand"
          >
            <option value="enas">ENAS</option>
            <option value="gac">GAC</option>
            <option value="none">No Logo</option>
          </select>
        </div>

        <div className="flex flex-col">
          <label className="text-xs sm:text-sm font-medium text-[#4f8f5e] mb-2 font-quicksand">
            Signature Option
          </label>
          <select
            name="export_signature_option"
            value={formData.export_signature_option}
            onChange={handleInputChange}
            className="h-10 sm:h-12 bg-[#e8f0eb] text-[#4f8f5e] px-3 sm:px-4 text-xs sm:text-sm outline-none font-quicksand"
          >
            <option value="with">With signature</option>
            <option value="without">Without signature</option>
          </select>
        </div>
      </div>
    </div>
  );

   const normalizeHeader = (value: unknown) =>
     String(value ?? "")
       .toLowerCase()
       .replace(/\s+/g, " ")
       .trim();

   const normalizeKey = (value: unknown) => normalizeHeader(value).replace(/[^a-z0-9]+/g, "");

   const parseDomesticXlsxFiles = async (files: File[]) => {
     setDomesticParseError("");
     setDomesticSchema(null);
     setDomesticParsedRows([]);
     if (!files.length) return;

     setDomesticParsing(true);
     try {
       const file = files[0];
       const buffer = await file.arrayBuffer();
       const workbook = XLSX.read(buffer, { type: "array" });

       const wantedSheetNames = [
         "final product name",
         "final product names",
         "final products names",
         "final producsts names",
       ];

       const sheetName = workbook.SheetNames.find((s: string) =>
         wantedSheetNames.includes(normalizeHeader(s))
       );

       if (!sheetName) {
         setDomesticParseError(
           "Required sheet not found. Please upload an XLSX containing a sheet named 'Final Product Name'."
         );
         return;
       }

       const sheet = workbook.Sheets[sheetName];
       if (!sheet) {
         setDomesticParseError("Unable to read sheet from the uploaded XLSX file.");
         return;
       }

       const grid = (XLSX.utils.sheet_to_json(sheet, {
         header: 1,
         defval: "",
         blankrows: false,
       }) || []) as unknown[][];

       if (!grid.length) {
         setDomesticParseError("No rows found in the uploaded XLSX file.");
         return;
       }

       const PRODUCT_NAME_KEYS = ["productname", "description", "productdescription"];
       const PRODUCT_CODE_KEYS = ["productcode", "productcodes"];
       const PACKAGING_KEYS = ["packagingdetails", "packaging", "packagingdetail", "packingdetails", "packing"];

       let headerRowIndex = -1;
       let productNameColIndex = -1;
       let productCodeColIndex = -1;
       let packagingColIndex = -1;

       const maxScanRows = Math.min(100, grid.length);
       for (let r = 0; r < maxScanRows; r += 1) {
         const row = grid[r] || [];
         const normalized = row.map((cell) => normalizeKey(cell));

         const nameIdx = normalized.findIndex((v) => PRODUCT_NAME_KEYS.includes(v));
         if (nameIdx === -1) continue;

         headerRowIndex = r;
         productNameColIndex = nameIdx;
         productCodeColIndex = normalized.findIndex((v) => PRODUCT_CODE_KEYS.includes(v));
         packagingColIndex = normalized.findIndex((v) => PACKAGING_KEYS.includes(v));
         break;
       }

       if (headerRowIndex === -1 || productNameColIndex === -1) {
         setDomesticParseError(
           "Header row not found. Please ensure the 'Final Product Name' sheet has a header row containing 'Product Name' or 'Description' (and optionally 'Product Code')."
         );
         return;
       }

       const hasCode = productCodeColIndex >= 0;
       const hasPackaging = packagingColIndex >= 0;
       const schema: DomesticProductSchema =
         hasCode && hasPackaging ? "code_name_packaging" :
         hasCode ? "code_name" : "name_only";
       setDomesticSchema(schema);

       const parsed: ParsedDomesticRow[] = [];
       for (let r = headerRowIndex + 1; r < grid.length; r += 1) {
         const row = grid[r] || [];
         const product_name = String(row[productNameColIndex] ?? "").trim();
         const product_code = hasCode ? String(row[productCodeColIndex] ?? "").trim() : "";
         const packaging_details = hasPackaging ? String(row[packagingColIndex] ?? "").trim() : "";

         if (!product_name) continue;

         if (schema === "code_name_packaging") {
           parsed.push({
             product_code: product_code || undefined,
             product_name,
             packaging_details: packaging_details || undefined,
           });
         } else if (schema === "code_name") {
           parsed.push({
             product_code: product_code || undefined,
             product_name,
           });
         } else {
           parsed.push({ product_name });
         }
       }

       setDomesticParsedRows(parsed);

       if (schema === "name_only") {
        setDomesticLayout((prev) => ({
          ...prev,
          products_per_page: prev.rows * prev.columns,
        }));
      } else if (schema === "code_name_packaging") {
        setDomesticLayout((prev) => ({
          ...prev,
          columns: 3,
          products_per_page: 10,
        }));
      } else {
        setDomesticLayout((prev) => ({
          ...prev,
          columns: 2,
          products_per_page: 10,
        }));
      }
    } catch (e) {
      setDomesticParseError("Failed to parse the XLSX file. Please verify the file format.");
    } finally {
      setDomesticParsing(false);
    }
  };

  const handleProductChange = (index: number, field: keyof ProductRow, value: string) => {
    setFormData((prev) => {
      const newProducts = [...prev.products];
      newProducts[index] = { ...newProducts[index], [field]: value };
      return { ...prev, products: newProducts };
    });
  };

  const addProductRow = () => {
    setFormData((prev) => ({
      ...prev,
      products: [...prev.products, { ...emptyProductRow }],
    }));
  };

  const removeProductRow = (index: number) => {
    if (formData.products.length > 1) {
      setFormData((prev) => ({
        ...prev,
        products: prev.products.filter((_, i) => i !== index),
      }));
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files) {
      processFiles(Array.from(files));
    }
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragOver(false);
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragOver(false);
    const files = Array.from(e.dataTransfer.files);
    processFiles(files);
  };

  const processFiles = (files: File[]) => {
    const validFiles = files.filter((file) => {
      const isValidType =
        file.name.toLowerCase().endsWith(".xlsx") ||
        file.name.toLowerCase().endsWith(".xls");
      if (!isValidType) {
        showResult(
          `Invalid file type: ${file.name}. Please select only XLSX or XLS files.`,
          false
        );
      }
      return isValidType;
    });

    setFormData((prev) => ({
      ...prev,
      csv_files: validFiles,
    }));

     if (formData.certificate_category === "domestic") {
       void parseDomesticXlsxFiles(validFiles);
     }

    if (validFiles.length !== files.length) {
      showResult(
        `${
          files.length - validFiles.length
        } file(s) were rejected. Only XLSX/XLS files are accepted.`,
        false
      );
    } else if (validFiles.length > 0) {
      setResult("");
    }
  };

  const handleLogoChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] || null;
    setFormData((prev) => ({
      ...prev,
      company_logo: file,
    }));
  };

  const parseNonMeatDocxFile = async (file: File) => {
    setNonMeatDocxError("");
    setNonMeatDocxParsing(true);
    try {
      const fileBase64 = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => {
          const result = reader.result as string;
          const parts = result.split(",");
          if (parts.length < 2) { reject(new Error("Invalid base64 format")); return; }
          resolve(parts[1]);
        };
        reader.onerror = reject;
        reader.readAsDataURL(file);
      });

      const auth_token =
        localStorage.getItem("hco_session_token") || (await authService.getAccessToken()) || "";

      const resp = await fetch(`${getApiUrl()}/export-non-meat/parse-docx`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          filename: file.name,
          file_data: fileBase64,
          auth_token,
        }),
      });

      const data = await resp.json();
      if (!resp.ok || !data?.processed) {
        setNonMeatDocxError(data?.message || "Failed to parse DOCX.");
        return;
      }

      const products = Array.isArray(data?.products) ? data.products : [];
      if (!products.length) {
        setNonMeatDocxError("No products found in the uploaded DOCX.");
        return;
      }

      setFormData((prev) => ({
        ...prev,
        products: products.map((p: any) => ({
          product_code: String(p?.product_code ?? ""),
          description: String(p?.description ?? ""),
          quantity: String(p?.quantity ?? ""),
          manufacture_date: String(p?.manufacture_date ?? ""),
          expiry_date: String(p?.expiry_date ?? ""),
          batch_number: String(p?.batch_number ?? ""),
          gross_weight: String(p?.gross_weight ?? ""),
          net_weight: String(p?.net_weight ?? ""),
          number_of_cases: String(p?.number_of_cases ?? ""),
        })),
      }));
    } catch (e) {
      setNonMeatDocxError("Failed to parse DOCX. Please verify the file format.");
    } finally {
      setNonMeatDocxParsing(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Validate required fields based on certificate category
    const missingFields: string[] = [];

    // Common required fields
    if (!formData.issue_date) missingFields.push("Issue Date");
    if (!formData.certificate_no) missingFields.push("Certificate Number");
    if (!formData.standards) missingFields.push("Standards");

    if (formData.certificate_category === "domestic") {
      // Halal Certificate validation
      if (!formData.company_name) missingFields.push("Company Name");
      if (!formData.company_address) missingFields.push("Company Address");
      if (!formData.sow) missingFields.push("Scope of Work");
      if (!formData.company_reg_no) missingFields.push("Company Registration Number");
      if (!formData.pu && !formData.au) {
        missingFields.push("PU or AU (at least one is required)");
      }
      if (formData.csv_files.length === 0) {
        missingFields.push("Product Files");
      }
    } else if (formData.certificate_category === "slaughterhouse") {
      // Slaughterhouse Certificate validation (no CSV files required - no annex page)
      if (!formData.company_name) missingFields.push("Company Name");
      if (!formData.company_address) missingFields.push("Company Address");
      if (!formData.sow) missingFields.push("Scope of Work");
      if (!formData.company_reg_no) missingFields.push("Company Registration Number");
      if (!formData.pu && !formData.au) {
        missingFields.push("PU or AU (at least one is required)");
      }
      // Note: No CSV/product files required for slaughterhouse certificates
    } else if (formData.certificate_category === "export_meat") {
      // Meat Export validation
      if (!formData.country_of_origin) missingFields.push("Country of Origin");
      if (!formData.exporter_name) missingFields.push("Exporter");
      if (!formData.destination) missingFields.push("Destination");
      if (!formData.importer_name) missingFields.push("Importer");
      if (!formData.slaughter_date) missingFields.push("Date of Slaughter");
      if (!formData.abattoir_address) missingFields.push("Abattoir Address");
      if (!formData.meat_type) missingFields.push("Meat Type");
      if (!formData.meat_condition) missingFields.push("Condition of Meat");
    } else if (formData.certificate_category === "export_non_meat") {
      // Non-Meat Export validation
      if (!formData.country_of_origin) missingFields.push("Country of Origin");
      if (!formData.destination) missingFields.push("Destination");
      if (!formData.exporter_name) missingFields.push("Exporter");
      if (!formData.importer_name) missingFields.push("Importer");
      if (!formData.shipment_mode) missingFields.push("Mode of Shipment");
      if (!formData.export_products_per_page || formData.export_products_per_page < 1) {
        missingFields.push("Products per page");
      }
      if (formData.products.length === 0 || !formData.products[0].description) {
        missingFields.push("At least one product");
      }
    }

    if (missingFields.length > 0) {
      showResult(
        `Please fill in the following required fields: ${missingFields.join(", ")}`,
        false
      );
      return;
    }

    setLoading(true);
    setResult("");

    try {
      // Convert files to base64 if needed (for halal certificate)
      const xlsxFiles = [];
      if (formData.certificate_category === "domestic") {
        for (const file of formData.csv_files) {
          const fileBase64 = await new Promise<string>((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => {
              const result = reader.result as string;
              const parts = result.split(",");
              if (parts.length < 2) { reject(new Error("Invalid base64 format")); return; }
              resolve(parts[1]);
            };
            reader.onerror = reject;
            reader.readAsDataURL(file);
          });

          xlsxFiles.push({
            filename: file.name,
            data: fileBase64,
          });
        }
      }

      // Convert company logo to base64 if provided
      let companyLogoBase64 = null;
      if (formData.company_logo) {
        companyLogoBase64 = await new Promise<string>((resolve, reject) => {
          const reader = new FileReader();
          reader.onload = () => {
            const result = reader.result as string;
            const parts = result.split(",");
            if (parts.length < 2) { reject(new Error("Invalid base64 format")); return; }
            resolve(parts[1]);
          };
          reader.onerror = reject;
          reader.readAsDataURL(formData.company_logo!);
        });
      }

      const auth_token =
        localStorage.getItem("hco_session_token") || (await authService.getAccessToken()) || "";

      // Build request data based on certificate category
      let requestData: Record<string, unknown> = {
        certificate_no: formData.certificate_no,
        issue_date: formData.issue_date,
        standards: formData.standards,
        certificate_category: formData.certificate_category,
        cert_num_footer: formData.cert_num_footer,
        auth_token,
      };

      if (formData.certificate_category === "domestic") {
        Object.assign(requestData, {
          certificate_type: "domestic",
          company_name: formData.company_name,
          company_reg_no: formData.company_reg_no,
          company_address: formData.company_address,
          pu: formData.pu || "",
          au: formData.au || "",
          sow: formData.sow,
          validity_period: formData.validity_period,
          domestic_logo_1: formData.domestic_logo_1,
          domestic_logo_2: formData.domestic_logo_2,
          csv_files_count: formData.csv_files.length,
          text_color: "black",
          pu_au_text: "",
          xlsx_files: xlsxFiles,
          annex_layout_options:
            domesticSchema === "name_only"
              ? {
                  rows: domesticLayout.rows,
                  columns: domesticLayout.columns,
                }
              : domesticSchema === "code_name_packaging"
                ? {
                    products_per_page: domesticLayout.products_per_page,
                    columns: 3,
                  }
                : domesticSchema === "code_name"
                  ? {
                      products_per_page: domesticLayout.products_per_page,
                      columns: domesticLayout.columns,
                    }
                  : {},
          company_logo: companyLogoBase64
            ? {
                filename: formData.company_logo!.name,
                data: companyLogoBase64,
                content_type: formData.company_logo!.type,
              }
            : null,
        });
      } else if (formData.certificate_category === "export_meat") {
        requestData = {
          certificate_no: formData.certificate_no,
          issue_date: formData.issue_date,
          standards: formData.standards,
          certificate_category: "export_meat",
          cert_num_footer: formData.cert_num_footer,
          auth_token,
          country_of_origin: formData.country_of_origin,
          exporter_name: formData.exporter_name,
          destination: formData.destination,
          importer_name: formData.importer_name,
          export_logo_option: formData.export_logo_option,
          export_signature_option: formData.export_signature_option,
          slaughter_date: formData.slaughter_date,
          producer_name: formData.producer_name,
          expiry_date: formData.expiry_date,
          abattoir_address: formData.abattoir_address,
          gross_weight: formData.gross_weight,
          number_of_carcasses: formData.number_of_carcasses,
          net_weight: formData.net_weight,
          number_of_boxes: formData.number_of_boxes,
          batch_reference: formData.batch_reference,
          halal_cert_number: formData.halal_cert_number,
          vet_cert_number: formData.vet_cert_number,
          destination_port: formData.destination_port,
          loading_port: formData.loading_port,
          flight_number: formData.flight_number,
          meat_type: formData.meat_type,
          awb_number: formData.awb_number,
          meat_condition: formData.meat_condition,
          inspector_name: formData.inspector_name,
        };
      } else if (formData.certificate_category === "export_non_meat") {
        requestData = {
          certificate_no: formData.certificate_no,
          issue_date: formData.issue_date,
          standards: formData.standards,
          certificate_category: "export_non_meat",
          cert_num_footer: formData.cert_num_footer,
          auth_token,
          country_of_origin: formData.country_of_origin,
          destination: formData.destination,
          exporter_name: formData.exporter_name,
          importer_name: formData.importer_name,
          export_logo_option: formData.export_logo_option,
          export_signature_option: formData.export_signature_option,
          shipment_mode: formData.shipment_mode,
          invoice_no: formData.invoice_no,
          vet_health_cert_no: formData.vet_health_cert_no,
          products: formData.products.filter(p => p.description), // Filter out empty rows
          export_products_per_page: formData.export_products_per_page,
        };
      } else if (formData.certificate_category === "slaughterhouse") {
        // Slaughterhouse certificate - no product files needed (no annex page)
        Object.assign(requestData, {
          certificate_type: "slaughterhouse",
          company_name: formData.company_name,
          company_reg_no: formData.company_reg_no,
          company_address: formData.company_address,
          pu: formData.pu || "",
          au: formData.au || "",
          sow: formData.sow,
          pl: formData.pl || "",  // Product List content
          validity_period: formData.validity_period,
          text_color: "black",
          pu_au_text: "",
          // No xlsx_files for slaughterhouse - no annex page
          xlsx_files: [],
          company_logo: companyLogoBase64
            ? {
                filename: formData.company_logo!.name,
                data: companyLogoBase64,
                content_type: formData.company_logo!.type,
              }
            : null,
        });
      }

      const response = await fetch(`${getApiUrl()}/generate-certificate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(requestData),
      });

      const data: GenerateResult = await response.json();

      if (data.success || data.status === "success" || data.certificate_id) {
        showResult("Certificate generated successfully!", true);
        setDownloadUrl(data.download_url || "");
        // Reset form
        setFormData({
          issue_date: new Date().toISOString().split("T")[0],
          certificate_no: "",
          standards: "GSO 2055-1",
          certificate_category: "domestic",
          cert_num_footer: "",
          company_name: "",
          company_address: "",
          pu: "",
          au: "",
          sow: "",
          pl: "",
          validity_period: "1",
          company_reg_no: "",
          csv_files: [],
          company_logo: null,
          country_of_origin: "",
          destination: "",
          exporter_name: "",
          importer_name: "",
          export_logo_option: "enas",
          export_signature_option: "with",
          slaughter_date: "",
          producer_name: "",
          expiry_date: "",
          abattoir_address: "",
          gross_weight: "",
          number_of_carcasses: "",
          net_weight: "",
          number_of_boxes: "",
          batch_reference: "",
          halal_cert_number: "",
          vet_cert_number: "",
          destination_port: "",
          loading_port: "",
          flight_number: "",
          meat_type: "",
          awb_number: "",
          meat_condition: "",
          inspector_name: "",
          shipment_mode: "",
          invoice_no: "",
          vet_health_cert_no: "",
          products: [{ ...emptyProductRow }],
          export_products_per_page: 10,
          domestic_logo_1: "enas",
          domestic_logo_2: "none",
        });

         setDomesticSchema(null);
         setDomesticParsedRows([]);
         setDomesticParseError("");
         setDomesticParsing(false);
         setDomesticLayout({ rows: 5, columns: 2, products_per_page: 10 });
      } else {
        showResult(
          data.message || "Error generating certificate. Please try again.",
          false
        );
      }
    } catch (error) {
      console.error("Error:", error);
      showResult(
        "Error generating certificate. Please check if the server is running.",
        false
      );
    } finally {
      setLoading(false);
    }
  };

  const showResult = (message: string, isSuccess: boolean) => {
    setResult(`${message}|${isSuccess ? "success" : "error"}`);
  };

  const handleDownloadInputChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>
  ) => {
    const { name, value } = e.target;
    setDownloadData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleDownload = async (e: React.FormEvent) => {
    e.preventDefault();

    const certNo = downloadData.certificate_no.trim();

    if (!certNo) {
      showDownloadResult("Please enter a certificate number.", false);
      return;
    }

    if (certNo.length < 3) {
      showDownloadResult("Please enter a valid certificate number (minimum 3 characters).", false);
      return;
    }

    setDownloadLoading(true);
    setDownloadResult("");
    setDownloadUrl("");

    try {
      const setLinkOnly = (url: string, filename?: string) => {
        setDownloadUrl(url);
        showDownloadResult(
          `Certificate found! Click the link below to open/download: ${filename || `${certNo}.pdf`}`,
          true
        );
      };

      const result = await fetch(`${getApiUrl()}/certificate/download`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          certificate_no: certNo,
          file_type: downloadData.file_type
        }),
      });

      const contentType = result.headers.get("content-type");
      if (contentType && contentType.includes("application/pdf")) {
        const blob = await result.blob();
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = `${certNo}.pdf`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);

        showDownloadResult(`Certificate ${certNo}.pdf downloaded successfully!`, true);
        return;
      }

      const responseText = await result.text();

      try {
        const jsonData = JSON.parse(responseText);
        if (jsonData.download_url) {
          setLinkOnly(jsonData.download_url, jsonData.filename);
          return;
        }
        if (jsonData.found && jsonData.file_data) {
          const byteCharacters = atob(jsonData.file_data);
          const byteNumbers = new Array(byteCharacters.length);
          for (let i = 0; i < byteCharacters.length; i++) {
            byteNumbers[i] = byteCharacters.charCodeAt(i);
          }
          const byteArray = new Uint8Array(byteNumbers);
          const blob = new Blob([byteArray], { type: "application/pdf" });

          const url = window.URL.createObjectURL(blob);
          const link = document.createElement("a");
          link.href = url;
          link.download = jsonData.filename || `${certNo}.pdf`;
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
          window.URL.revokeObjectURL(url);

          showDownloadResult(`Certificate ${jsonData.filename || `${certNo}.pdf`} downloaded successfully!`, true);
          return;
        }
        if (!jsonData.found) {
          showDownloadResult(`Certificate "${certNo}" not found: ${jsonData.message || "Please check the certificate number."}`, false);
          return;
        }
      } catch {
        showDownloadResult("Invalid response format from server. Please try again.", false);
      }
    } catch (error) {
      console.error("Download error:", error);
      showDownloadResult("Error downloading certificate. Please try again.", false);
    } finally {
      setDownloadLoading(false);
    }
  };

  const showDownloadResult = (message: string, isSuccess: boolean) => {
    setDownloadResult(`${message}|${isSuccess ? "success" : "error"}`);
  };

  const [message, type = "unknown"] = (result || "").split("|");
  const [downloadMessage, downloadType = "unknown"] = (downloadResult || "").split("|");

  // Get category display name
  const getCategoryDisplayName = (category: CertificateCategory): string => {
    switch (category) {
      case "domestic": return "Domestic";
      case "export_meat": return "Export - Meat";
      case "export_non_meat": return "Export - Non-Meat";
      case "slaughterhouse": return "Slaughterhouse";
      default: return "Halal Certificate";
    }
  };

  // Render form fields based on certificate category
  const renderCategorySpecificFields = () => {
    switch (formData.certificate_category) {
      case "domestic":
        return renderHalalCertificateFields();
      case "export_meat":
        return renderMeatExportFields();
      case "export_non_meat":
        return renderNonMeatExportFields();
      case "slaughterhouse":
        return renderSlaughterhouseFields();
      default:
        return renderHalalCertificateFields();
    }
  };

  const renderSlaughterhouseFields = () => (
    <>
      {/* Company Info */}
      <div className="bg-[#f7fbf8] border border-[#e0efe4] p-6 sm:p-8 shadow-sm">
        <h3 className="text-lg font-semibold text-[#4f8f5e] font-quicksand mb-6">
          Company Information
        </h3>
        <div className="grid gap-6 md:grid-cols-2">
          <InputField
            label="Company Name"
            name="company_name"
            value={formData.company_name}
            onChange={handleInputChange}
            required
          />
          <InputField
            label="Registration No"
            name="company_reg_no"
            value={formData.company_reg_no}
            onChange={handleInputChange}
            required
          />
        </div>
        <div className="mt-6">
          <TextareaField
            label="Company Address"
            name="company_address"
            value={formData.company_address}
            onChange={handleInputChange}
            rows={2}
            required
            warningText={companyAddressWarning}
          />
        </div>
      </div>

      {/* Certificate Details */}
      <div className="bg-[#f7fbf8] border border-[#e0efe4] p-6 sm:p-8 shadow-sm">
        <h3 className="text-lg font-semibold text-[#4f8f5e] font-quicksand mb-6">
          Certificate Details
        </h3>
        <div className="grid gap-6 md:grid-cols-2">
          <div className="flex flex-col">
            <label className="text-sm font-medium text-[#4f8f5e] mb-2 font-quicksand">
              Validity Period <span className="text-[#4f8f5e]">*</span>
            </label>
            <select
              name="validity_period"
              value={formData.validity_period}
              onChange={handleInputChange}
              className="h-12 bg-[#e8f0eb] text-[#4f8f5e] px-4 text-sm outline-none"
              required
            >
              <option value="1">1 Year</option>
              <option value="2">2 Years</option>
              <option value="3">3 Years</option>
            </select>
          </div>
        </div>
        <div className="grid gap-6 md:grid-cols-2 mt-6">
          <InputField
            label="Production Unit"
            name="pu"
            value={formData.pu}
            onChange={(e) => {
              const value = e.target.value;
              setFormData((prev) => ({
                ...prev,
                pu: value,
                au: value ? "" : prev.au,
              }));
            }}
            placeholder="Optional if AU provided"
            disabled={auHasValue}
          />
          <InputField
            label="Administrative Unit"
            name="au"
            value={formData.au}
            onChange={(e) => {
              const value = e.target.value;
              setFormData((prev) => ({
                ...prev,
                au: value,
                pu: value ? "" : prev.pu,
              }));
            }}
            placeholder="Optional if PU provided"
            disabled={puHasValue}
          />
        </div>
        <div className="mt-6">
          <TextareaField
            label="Scope of Work"
            name="sow"
            value={formData.sow}
            onChange={handleInputChange}
            rows={2}
            required
            placeholder="e.g., Slaughtering of Halal animals"
          />
        </div>
        <div className="mt-6">
          <TextareaField
            label="Product List (PL)"
            name="pl"
            value={formData.pl}
            onChange={handleInputChange}
            rows={2}
            placeholder="e.g., Halal slaughtered chicken, lamb, beef"
          />
        </div>
      </div>


      {/* Company Logo */}
      <div className="bg-[#f7fbf8] border border-[#e0efe4] p-6 sm:p-8 shadow-sm">
        <h3 className="text-lg font-semibold text-[#4f8f5e] font-quicksand mb-6">
          Company Logo (Optional)
        </h3>
        <div>
          <p className="text-sm text-[#7aa487] mb-4">
            Add your company logo to personalize the certificate.
          </p>
          <div
            className="cursor-pointer border border-dashed rounded-none px-6 py-6 bg-[#f9fcfa] border-[#c7ddcf]"
            onClick={() =>
              document.getElementById("companyLogo")?.click()
            }
          >
            {formData.company_logo ? (
              <div className="flex flex-col items-center gap-3 text-[#4f8f5e]">
                <img
                  src={URL.createObjectURL(formData.company_logo)}
                  alt="Company Logo Preview"
                  className="h-24 object-contain"
                />
                <p className="text-sm">{formData.company_logo.name}</p>
                <button
                  type="button"
                  className="text-xs text-[#c85c5c] underline"
                  onClick={(e) => {
                    e.stopPropagation();
                    setFormData((prev) => ({
                      ...prev,
                      company_logo: null,
                    }));
                  }}
                >
                  Remove logo
                </button>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-2 text-[#7aa487]">
                <div className="h-12 w-12 rounded-full bg-[#e0efe4] flex items-center justify-center text-[#4f8f5e]">
                  <span role="img" aria-label="image">🖼️</span>
                </div>
                <p className="text-sm font-medium text-[#4f8f5e] font-quicksand">
                  Click to upload company logo
                </p>
                <p className="text-xs">
                  Supported: JPG, PNG, GIF (max 5MB)
                </p>
              </div>
            )}
            <input
              type="file"
              id="companyLogo"
              name="company_logo"
              accept="image/*"
              onChange={handleLogoChange}
              style={{ display: "none" }}
            />
          </div>
        </div>
      </div>
    </>
  );

  const renderHalalCertificateFields = () => (
    <>
      {/* Company Info */}
      <div className="bg-[#f7fbf8] border border-[#e0efe4] p-6 sm:p-8 shadow-sm">
        <h3 className="text-lg font-semibold text-[#4f8f5e] font-quicksand mb-6">
          Company Information
        </h3>
        <div className="grid gap-6 md:grid-cols-2">
          <InputField
            label="Company Name"
            name="company_name"
            value={formData.company_name}
            onChange={handleInputChange}
            required
          />
          <InputField
            label="Registration No"
            name="company_reg_no"
            value={formData.company_reg_no}
            onChange={handleInputChange}
            required
          />
        </div>
        <div className="mt-6">
          <TextareaField
            label="Company Address"
            name="company_address"
            value={formData.company_address}
            onChange={handleInputChange}
            rows={2}
            required
            warningText={companyAddressWarning}
          />
        </div>
      </div>

      {/* Certificate Details */}
      <div className="bg-[#f7fbf8] border border-[#e0efe4] p-6 sm:p-8 shadow-sm">
        <h3 className="text-lg font-semibold text-[#4f8f5e] font-quicksand mb-6">
          Certificate Details
        </h3>
        <div className="grid gap-6 md:grid-cols-3">
          <div className="flex flex-col">
            <label className="text-sm font-medium text-[#4f8f5e] mb-2 font-quicksand">
              Validity Period <span className="text-[#4f8f5e]">*</span>
            </label>
            <select
              name="validity_period"
              value={formData.validity_period}
              onChange={handleInputChange}
              className="h-12 bg-[#e8f0eb] text-[#4f8f5e] px-4 text-sm outline-none"
              required
            >
              <option value="1">1 Year</option>
              <option value="2">2 Years</option>
              <option value="3">3 Years</option>
            </select>
          </div>
          <div className="flex flex-col">
            <label className="text-sm font-medium text-[#4f8f5e] mb-2 font-quicksand">
              Accreditation Logo 1
            </label>
            <select
              value={formData.domestic_logo_1}
              onChange={(e) => {
                const val = e.target.value as DomesticLogoOption;
                setFormData((prev) => ({
                  ...prev,
                  domestic_logo_1: val,
                  domestic_logo_2: val !== "none" && prev.domestic_logo_2 === val ? "none" : prev.domestic_logo_2,
                }));
              }}
              className="h-12 bg-[#e8f0eb] text-[#4f8f5e] px-4 text-sm outline-none"
            >
              <option value="gac">GAC</option>
              <option value="enas">ENAS</option>
              <option value="none">No Logo</option>
            </select>
          </div>
          <div className="flex flex-col">
            <label className="text-sm font-medium text-[#4f8f5e] mb-2 font-quicksand">
              Accreditation Logo 2 (Optional)
            </label>
            <select
              value={formData.domestic_logo_2}
              onChange={(e) => {
                const val = e.target.value as DomesticLogoOption;
                setFormData((prev) => ({
                  ...prev,
                  domestic_logo_2: val,
                  domestic_logo_1: val !== "none" && prev.domestic_logo_1 === val ? "none" : prev.domestic_logo_1,
                }));
              }}
              className="h-12 bg-[#e8f0eb] text-[#4f8f5e] px-4 text-sm outline-none"
            >
              <option value="none">No Logo</option>
              {formData.domestic_logo_1 !== "gac" && <option value="gac">GAC</option>}
              {formData.domestic_logo_1 !== "enas" && <option value="enas">ENAS</option>}
            </select>
          </div>
        </div>
        <div className="grid gap-6 md:grid-cols-2 mt-6">
          <InputField
            label="Production Unit"
            name="pu"
            value={formData.pu}
            onChange={(e) => {
              const value = e.target.value;
              setFormData((prev) => ({
                ...prev,
                pu: value,
                au: value ? "" : prev.au,
              }));
            }}
            placeholder="Optional if AU provided"
            disabled={auHasValue}
          />
          <InputField
            label="Administrative Unit"
            name="au"
            value={formData.au}
            onChange={(e) => {
              const value = e.target.value;
              setFormData((prev) => ({
                ...prev,
                au: value,
                pu: value ? "" : prev.pu,
              }));
            }}
            placeholder="Optional if PU provided"
            disabled={puHasValue}
          />
        </div>
        <div className="mt-6">
          <TextareaField
            label="Scope of Work"
            name="sow"
            value={formData.sow}
            onChange={handleInputChange}
            rows={2}
            required
          />
        </div>
      </div>

      {/* Product Files */}
      <div className="bg-[#f7fbf8] border border-[#e0efe4] p-6 sm:p-8 shadow-sm">
        <h3 className="text-lg font-semibold text-[#4f8f5e] font-quicksand mb-6">
          Product Files
        </h3>
        <div
          className={`cursor-pointer border border-dashed rounded-none px-6 py-8 text-center transition-colors ${
            dragOver
              ? "bg-[#e8f5ed] border-[#4f8f5e]"
              : "bg-[#f9fcfa] border-[#c7ddcf]"
          }`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => document.getElementById("csvFiles")?.click()}
        >
          <div className="flex flex-col items-center gap-3 text-[#4f8f5e]">
            <div className="h-12 w-12 rounded-full bg-[#e0efe4] flex items-center justify-center">
              <span role="img" aria-label="folder">📁</span>
            </div>
            <p className="text-sm font-medium font-quicksand">
              Product Files (XLSX){" "}
              <span className="text-[#4f8f5e]">*</span>
            </p>
            <p className="text-xs text-[#7aa487]">
              {dragOver
                ? "Drop files here"
                : "Click to select or drag & drop XLSX files"}
            </p>
            {formData.csv_files.length > 0 && (
              <p className="text-xs text-[#4f8f5e] mt-1">
                {formData.csv_files.length} file
                {formData.csv_files.length !== 1 ? "s" : ""} selected
              </p>
            )}
          </div>
          <input
            type="file"
            id="csvFiles"
            name="csv_files"
            onChange={handleFileChange}
            accept=".xlsx,.xls"
            multiple
            required
            style={{ display: "none" }}
          />
        </div>

        {formData.certificate_category === "domestic" && (domesticParsing || domesticParseError || domesticParsedRows.length > 0) && (
          <div className="mt-6">
            <div className="text-sm text-[#4f8f5e] font-quicksand font-medium mb-2">File Preview</div>
            {domesticParsing && <div className="text-xs text-[#7aa487]">Reading XLSX...</div>}
            {!domesticParsing && domesticParseError && (
              <div className="text-xs text-[#c85c5c]">{domesticParseError}</div>
            )}
            {!domesticParsing && !domesticParseError && domesticSchema && (
              <div className="text-xs text-[#7aa487]">
                Detected format:{" "}
                {domesticSchema === "name_only"
                  ? "Name only"
                  : domesticSchema === "code_name_packaging"
                    ? "Product code + Product name + Packaging details"
                    : "Product code + Product name"}{" "}
                ({domesticParsedRows.length} rows)
              </div>
            )}

            {!domesticParsing && domesticParsedRows.length > 0 && (
              <div className="mt-3 overflow-x-auto border border-[#e0efe4] bg-white">
                <table className="min-w-full text-xs">
                  <thead className="bg-[#f7fbf8] text-[#4f8f5e]">
                    <tr>
                      {(domesticSchema === "code_name" || domesticSchema === "code_name_packaging") && (
                        <th className="text-left p-2 border-b border-[#e0efe4]">Product Code</th>
                      )}
                      <th className="text-left p-2 border-b border-[#e0efe4]">Product Name</th>
                      {domesticSchema === "code_name_packaging" && (
                        <th className="text-left p-2 border-b border-[#e0efe4]">Packaging Details</th>
                      )}
                    </tr>
                  </thead>
                  <tbody>
                    {domesticParsedRows.slice(0, 10).map((row, idx) => (
                      <tr key={idx} className="text-[#4f8f5e]">
                        {(domesticSchema === "code_name" || domesticSchema === "code_name_packaging") && (
                          <td className="p-2 border-b border-[#e0efe4]">{row.product_code || ""}</td>
                        )}
                        <td className="p-2 border-b border-[#e0efe4]">{row.product_name}</td>
                        {domesticSchema === "code_name_packaging" && (
                          <td className="p-2 border-b border-[#e0efe4]">{row.packaging_details || ""}</td>
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {formData.certificate_category === "domestic" && domesticSchema && (
          <div className="mt-6 border border-[#e0efe4] bg-[#f9fcfa] p-4">
            <div className="text-sm text-[#4f8f5e] font-quicksand font-semibold mb-4">Annex Layout</div>

            {domesticSchema === "name_only" ? (
              <div className="grid gap-4 md:grid-cols-2">
                <div className="flex flex-col">
                  <label className="text-xs sm:text-sm font-medium text-[#4f8f5e] mb-2 font-quicksand">
                    Columns per page
                  </label>
                  <input
                    type="text"
                    inputMode="numeric"
                    pattern="[0-9]*"
                    value={domesticColumnsInput}
                    onChange={(e) => {
                      const raw = e.target.value;

                      if (raw === "") {
                        setDomesticColumnsInput("");
                        return;
                      }

                      if (!/^\d+$/.test(raw)) return;
                      setDomesticColumnsInput(raw);
                    }}
                    onBlur={() => {
                      const parsed = Number.parseInt(domesticColumnsInput, 10);
                      const columns = Math.min(6, Math.max(1, Number.isFinite(parsed) ? parsed : 1));
                      setDomesticLayout((prev) => ({
                        ...prev,
                        columns,
                        products_per_page: columns * prev.rows,
                      }));
                    }}
                    className="h-10 sm:h-12 bg-[#e8f0eb] text-[#4f8f5e] px-3 sm:px-4 text-xs sm:text-sm outline-none font-quicksand"
                  />
                  {domesticLayoutWarnings.columns && (
                    <div className="mt-1 text-xs text-[#c85c5c]">
                      Please make sure it is under 4. More than 4 can cause overlapping in certificate fields.
                    </div>
                  )}
                </div>
                <div className="flex flex-col">
                  <label className="text-xs sm:text-sm font-medium text-[#4f8f5e] mb-2 font-quicksand">
                    Rows per column
                  </label>
                  <input
                    type="text"
                    inputMode="numeric"
                    pattern="[0-9]*"
                    value={domesticRowsInput}
                    onChange={(e) => {
                      const raw = e.target.value;

                      if (raw === "") {
                        setDomesticRowsInput("");
                        return;
                      }

                      if (!/^\d+$/.test(raw)) return;
                      setDomesticRowsInput(raw);
                    }}
                    onBlur={() => {
                      const parsed = Number.parseInt(domesticRowsInput, 10);
                      const rows = Math.min(30, Math.max(1, Number.isFinite(parsed) ? parsed : 1));
                      setDomesticLayout((prev) => ({
                        ...prev,
                        rows,
                        products_per_page: prev.columns * rows,
                      }));
                    }}
                    className="h-10 sm:h-12 bg-[#e8f0eb] text-[#4f8f5e] px-3 sm:px-4 text-xs sm:text-sm outline-none font-quicksand"
                  />
                  {domesticLayoutWarnings.rows && (
                    <div className="mt-1 text-xs text-[#c85c5c]">
                      Please keep it 10 or below. More than 10 can overlap with the footer on some pages.
                    </div>
                  )}
                </div>
                <div className="text-xs text-[#7aa487] md:col-span-2">
                  Products per page: {domesticColumnsPreview * domesticRowsPreview}
                </div>
              </div>
            ) : (
              <div className="grid gap-4 md:grid-cols-2">
                <div className="flex flex-col">
                  <label className="text-xs sm:text-sm font-medium text-[#4f8f5e] mb-2 font-quicksand">
                    Table Columns
                  </label>
                  <select
                    value={domesticLayout.columns}
                    onChange={(e) => {
                      const columns = Number(e.target.value || 2);
                      setDomesticLayout((prev) => ({
                        ...prev,
                        columns,
                        products_per_page: columns === 3 ? 10 : columns === 2 ? 10 : 16,
                      }));
                    }}
                    className="h-10 sm:h-12 bg-[#e8f0eb] text-[#4f8f5e] px-3 sm:px-4 text-xs sm:text-sm outline-none"
                  >
                    <option value={2}>2 columns (Code | Name)</option>
                    <option value={3}>3 columns (Code | Name | Packaging)</option>
                    <option value={4}>4 columns (Code/Name + Code/Name)</option>
                  </select>
                </div>
                <div className="flex flex-col">
                  <label className="text-xs sm:text-sm font-medium text-[#4f8f5e] mb-2 font-quicksand">
                    Products per page
                  </label>
                  <input
                    type="text"
                    inputMode="numeric"
                    pattern="[0-9]*"
                    value={domesticProductsPerPageInput}
                    onChange={(e) => {
                      const raw = e.target.value;

                      if (raw === "") {
                        setDomesticProductsPerPageInput("");
                        return;
                      }

                      if (!/^\d+$/.test(raw)) return;
                      setDomesticProductsPerPageInput(raw);
                    }}
                    onBlur={() => {
                      const parsed = Number.parseInt(domesticProductsPerPageInput, 10);
                      const products_per_page = Math.max(1, Number.isFinite(parsed) ? parsed : 1);
                      setDomesticLayout((prev) => ({
                        ...prev,
                        products_per_page,
                      }));
                    }}
                    className="h-10 sm:h-12 bg-[#e8f0eb] text-[#4f8f5e] px-3 sm:px-4 text-xs sm:text-sm outline-none font-quicksand"
                  />
                  {domesticLayoutWarnings.productsPerPage && (
                    <div className="mt-1 text-xs text-[#c85c5c]">
                      Please keep it {domesticProductsPerPageLimit} or below. More than {domesticProductsPerPageLimit} can overlap with the footer on some pages.
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Company Logo */}
      <div className="bg-[#f7fbf8] border border-[#e0efe4] p-6 sm:p-8 shadow-sm">
        <h3 className="text-lg font-semibold text-[#4f8f5e] font-quicksand mb-6">
          Company Logo (Optional)
        </h3>
        <div>
          <p className="text-sm text-[#7aa487] mb-4">
            Add your company logo to personalize the certificate.
          </p>
          <div
            className="cursor-pointer border border-dashed rounded-none px-6 py-6 bg-[#f9fcfa] border-[#c7ddcf]"
            onClick={() =>
              document.getElementById("companyLogo")?.click()
            }
          >
            {formData.company_logo ? (
              <div className="flex flex-col items-center gap-3 text-[#4f8f5e]">
                <img
                  src={URL.createObjectURL(formData.company_logo)}
                  alt="Company Logo Preview"
                  className="h-24 object-contain"
                />
                <p className="text-sm">{formData.company_logo.name}</p>
                <button
                  type="button"
                  className="text-xs text-[#c85c5c] underline"
                  onClick={(e) => {
                    e.stopPropagation();
                    setFormData((prev) => ({
                      ...prev,
                      company_logo: null,
                    }));
                  }}
                >
                  Remove logo
                </button>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-2 text-[#7aa487]">
                <div className="h-12 w-12 rounded-full bg-[#e0efe4] flex items-center justify-center text-[#4f8f5e]">
                  <span role="img" aria-label="image">🖼️</span>
                </div>
                <p className="text-sm font-medium text-[#4f8f5e] font-quicksand">
                  Click to upload company logo
                </p>
                <p className="text-xs">
                  Supported: JPG, PNG, GIF (max 5MB)
                </p>
              </div>
            )}
            <input
              type="file"
              id="companyLogo"
              name="company_logo"
              accept="image/*"
              onChange={handleLogoChange}
              style={{ display: "none" }}
            />
          </div>
        </div>
      </div>
    </>
  );

  const renderMeatExportFields = () => (
    <>
      {/* Header Information */}
      <div className="bg-[#f7fbf8] border border-[#e0efe4] p-6 sm:p-8 shadow-sm">
        <h3 className="text-lg font-semibold text-[#4f8f5e] font-quicksand mb-6">
          Header Information
        </h3>
        <div className="grid gap-6 md:grid-cols-2">
          <InputField
            label="Country of Origin"
            name="country_of_origin"
            value={formData.country_of_origin}
            onChange={handleInputChange}
            placeholder="e.g., UNITED KINGDOM"
            required
          />
          <InputField
            label="Destination"
            name="destination"
            value={formData.destination}
            onChange={handleInputChange}
            placeholder="e.g., Saudi Arabia"
            required
          />
          <InputField
            label="Exporter"
            name="exporter_name"
            value={formData.exporter_name}
            onChange={handleInputChange}
            placeholder="Full company name with location"
            required
            warningText={exporterWarning}
          />
          <InputField
            label="Importer"
            name="importer_name"
            value={formData.importer_name}
            onChange={handleInputChange}
            placeholder="Full name and address"
            required
            warningText={importerWarning}
          />
        </div>
      </div>

      {renderExportOptions()}

      {/* Consignment Information */}
      <div className="bg-[#f7fbf8] border border-[#e0efe4] p-6 sm:p-8 shadow-sm">
        <h3 className="text-lg font-semibold text-[#4f8f5e] font-quicksand mb-6">
          Consignment Information
        </h3>
        <div className="grid gap-6 md:grid-cols-2">
          <InputField
            label="Date of Slaughter"
            name="slaughter_date"
            type="date"
            value={formData.slaughter_date}
            onChange={handleInputChange}
            required
          />
          <InputField
            label="Expiry Date"
            name="expiry_date"
            type="date"
            value={formData.expiry_date}
            onChange={handleInputChange}
          />
          <TextareaField
            label="Abattoir Address"
            name="abattoir_address"
            value={formData.abattoir_address}
            onChange={handleInputChange}
            rows={2}
            placeholder="Full address with approval number"
            required
            warningText={abattoirAddressWarning}
          />
        </div>
        <div className="grid gap-6 md:grid-cols-3 mt-6">
          <InputField
            label="Gross Weight (kg)"
            name="gross_weight"
            value={formData.gross_weight}
            onChange={handleInputChange}
            placeholder="e.g., 500 kg"
          />
          <InputField
            label="Net Weight (kg)"
            name="net_weight"
            value={formData.net_weight}
            onChange={handleInputChange}
            placeholder="e.g., 450 kg"
          />
          <InputField
            label="Number of Lamb Carcasses"
            name="number_of_carcasses"
            value={formData.number_of_carcasses}
            onChange={handleInputChange}
            placeholder="Quantity"
          />
        </div>
        <div className="grid gap-6 md:grid-cols-3 mt-6">
          <InputField
            label="Number of Boxes"
            name="number_of_boxes"
            value={formData.number_of_boxes}
            onChange={handleInputChange}
            placeholder="Quantity"
          />
          <InputField
            label="Batch Reference"
            name="batch_reference"
            value={formData.batch_reference}
            onChange={handleInputChange}
            placeholder="Reference number"
          />
          <InputField
            label="Halal Certificate Number"
            name="halal_cert_number"
            value={formData.halal_cert_number}
            onChange={handleInputChange}
            placeholder="Reference number"
          />
        </div>
      </div>

      {/* Shipping Information */}
      <div className="bg-[#f7fbf8] border border-[#e0efe4] p-6 sm:p-8 shadow-sm">
        <h3 className="text-lg font-semibold text-[#4f8f5e] font-quicksand mb-6">
          Shipping Information
        </h3>
        <div className="grid gap-6 md:grid-cols-2">
          <InputField
            label="Vet Certificate Number"
            name="vet_cert_number"
            value={formData.vet_cert_number}
            onChange={handleInputChange}
            placeholder="Veterinary certificate reference"
          />
          <InputField
            label="Destination Port"
            name="destination_port"
            value={formData.destination_port}
            onChange={handleInputChange}
            placeholder="Airport/seaport name"
          />
          <InputField
            label="Loading Port"
            name="loading_port"
            value={formData.loading_port}
            onChange={handleInputChange}
            placeholder="Departure port"
          />
          <InputField
            label="Flight Number"
            name="flight_number"
            value={formData.flight_number}
            onChange={handleInputChange}
            placeholder="Flight/shipment number"
          />
          <InputField
            label="AWB Number"
            name="awb_number"
            value={formData.awb_number}
            onChange={handleInputChange}
            placeholder="Air Waybill number"
          />
        </div>
      </div>

      {/* Meat Details */}
      <div className="bg-[#f7fbf8] border border-[#e0efe4] p-6 sm:p-8 shadow-sm">
        <h3 className="text-lg font-semibold text-[#4f8f5e] font-quicksand mb-6">
          Meat Details
        </h3>
        <div className="grid gap-6 md:grid-cols-2">
          <InputField
            label="Meat Type"
            name="meat_type"
            value={formData.meat_type}
            onChange={handleInputChange}
            placeholder="e.g., Lamb Carcasses"
            required
          />
          <div className="flex flex-col">
            <label className="text-sm font-medium text-[#4f8f5e] mb-2 font-quicksand">
              Condition of Meat <span className="text-[#4f8f5e]">*</span>
            </label>
            <select
              name="meat_condition"
              value={formData.meat_condition}
              onChange={handleInputChange}
              className="h-12 bg-[#e8f0eb] text-[#4f8f5e] px-4 text-sm outline-none"
              required
            >
              <option value="">Select condition</option>
              <option value="Chilled">Chilled</option>
              <option value="Frozen">Frozen</option>
              <option value="Fresh">Fresh</option>
            </select>
          </div>
          <InputField
            label="Halal Inspector / Auditor"
            name="inspector_name"
            value={formData.inspector_name}
            onChange={handleInputChange}
            placeholder="Name of inspector"
          />
        </div>
      </div>
    </>
  );

  const renderNonMeatExportFields = () => (
    <>
      {/* Header Information */}
      <div className="bg-[#f7fbf8] border border-[#e0efe4] p-6 sm:p-8 shadow-sm">
        <h3 className="text-lg font-semibold text-[#4f8f5e] font-quicksand mb-6">
          Header Information
        </h3>
        <div className="grid gap-6 md:grid-cols-2">
          <InputField
            label="Country of Origin"
            name="country_of_origin"
            value={formData.country_of_origin}
            onChange={handleInputChange}
            placeholder="e.g., UK"
            required
          />
          <InputField
            label="Destination"
            name="destination"
            value={formData.destination}
            onChange={handleInputChange}
            placeholder="e.g., Kuwait"
            required
          />
          <TextareaField
            label="Importer"
            name="importer_name"
            value={formData.importer_name}
            onChange={handleInputChange}
            rows={2}
            placeholder="Full company name and address"
            required
            warningText={importerWarning}
          />
          <TextareaField
            label="Exporter"
            name="exporter_name"
            value={formData.exporter_name}
            onChange={handleInputChange}
            rows={2}
            placeholder="Full company name and address"
            required
            warningText={exporterWarning}
          />
        </div>
        <div className="grid gap-6 md:grid-cols-3 mt-6">
          <div className="flex flex-col">
            <label className="text-sm font-medium text-[#4f8f5e] mb-2 font-quicksand">
              Mode of Shipment <span className="text-[#4f8f5e]">*</span>
            </label>
            <select
              name="shipment_mode"
              value={formData.shipment_mode}
              onChange={handleInputChange}
              className="h-12 bg-[#e8f0eb] text-[#4f8f5e] px-4 text-sm outline-none"
              required
            >
              <option value="">Select mode</option>
              <option value="By Air">By Air</option>
              <option value="By Sea">By Sea</option>
              <option value="By Land">By Land</option>
            </select>
          </div>
          <InputField
            label="Product Invoice No"
            name="invoice_no"
            value={formData.invoice_no}
            onChange={handleInputChange}
            placeholder="Invoice reference number"
          />
          <InputField
            label="Vet Health Cert. No"
            name="vet_health_cert_no"
            value={formData.vet_health_cert_no}
            onChange={handleInputChange}
            placeholder="If applicable"
          />
        </div>
      </div>

      {renderExportOptions()}

      {/* Products Table */}
      <div className="bg-[#f7fbf8] border border-[#e0efe4] p-6 sm:p-8 shadow-sm">
        <div className="flex justify-between items-center mb-6">
          <h3 className="text-lg font-semibold text-[#4f8f5e] font-quicksand">
            Details of Consignment - Products
          </h3>
          {nonMeatProductInputMode === "manual" ? (
            <button
              type="button"
              onClick={addProductRow}
              className="px-4 py-2 bg-[#4f8f5e] text-white text-sm font-medium rounded hover:bg-[#3f724d] transition-colors"
            >
              + Add Product
            </button>
          ) : null}
        </div>

        <div className="grid gap-4 md:grid-cols-2 mb-6">
          <div className="flex flex-col">
            <label className="text-sm font-medium text-[#4f8f5e] mb-2 font-quicksand">
              Product Input Method
            </label>
            <select
              value={nonMeatProductInputMode}
              onChange={(e) => {
                const mode = (e.target.value as "manual" | "docx") || "manual";
                setNonMeatProductInputMode(mode);
                setNonMeatDocxError("");
                setNonMeatDocxFile(null);
                if (mode === "manual") {
                  setFormData((prev) => ({
                    ...prev,
                    products: prev.products.length ? prev.products : [{ ...emptyProductRow }],
                  }));
                }
              }}
              className="h-12 bg-[#e8f0eb] text-[#4f8f5e] px-4 text-sm outline-none"
            >
              <option value="manual">Manual entry</option>
              <option value="docx">Upload DOCX</option>
            </select>
          </div>

          {nonMeatProductInputMode === "docx" ? (
            <div className="flex flex-col">
              <label className="text-sm font-medium text-[#4f8f5e] mb-2 font-quicksand">
                Upload DOCX
              </label>
              <input
                type="file"
                accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                onChange={(e) => {
                  const file = e.target.files?.[0] || null;
                  setNonMeatDocxFile(file);
                  if (file) {
                    void parseNonMeatDocxFile(file);
                  }
                }}
                className="h-12 bg-[#e8f0eb] text-[#4f8f5e] px-4 text-sm outline-none font-quicksand"
              />
              {nonMeatDocxParsing ? (
                <div className="text-xs text-[#7aa487] mt-2">Parsing DOCX...</div>
              ) : null}
              {nonMeatDocxError ? (
                <div className="text-xs text-[#c85c5c] mt-2">{nonMeatDocxError}</div>
              ) : null}
              {nonMeatDocxFile && !nonMeatDocxParsing && !nonMeatDocxError ? (
                <div className="text-xs text-[#7aa487] mt-2">Loaded: {nonMeatDocxFile.name}</div>
              ) : null}
            </div>
          ) : null}
        </div>

        <div className="grid gap-4 md:grid-cols-2 mb-6">
          <div className="flex flex-col">
            <label className="text-sm font-medium text-[#4f8f5e] mb-2 font-quicksand">
              Products per page
            </label>
            <input
              type="text"
              inputMode="numeric"
              pattern="[0-9]*"
              value={exportProductsPerPageInput}
              onChange={(e) => {
                const raw = e.target.value;

                if (raw === "") {
                  setExportProductsPerPageInput("");
                  return;
                }

                if (!/^\d+$/.test(raw)) return;
                setExportProductsPerPageInput(raw);
              }}
              onBlur={() => {
                const parsed = Number.parseInt(exportProductsPerPageInput, 10);
                const export_products_per_page = Math.min(
                  50,
                  Math.max(1, Number.isFinite(parsed) ? parsed : 10)
                );
                setFormData((prev) => ({
                  ...prev,
                  export_products_per_page,
                }));
              }}
              className="h-12 bg-[#e8f0eb] text-[#4f8f5e] px-4 text-sm outline-none font-quicksand"
            />
            <div className="text-xs text-[#7aa487] mt-2">
              Controls how many product rows are printed on each page.
            </div>
            {exportProductsPerPagePreview > 10 && (
              <div className="mt-1 text-xs text-[#c85c5c]">
                Please keep it 10 or below. More than 10 can overlap with the footer on some pages.
              </div>
            )}
          </div>
        </div>

        <div className="space-y-6">
          {formData.products.map((product, index) => (
            <div key={index} className="border border-[#e0efe4] p-4 rounded relative">
              {formData.products.length > 1 && (
                <button
                  type="button"
                  onClick={() => removeProductRow(index)}
                  className="absolute top-2 right-2 text-[#c85c5c] hover:text-[#a33] text-sm"
                >
                  Remove
                </button>
              )}
              <p className="text-sm font-medium text-[#4f8f5e] mb-4">Product {index + 1}</p>
              <div className="grid gap-4 md:grid-cols-3">
                <div className="flex flex-col">
                  <label className="text-xs font-medium text-[#4f8f5e] mb-1">Product Code</label>
                  <input
                    type="text"
                    value={product.product_code}
                    onChange={(e) => handleProductChange(index, "product_code", e.target.value)}
                    placeholder="e.g., ABEENG"
                    className="h-10 bg-[#e8f0eb] text-[#4f8f5e] px-3 text-xs placeholder-[#9bb7a4] outline-none"
                  />
                </div>
                <div className="flex flex-col md:col-span-2">
                  <label className="text-xs font-medium text-[#4f8f5e] mb-1">Description <span className="text-[#4f8f5e]">*</span></label>
                  <input
                    type="text"
                    value={product.description}
                    onChange={(e) => handleProductChange(index, "description", e.target.value)}
                    placeholder="Full product name and specifications"
                    className="h-10 bg-[#e8f0eb] text-[#4f8f5e] px-3 text-xs placeholder-[#9bb7a4] outline-none"
                    required={index === 0}
                  />
                </div>
              </div>
              <div className="grid gap-4 md:grid-cols-4 mt-4">
                <div className="flex flex-col">
                  <label className="text-xs font-medium text-[#4f8f5e] mb-1">Quantity (units)</label>
                  <input
                    type="text"
                    value={product.quantity}
                    onChange={(e) => handleProductChange(index, "quantity", e.target.value)}
                    placeholder="Number of units"
                    className="h-10 bg-[#e8f0eb] text-[#4f8f5e] px-3 text-xs placeholder-[#9bb7a4] outline-none"
                  />
                </div>
                <div className="flex flex-col">
                  <label className="text-xs font-medium text-[#4f8f5e] mb-1">Manufacture Date</label>
                  <input
                    type="date"
                    value={product.manufacture_date}
                    onChange={(e) => handleProductChange(index, "manufacture_date", e.target.value)}
                    className="h-10 bg-[#e8f0eb] text-[#4f8f5e] px-3 text-xs outline-none"
                  />
                </div>
                <div className="flex flex-col">
                  <label className="text-xs font-medium text-[#4f8f5e] mb-1">Expiry Date</label>
                  <input
                    type="date"
                    value={product.expiry_date}
                    onChange={(e) => handleProductChange(index, "expiry_date", e.target.value)}
                    className="h-10 bg-[#e8f0eb] text-[#4f8f5e] px-3 text-xs outline-none"
                  />
                </div>
                <div className="flex flex-col">
                  <label className="text-xs font-medium text-[#4f8f5e] mb-1">Batch Number</label>
                  <input
                    type="text"
                    value={product.batch_number}
                    onChange={(e) => handleProductChange(index, "batch_number", e.target.value)}
                    placeholder="e.g., P25217"
                    className="h-10 bg-[#e8f0eb] text-[#4f8f5e] px-3 text-xs placeholder-[#9bb7a4] outline-none"
                  />
                </div>
              </div>
              <div className="grid gap-4 md:grid-cols-3 mt-4">
                <div className="flex flex-col">
                  <label className="text-xs font-medium text-[#4f8f5e] mb-1">Gross Weight (kg)</label>
                  <input
                    type="text"
                    value={product.gross_weight}
                    onChange={(e) => handleProductChange(index, "gross_weight", e.target.value)}
                    placeholder="e.g., 54"
                    className="h-10 bg-[#e8f0eb] text-[#4f8f5e] px-3 text-xs placeholder-[#9bb7a4] outline-none"
                  />
                </div>
                <div className="flex flex-col">
                  <label className="text-xs font-medium text-[#4f8f5e] mb-1">Net Weight (kg)</label>
                  <input
                    type="text"
                    value={product.net_weight}
                    onChange={(e) => handleProductChange(index, "net_weight", e.target.value)}
                    placeholder="e.g., 74.7"
                    className="h-10 bg-[#e8f0eb] text-[#4f8f5e] px-3 text-xs placeholder-[#9bb7a4] outline-none"
                  />
                </div>
                <div className="flex flex-col">
                  <label className="text-xs font-medium text-[#4f8f5e] mb-1">Number of Cases</label>
                  <input
                    type="text"
                    value={product.number_of_cases}
                    onChange={(e) => handleProductChange(index, "number_of_cases", e.target.value)}
                    placeholder="Total boxes"
                    className="h-10 bg-[#e8f0eb] text-[#4f8f5e] px-3 text-xs placeholder-[#9bb7a4] outline-none"
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </>
  );

  return (
    <div className="min-h-screen bg-white">
      <div className="w-full bg-[#358743] text-white py-6 lg:py-10 text-center">
        <h2 className="text-xl sm:text-2xl lg:text-3xl font-semibold font-quicksand px-4">
          Generate Certificate
        </h2>
        <p className="mt-2 lg:mt-3 text-xs sm:text-sm lg:text-base max-w-3xl mx-auto opacity-90 px-4 font-quicksand">
          Fill in the required details to generate a certificate.
        </p>
      </div>

      <div className="py-6 lg:py-10 px-4 sm:px-6 lg:px-8">
        <div className="max-w-5xl mx-auto space-y-6 lg:space-y-10">
          <form onSubmit={handleSubmit} className="space-y-6 lg:space-y-8">
            {/* Certificate Category Selection */}
            <div className="bg-[#f7fbf8] border border-[#e0efe4] p-4 sm:p-6 lg:p-8 shadow-sm">
              <h3 className="text-base sm:text-lg font-semibold text-[#4f8f5e] font-quicksand mb-4 sm:mb-6">
                Certificate Category
              </h3>
              <div className="flex flex-col">
                <label className="text-sm font-medium text-[#4f8f5e] mb-2 font-quicksand">
                  Select Certificate Type <span className="text-[#4f8f5e]">*</span>
                </label>
                <select
                  name="certificate_category"
                  value={formData.certificate_category}
                  onChange={handleInputChange}
                  className="h-12 bg-[#e8f0eb] text-[#4f8f5e] px-4 text-sm outline-none font-quicksand"
                  required
                >
                  <option value="domestic">Domestic</option>
                  <option value="export_meat">Export - Meat</option>
                  <option value="export_non_meat">Export - Non-Meat</option>
                  <option value="slaughterhouse">Slaughterhouse</option>
                </select>
                <p className="text-xs text-[#7aa487] mt-2">
                  Selected: {getCategoryDisplayName(formData.certificate_category)}
                </p>
              </div>
            </div>

            {/* Certificate Info - Common fields */}
            <div className="bg-[#f7fbf8] border border-[#e0efe4] p-4 sm:p-6 lg:p-8 shadow-sm">
              <h3 className="text-base sm:text-lg font-semibold text-[#4f8f5e] font-quicksand mb-4 sm:mb-6">
                Certificate Information
              </h3>
              <div className="grid gap-4 sm:gap-6 md:grid-cols-2">
                <div className="flex flex-col">
                  <label className="text-sm font-medium text-[#4f8f5e] mb-2 font-quicksand">
                    Certificate Number <span className="text-[#4f8f5e]">*</span>
                  </label>
                  <div className="flex items-center bg-[#e8f0eb] text-[#4f8f5e] px-4 h-12">
                    <svg
                      width="18"
                      height="18"
                      viewBox="0 0 24 24"
                      fill="none"
                      className="mr-3 text-[#7aa487]"
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
                      name="certificate_no"
                      value={formData.certificate_no}
                      onChange={handleInputChange}
                      placeholder={formData.certificate_category.includes("export") ? "e.g., HCO/FF/20042022-FF658" : "e.g., HCO-2024-001"}
                      className="w-full h-full bg-transparent text-[#4f8f5e] px-2 sm:px-3 py-2 sm:py-3 outline-none text-xs sm:text-sm font-quicksand"
                    />
                  </div>
                </div>

                <div className="flex flex-col">
                  <label className="text-xs sm:text-sm font-medium text-[#4f8f5e] mb-2 font-quicksand">
                    Certificate Footer Number
                  </label>
                  <input
                    type="text"
                    name="cert_num_footer"
                    value={formData.cert_num_footer}
                    onChange={handleInputChange}
                    placeholder="Add Certificate Footer Number"
                    className="h-10 sm:h-12 bg-[#e8f0eb] text-[#4f8f5e] px-3 sm:px-4 text-xs sm:text-sm placeholder-[#9bb7a4] outline-none font-quicksand"
                  />
                </div>

                <div className="flex flex-col">
                  <label className="text-sm font-medium text-[#4f8f5e] mb-2 font-quicksand">
                    Issue Date <span className="text-[#4f8f5e]">*</span>
                  </label>
                  <div className="flex items-center bg-[#e8f0eb] text-[#4f8f5e] px-4 h-12">
                    <svg
                      width="18"
                      height="18"
                      viewBox="0 0 24 24"
                      fill="none"
                      className="mr-3 text-[#7aa487]"
                    >
                      <rect
                        x="3"
                        y="4"
                        width="18"
                        height="18"
                        rx="2"
                        ry="2"
                        stroke="currentColor"
                        strokeWidth="2"
                      />
                      <line
                        x1="16"
                        y1="2"
                        x2="16"
                        y2="6"
                        stroke="currentColor"
                        strokeWidth="2"
                      />
                      <line
                        x1="8"
                        y1="2"
                        x2="8"
                        y2="6"
                        stroke="currentColor"
                        strokeWidth="2"
                      />
                      <line
                        x1="3"
                        y1="10"
                        x2="21"
                        y2="10"
                        stroke="currentColor"
                        strokeWidth="2"
                      />
                    </svg>
                    <input
                      type="date"
                      name="issue_date"
                      value={formData.issue_date}
                      onChange={handleInputChange}
                      className="flex-1 bg-transparent outline-none text-sm"
                      required
                    />
                  </div>
                </div>
              </div>
              <div className="mt-4 sm:mt-6">
                <InputField
                  label="Standards"
                  name="standards"
                  value={formData.standards}
                  onChange={handleInputChange}
                  placeholder={formData.certificate_category.includes("export") ? "e.g., GSO 993/2015, GSO 2055-1/2015 Category-CV" : "e.g., GSO 2055-1"}
                  required
                />
              </div>
            </div>

            {/* Category-specific fields */}
            {renderCategorySpecificFields()}

            <div className="flex justify-center">
              <button
                type="submit"
                className="inline-flex items-center justify-center px-8 h-12 bg-[#4f8f5e] text-white text-sm font-medium font-quicksand tracking-wide hover:bg-[#3f724d] transition-colors disabled:bg-[#b8cbbf] disabled:cursor-not-allowed rounded-lg"
                disabled={loading}
              >
                {loading ? "Generating..." : `Generate ${getCategoryDisplayName(formData.certificate_category)}`}
              </button>
            </div>
          </form>

          {loading && (
            <div className="flex items-start gap-3 text-[#4f8f5e] text-sm">
              <div className="h-5 w-5 border-2 border-[#4f8f5e] border-t-transparent rounded-full animate-spin mt-0.5" />
              <div>
                <p className="font-medium">Generating certificate...</p>
                <p className="text-[#7aa487]">
                  Please wait while we process your request.
                </p>
              </div>
            </div>
          )}

          {result && (
            <div
              className={`border-l-4 px-4 py-3 text-sm ${
                type === "success"
                  ? "border-[#4f8f5e] bg-[#e8f5ed] text-[#2f5f3b]"
                  : "border-[#c85c5c] bg-[#fceced] text-[#8a3131]"
              }`}
            >
              {message}
              {downloadUrl && type === "success" && (
                <div className="mt-3">
                  <a
                    href={downloadUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="underline font-medium"
                  >
                    Download / Open generated certificate
                  </a>
                </div>
              )}
            </div>
          )}

          {/* Download Section */}
          <div className="bg-[#f7fbf8] border border-[#e0efe4] p-6 sm:p-8 shadow-sm">
            <h2 className="text-lg font-semibold text-[#4f8f5e] font-quicksand">
              Download Certificate
            </h2>
            <p className="mt-2 text-sm text-[#7aa487]">
              Enter a certificate number to download an existing certificate as
              PDF.
            </p>

            <form onSubmit={handleDownload} className="mt-6 space-y-6">
              <div className="flex flex-col max-w-md">
                <label className="text-sm font-medium text-[#4f8f5e] mb-2 font-quicksand">
                  Certificate Number <span className="text-[#4f8f5e]">*</span>
                </label>
                <input
                  type="text"
                  name="certificate_no"
                  value={downloadData.certificate_no}
                  onChange={handleDownloadInputChange}
                  placeholder="e.g., HCO-2024-001"
                  required
                  className="h-12 bg-[#e8f0eb] text-[#4f8f5e] px-4 text-sm placeholder-[#9bb7a4] outline-none font-quicksand"
                />
              </div>

              <button
                type="submit"
                className="inline-flex items-center justify-center px-8 h-11 bg-[#3a8f43] hover:text-amber-100 text-white text-sm font-medium font-quicksand tracking-wide hover:bg-[#3f724d] transition-colors disabled:bg-[#b8cbbf] disabled:cursor-not-allowed rounded-lg"
                disabled={downloadLoading}
              >
                {downloadLoading
                  ? "Downloading..."
                  : "Download Certificate (PDF)"}
              </button>
            </form>

            {downloadLoading && (
              <div className="mt-4 flex items-start gap-3 text-[#4f8f5e] text-sm">
                <div className="h-5 w-5 border-2 border-[#4f8f5e] border-t-transparent rounded-full animate-spin mt-0.5" />
                <div>
                  <p className="font-medium">Preparing download...</p>
                  <p className="text-[#7aa487]">
                    Please wait while we prepare your file.
                  </p>
                </div>
              </div>
            )}

            {downloadResult && (
              <div
                className={`mt-4 border-l-4 px-4 py-3 text-sm ${
                  downloadType === "success"
                    ? "border-[#4f8f5e] bg-[#e8f5ed] text-[#2f5f3b]"
                    : "border-[#c85c5c] bg-[#fceced] text-[#8a3131]"
                }`}
              >
                {downloadMessage}
                {downloadUrl && downloadType === "success" && (
                  <div className="mt-3">
                    <a
                      href={downloadUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="underline font-medium"
                    >
                      Open certificate in new tab
                    </a>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default GenerateCertificate;
