# HCO - Halal Certificate Organisation Platform

A full-stack application for generating, verifying, and managing Halal certificates. The backend is a Python-based uAgent with REST endpoints; the frontend is a React + Vite application.

---

## Project Structure

```
HCO/
├── agents/          # Backend — Python uAgent (port 8096)
├── frontend/       # Frontend — React + Vite + TypeScript (port 5173)
└── README.md
```

---

## Prerequisites

- **Python** 3.11+
- **Node.js** 18+ and **npm** 9+
- **PostgreSQL** (optional — falls back to local JSON storage)
- **WeasyPrint** system dependencies (for PDF generation)
- **OpenAI API key** (required for certificate verification and product matching)
- **Microsoft Azure app registration** (optional — for Excel/OneDrive integration)

---

## Backend Setup (`agents/`)

### 1. Install system dependencies

WeasyPrint requires native libraries for PDF rendering:

```bash
# macOS
brew install cairo pango gdk-pixbuf libffi

# Ubuntu / Debian
sudo apt-get install -y build-essential libglib2.0-0 libcairo2 \
  libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 shared-mime-info
```

### 2. Create a virtual environment and install Python packages

```bash
cd agents
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in the required values:

#### Required

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key (used for verification, product matching, and chat) |

#### Certificate Storage (at least one recommended)

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string, e.g. `postgresql://user:pass@localhost:5432/hco` |
| `CERT_OUTPUT_DIR` | Local directory for generated certificate files (default: `generated_certificates`) |

#### Microsoft Excel / OneDrive (optional)

| Variable | Description |
|----------|-------------|
| `MS_TENANT_ID` | Microsoft tenant ID (`consumers` for personal accounts) |
| `MS_CLIENT_ID` | Azure app registration client ID |
| `MS_REFRESH_TOKEN` | Microsoft refresh token for personal account auth |
| `EXCEL_SHARE_URL` | Share URL of the Excel workbook for certificate records |
| `ONEDRIVE_FOLDER_SHARE_URL` | Share URL of the OneDrive folder for certificate files |
| `EXCEL_TABLE_NAME` | Name of the Excel table (default: `Certificates`) |
| `EXCEL_FILE_NAME` | Name of the Excel file (default: `Book.xlsx`) |

#### Other (optional)

| Variable | Description |
|----------|-------------|
| `AGENTVERSE_URL` | Agentverse URL (default: `https://agentverse.ai`) |
| `ASI_ONE_API_KEY` | ASI:One API key (for chat protocol integration) |
| `ANTHROPIC_API_KEY` | Anthropic API key (alternative LLM, if configured) |
| `GOOGLE_SHEETS_URL` | Google Sheets Apps Script URL (legacy, optional) |
| `HCO_PUBLIC_GENERATION` | Set to `true` to allow certificate generation without login |
| `HCO_VERIFY_EXCEL_FIRST` | Set to `true` to check Excel before local DB during verification |

### 4. Run the backend

```bash
python agent.py
```

The agent starts on **http://localhost:8096**.

#### Key REST endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/chat` | General chat (inquiry, verification, product verification) |
| POST | `/image/upload` | Upload image or PDF for certificate verification |
| POST | `/generate-certificate` | Generate a new certificate |
| POST | `/certificate/query` | Query with intent classification (download, verify, etc.) |
| POST | `/certificate/verify` | Verify a certificate by number |
| POST | `/certificate/verify-products` | Verify products against a certificate |
| POST | `/certificate/download` | Download a certificate file |

### Run with Docker (alternative)

```bash
cd agents
docker compose up --build
```

This builds the image, mounts `generated_certificates/`, and runs on port **8096**.

---

## Frontend Setup (`hco-frontend/`)

### 1. Install dependencies

```bash
cd frontend
npm install
```

### 2. Configure environment variables

```bash
cp .env.example .env.local
```

Edit `.env.local`:

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_USE_PRODUCTION` | `true` for production API, `false` for local dev | `false` |
| `VITE_DEVELOPMENT_API_URL` | Local backend URL | `http://localhost:8096` |
| `VITE_PRODUCTION_API_URL` | Production backend URL | `https://hco.sandbox-london-b.fetch-ai.com` |

For local development, the defaults work out of the box (connects to `localhost:8096`).

### 3. Run the dev server

```bash
npm run dev
```

The frontend starts on **http://localhost:5173**.

### 4. Build for production

```bash
npm run build
```

Output is written to `dist/`.

---

## Running the Full Stack Locally

1. **Start the backend** (in one terminal):

```bash
cd agents
source venv/bin/activate
python agent.py
```

2. **Start the frontend** (in another terminal):

```bash
cd frontend
npm run dev
```

3. Open **http://localhost:5173** in your browser.

---

## Features

- **Certificate Generation** — Create Halal certificates (domestic, export meat, export non-meat, slaughterhouse) with PDF output
- **Certificate Verification** — Verify certificates by number, image upload, or PDF upload using OpenAI Vision
- **Product Verification** — Check if specific products are listed on a certificate
- **Certificate Download** — Download generated certificates as PDF/PNG
- **Chat Interface** — Natural language chat for inquiries, verification, and product checks
- **ASI:One Integration** — Chat protocol support for the Fetch.ai agent ecosystem
- **Excel/OneDrive Integration** — Read/write certificate records to Excel Online via Microsoft Graph
- **Database Storage** — PostgreSQL persistence with JSON file fallback

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 19, TypeScript, Vite, Tailwind CSS |
| Backend | Python, uAgents framework, OpenAI API |
| PDF Generation | WeasyPrint, ReportLab |
| Database | PostgreSQL (psycopg2), JSON fallback |
| Cloud | Microsoft Graph API (Excel, OneDrive), Azure MSAL |
| Auth | MSAL (Microsoft), simple token-based login |

---

## Usage Guide

For detailed usage instructions, see the [HCO Usage Guide](https://docs.google.com/document/d/10U6jhd5l7S_p3_MaslgO75zrked8O2IJUX02Z9q-Ego/edit?usp=sharing).

---

## Migration Guide

For migration instructions, see the [HCO AI Certificate Validation System - Migration Guide](https://docs.google.com/document/d/1q5v_Dih48slnmIdlKdRTzT2xsipv3XWa85ltWDqM9yM/edit?usp=sharing).
