# HCO Agent (Backend)

Backend service for:
- **Public certificate validation** (no Microsoft login required)
- **Certificate generation** (Microsoft login required by default; restricted to users who can access the configured OneDrive folder)
- Optional **Microsoft OneDrive upload + Excel logging** via Microsoft Graph
- Optional **PostgreSQL storage** (falls back to local files if `DATABASE_URL` is not set)

The service runs on **port `8096`**.

## Quick start (Docker)

1) Create `hco-agent/.env` (example below).

2) Run:

```bash
cd hco-agent
docker compose up -d --build --force-recreate
```

3) View logs:

```bash
docker logs -f hco-agent-v3
```

Generated PDFs/JSONs are persisted to `hco-agent/generated_certificates/` by default (see `CERT_OUTPUT_DIR`).

## Local run (without Docker)

```bash
cd hco-agent
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python agent.py
```

## Environment variables

Create a `.env` file inside `hco-agent/`. All variables are optional unless marked **required**.

### Core
- **`AGENTVERSE_URL`**: Optional Agentverse URL (default in docker-compose is `https://agentverse.ai`).
- **`CERT_OUTPUT_DIR`**: Where fallback files are written/read when `DATABASE_URL` is not set. Default: `generated_certificates`.
- **`DATABASE_URL`**: PostgreSQL connection string (enables DB storage). If not set, the agent uses fallback JSON/PDF/PNG files under `CERT_OUTPUT_DIR`.

### AI / extraction (optional but recommended)
- **`OPENAI_API_KEY`**: Used for extracting products from uploaded Excel files during certificate generation.
- **`ANTHROPIC_API_KEY`**: Optional (used by some analysis flows depending on config).
- **`ASI_ONE_API_KEY`**: Optional (used by some certificate-number extraction flows).

### Google Sheets (optional)
- **`GOOGLE_SHEETS_URL`**: If provided, the agent can log/verify against Google Sheets. If empty, validation still works using DB/fallback files.

### Generation access control (recommended)
By default, **generation is restricted**.
- **`HCO_PUBLIC_GENERATION`**: If set to `true/1/yes`, generation is allowed without Microsoft login (**not recommended**).
- **`HCO_ALLOWED_LOGIN_EMAILS`**: Optional comma-separated allowlist (e.g. `user1@gmail.com,user2@domain.com`). If set, only these accounts can generate.
- **`HCO_ONEDRIVE_FOLDER_SHARE_URL`** (or `ONEDRIVE_FOLDER_SHARE_URL`): Share link to the OneDrive folder used for:
  - Checking whether a logged-in user has access (generation gate)
  - Uploading PDFs via Graph (when configured)

## Microsoft OneDrive + Excel logging (Microsoft Graph)

This is optional. If enabled, after generation the agent will:
- upload the generated PDF to the shared folder
- append a row to the Excel table

You must provide **share links**:
- **`HCO_ONEDRIVE_FOLDER_SHARE_URL`**: folder share link (recommended to use “Share → Copy link”)
- **`HCO_EXCEL_SHARE_URL`** (or `EXCEL_SHARE_URL`): Excel workbook share link
- **`HCO_EXCEL_TABLE_NAME`** (or `EXCEL_TABLE_NAME`): Excel table name inside the workbook (default: `Certificates`)

### Option A — Work/School (OneDrive for Business / SharePoint) with **app-only** auth

Set:
- **`MS_TENANT_ID`** (or `AZURE_TENANT_ID`)
- **`MS_CLIENT_ID`** (or `AZURE_CLIENT_ID`)
- **`MS_CLIENT_SECRET`** (or `AZURE_CLIENT_SECRET`)

Azure App Registration permissions (Application permissions; admin consent required):
- `Files.ReadWrite.All`
- `Sites.ReadWrite.All`

### Option B — Personal Microsoft account (OneDrive personal) with **refresh token**

Important: **personal OneDrive does not support app-only (client credentials)**. You must use delegated auth with a refresh token.

Set:
- **`MS_TENANT_ID=consumers`** (recommended for personal accounts)
- **`MS_CLIENT_ID`** (or `AZURE_CLIENT_ID`)
- **`MS_REFRESH_TOKEN`** (or `AZURE_REFRESH_TOKEN`)

App Registration requirements:
- Supported account types: **Personal Microsoft accounts**
- Delegated permissions:
  - `Files.ReadWrite`
  - `offline_access`
  - (Optional) `User.Read` (helpful for some `/auth/validate` flows; the backend tries to decode email from JWT first)

#### Getting the refresh token (device code flow)

Run this helper **once** (it prints a `MS_REFRESH_TOKEN=...` line):

```bash
cd hco-agent
export MS_TENANT_ID=consumers
export MS_CLIENT_ID=YOUR_AZURE_APP_CLIENT_ID
python ms_personal_auth_device_code.py
```

Then copy the printed token into `hco-agent/.env`:
- `MS_TENANT_ID=consumers`
- `MS_REFRESH_TOKEN=...`

Security note: a refresh token is sensitive. Don’t commit it, and rotate it if leaked.

## Example `.env`

```bash
# Core
CERT_OUTPUT_DIR=generated_certificates
# DATABASE_URL=postgresql://user:pass@host:5432/dbname

# AI (optional)
OPENAI_API_KEY=...
# ANTHROPIC_API_KEY=...
# ASI_ONE_API_KEY=...

# Optional Google Sheets logging/lookup
# GOOGLE_SHEETS_URL=https://...

# Access control (recommended)
HCO_PUBLIC_GENERATION=false
# HCO_ALLOWED_LOGIN_EMAILS=user1@gmail.com,user2@domain.com

# OneDrive folder + Excel workbook share links
HCO_ONEDRIVE_FOLDER_SHARE_URL=...
HCO_EXCEL_SHARE_URL=...
HCO_EXCEL_TABLE_NAME=Certificates

# Personal account (delegated) OR Work/School (app-only)
MS_TENANT_ID=consumers
MS_CLIENT_ID=...
MS_REFRESH_TOKEN=...
# MS_CLIENT_SECRET=...   # only for app-only work/school flow
```

## Quick API smoke tests

Certificate verify:

```bash
curl -s -X POST http://localhost:8096/certificate/verify \
  -H "Content-Type: application/json" \
  -d '{"certificate_no":"HCO/RAG/071afdsfasawsfasdfd"}'
```

Generate certificate (requires Microsoft token unless `HCO_PUBLIC_GENERATION=true`):

```bash
curl -s -X POST http://localhost:8096/generate-certificate \
  -H "Content-Type: application/json" \
  -d '{
    "certificate_no":"HCO/TEST/0001",
    "company_name":"ACME Ltd",
    "company_address":"123 Street",
    "company_reg_no":"REG-123",
    "issue_date":"2026-01-11",
    "standards":"MS1500:2019",
    "sow":"Food Processing",
    "validity_period":"3",
    "xlsx_files":[],
    "company_logo": null,
    "auth_token":"<MS_ACCESS_TOKEN_FROM_FRONTEND_LOGIN>"
  }'
```