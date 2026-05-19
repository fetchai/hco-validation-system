import os
from datetime import datetime
from typing import Optional, Dict, Any
import base64
import logging

# Logging is configured globally by hco_logger.configure(); just attach a child logger.
logger = logging.getLogger("hco.db")

DATABASE_URL = os.getenv("DATABASE_URL")

# psycopg2 is optional: if it's not installed (common in minimal Docker images),
# we continue in fallback mode (local JSON/files).
try:
    import psycopg2  # type: ignore
    import psycopg2.extras  # type: ignore
except Exception:  # pragma: no cover
    psycopg2 = None  # type: ignore
    logger.warning("psycopg2 is not installed; database features disabled (fallback mode enabled).")

def get_db_connection():
    """Get PostgreSQL database connection with fallback"""
    try:
        if not DATABASE_URL:
            logger.warning("DATABASE_URL not set, using fallback mode")
            return None
        if psycopg2 is None:
            logger.warning("DATABASE_URL is set but psycopg2 is missing; cannot connect, using fallback mode")
            return None
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        logger.error(f"Error connecting to database: {e}")
        logger.warning("Database connection failed, continuing in fallback mode")
        return None

def init_database():
    """Initialize database tables"""
    try:
        conn = get_db_connection()
        if conn is None:
            logger.warning("Database connection not available, skipping database initialization")
            return
        cur = conn.cursor()
        
        # Create certificates table
        create_table_query = """
        CREATE TABLE IF NOT EXISTS certificates (
            id SERIAL PRIMARY KEY,
            certificate_id VARCHAR(255) UNIQUE NOT NULL,
            certificate_no VARCHAR(255) NOT NULL,
            company_name VARCHAR(500) NOT NULL,
            company_reg_no VARCHAR(255) NOT NULL,
            issue_date DATE NOT NULL,
            certificate_type VARCHAR(255) DEFAULT 'halal_certificate',
            standards TEXT,
            products_data JSONB,
            text_color VARCHAR(50) DEFAULT 'black',
            png_data BYTEA,
            pdf_data BYTEA,
            png_filename VARCHAR(255),
            pdf_filename VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        cur.execute(create_table_query)
        
        # Create index on certificate_no for faster lookups
        create_index_query = """
        CREATE INDEX IF NOT EXISTS idx_certificate_no ON certificates(certificate_no);
        """
        cur.execute(create_index_query)
        
        # Add new columns if they don't exist (for existing tables)
        upgrade_table_queries = [
            "ALTER TABLE certificates ADD COLUMN IF NOT EXISTS certificate_type VARCHAR(255) DEFAULT 'halal_certificate';",
            "ALTER TABLE certificates ADD COLUMN IF NOT EXISTS standards TEXT;",
            "ALTER TABLE certificates ADD COLUMN IF NOT EXISTS products_data JSONB;"
        ]
        
        for query in upgrade_table_queries:
            try:
                cur.execute(query)
            except Exception as e:
                logger.info(f"Column might already exist: {e}")
        
        conn.commit()
        cur.close()
        conn.close()
        logger.info("Database initialized successfully")
        
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise

def save_certificate_to_db(
    certificate_id: str,
    certificate_no: str,
    company_name: str,
    company_reg_no: str,
    issue_date: str,
    text_color: str = "black",
    png_data: Optional[bytes] = None,
    pdf_data: Optional[bytes] = None,
    png_filename: Optional[str] = None,
    pdf_filename: Optional[str] = None,
    certificate_type: str = "halal_certificate",
    standards: str = "",
    products_data: Optional[list] = None
) -> bool:
    """Save certificate data to PostgreSQL database"""
    try:
        conn = get_db_connection()
        if conn is None:
            logger.warning("Database connection not available, skipping database save")
            # Save to local file as fallback
            try:
                import json
                import os

                out_dir = os.getenv("CERT_OUTPUT_DIR", "generated_certificates")
                try:
                    os.makedirs(out_dir, exist_ok=True)
                except Exception:
                    out_dir = "."

                fallback_data = {
                    'certificate_id': certificate_id,
                    'certificate_no': certificate_no,
                    'company_name': company_name,
                    'company_reg_no': company_reg_no,
                    'issue_date': issue_date,
                    'certificate_type': certificate_type,
                    'standards': standards,
                    'products_data': products_data,
                    'created_at': datetime.now().isoformat()
                }
                
                fallback_file = os.path.join(out_dir, f"certificate_{certificate_no.replace('/', '_')}_data.json")
                with open(fallback_file, 'w') as f:
                    json.dump(fallback_data, f, indent=2)
                
                # Also persist files locally if provided (enables download + OneDrive upload in fallback mode)
                safe_cert_no = certificate_no.replace('/', '_').replace('\\', '_')
                try:
                    if pdf_data:
                        pdf_path = os.path.join(out_dir, (pdf_filename or f"certificate_{safe_cert_no}.pdf"))
                        # Only write if it looks like a PDF
                        if isinstance(pdf_data, (bytes, bytearray)) and bytes(pdf_data).startswith(b"%PDF"):
                            with open(pdf_path, "wb") as pf:
                                pf.write(bytes(pdf_data))
                            logger.info(f"Certificate PDF saved to fallback file: {pdf_path}")
                except Exception as file_err:
                    logger.warning(f"Could not save PDF to fallback file: {file_err}")

                try:
                    if png_data:
                        png_path = os.path.join(out_dir, (png_filename or f"certificate_{safe_cert_no}.png"))
                        if isinstance(png_data, (bytes, bytearray)):
                            with open(png_path, "wb") as imgf:
                                imgf.write(bytes(png_data))
                            logger.info(f"Certificate PNG saved to fallback file: {png_path}")
                except Exception as file_err:
                    logger.warning(f"Could not save PNG to fallback file: {file_err}")

                logger.info(f"Certificate data saved to fallback file: {fallback_file}")
                return True  # Return True to continue certificate generation
            except Exception as fallback_error:
                logger.error(f"Fallback save also failed: {fallback_error}")
                return True  # Still return True to not block certificate generation
        
        cur = conn.cursor()
        
        # Convert date string to date object if needed
        if isinstance(issue_date, str):
            # Try different date formats
            try:
                issue_date_obj = datetime.strptime(issue_date, '%Y-%m-%d').date()
            except ValueError:
                try:
                    issue_date_obj = datetime.strptime(issue_date, '%Y/%m/%d').date()
                except ValueError:
                    # If parsing fails, use current date
                    issue_date_obj = datetime.now().date()
        else:
            issue_date_obj = issue_date
        
        # Convert products list to JSON if provided
        import json
        products_json = json.dumps(products_data) if products_data else None
        
        insert_query = """
        INSERT INTO certificates (
            certificate_id, certificate_no, company_name, company_reg_no, 
            issue_date, certificate_type, standards, products_data,
            text_color, png_data, pdf_data, png_filename, pdf_filename
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        ) ON CONFLICT (certificate_id) DO UPDATE SET
            certificate_no = EXCLUDED.certificate_no,
            company_name = EXCLUDED.company_name,
            company_reg_no = EXCLUDED.company_reg_no,
            issue_date = EXCLUDED.issue_date,
            certificate_type = EXCLUDED.certificate_type,
            standards = EXCLUDED.standards,
            products_data = EXCLUDED.products_data,
            text_color = EXCLUDED.text_color,
            png_data = EXCLUDED.png_data,
            pdf_data = EXCLUDED.pdf_data,
            png_filename = EXCLUDED.png_filename,
            pdf_filename = EXCLUDED.pdf_filename,
            updated_at = CURRENT_TIMESTAMP;
        """
        
        cur.execute(insert_query, (
            certificate_id, certificate_no, company_name, company_reg_no,
            issue_date_obj, certificate_type, standards, products_json,
            text_color, png_data, pdf_data, png_filename, pdf_filename
        ))
        
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"Certificate {certificate_id} saved to database successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error saving certificate to database: {e}")
        return False

def get_certificate_from_db(certificate_no: str) -> Optional[Dict[str, Any]]:
    """Retrieve certificate data from PostgreSQL database"""
    try:
        conn = get_db_connection()
        if conn is None:
            logger.warning("Database connection not available, trying fallback file lookup")
            # Try to find local certificate data as fallback
            try:
                import json
                import glob
                import os
                
                # Look for certificate data files
                safe_cert_no = certificate_no.replace('/', '_').replace('\\', '_')
                file_patterns = [
                    f"certificate_{safe_cert_no}_data.json",
                    f"{safe_cert_no}_data.json",
                    f"*{safe_cert_no}*_data.json"
                ]

                out_dir = os.getenv("CERT_OUTPUT_DIR", "generated_certificates")
                file_patterns.extend([os.path.join(out_dir, p) for p in list(file_patterns)])
                
                for pattern in file_patterns:
                    files = glob.glob(pattern)
                    if files:
                        with open(files[0], 'r') as f:
                            certificate_data = json.load(f)
                            logger.info(f"Certificate {certificate_no} retrieved from fallback file: {files[0]}")
                            return certificate_data
                
                logger.info(f"Certificate {certificate_no} not found in fallback files")
                return None
                
            except Exception as fallback_error:
                logger.error(f"Fallback certificate lookup failed: {fallback_error}")
                return None
        
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        select_query = """
        SELECT * FROM certificates WHERE UPPER(certificate_no) = UPPER(%s) ORDER BY created_at DESC LIMIT 1;
        """
        
        cur.execute(select_query, (certificate_no,))
        result = cur.fetchone()
        
        cur.close()
        conn.close()
        
        if result:
            # Convert to regular dict and handle date serialization
            certificate_data = dict(result)
            if certificate_data.get('issue_date'):
                certificate_data['issue_date'] = certificate_data['issue_date'].strftime('%Y-%m-%d')
            if certificate_data.get('created_at'):
                certificate_data['created_at'] = certificate_data['created_at'].isoformat()
            if certificate_data.get('updated_at'):
                certificate_data['updated_at'] = certificate_data['updated_at'].isoformat()
            
            logger.info(f"Certificate {certificate_no} retrieved from database")
            return certificate_data
        else:
            logger.info(f"Certificate {certificate_no} not found in database")
            return None
            
    except Exception as e:
        logger.error(f"Error retrieving certificate from database: {e}")
        return None

def get_certificate_file_from_db(certificate_no: str, file_type: str) -> Optional[bytes]:
    """Retrieve certificate file (PNG or PDF) from database"""
    try:
        conn = get_db_connection()
        if conn is None:
            logger.warning("Database connection not available, trying fallback file lookup")
            # Try to find local certificate files as fallback
            try:
                import glob
                import os
                
                # Look for certificate files in current directory with pattern
                safe_cert_no = certificate_no.replace('/', '_').replace('\\', '_')
                file_patterns = [
                    f"certificate_{safe_cert_no}.{file_type.lower()}",
                    f"{safe_cert_no}.{file_type.lower()}",
                    f"*{safe_cert_no}*.{file_type.lower()}"
                ]

                out_dir = os.getenv("CERT_OUTPUT_DIR", "generated_certificates")
                file_patterns.extend([os.path.join(out_dir, p) for p in list(file_patterns)])
                
                for pattern in file_patterns:
                    files = glob.glob(pattern)
                    if files:
                        with open(files[0], 'rb') as f:
                            file_data = f.read()
                            logger.info(f"Certificate {file_type} file found in fallback: {files[0]}")
                            return file_data
                
                logger.info(f"Certificate {file_type} file not found in fallback for {certificate_no}")
                return None
                
            except Exception as fallback_error:
                logger.error(f"Fallback file lookup failed: {fallback_error}")
                return None
        
        cur = conn.cursor()
        
        if file_type.lower() == 'png':
            select_query = "SELECT png_data FROM certificates WHERE UPPER(certificate_no) = UPPER(%s) ORDER BY created_at DESC LIMIT 1;"
        elif file_type.lower() == 'pdf':
            select_query = "SELECT pdf_data FROM certificates WHERE UPPER(certificate_no) = UPPER(%s) ORDER BY created_at DESC LIMIT 1;"
        else:
            logger.error(f"Invalid file type: {file_type}")
            return None
        
        cur.execute(select_query, (certificate_no,))
        result = cur.fetchone()
        
        cur.close()
        conn.close()
        
        if result and result[0]:
            logger.info(f"Certificate {file_type} file retrieved for {certificate_no}")
            return bytes(result[0])
        else:
            logger.info(f"Certificate {file_type} file not found for {certificate_no}")
            return None
            
    except Exception as e:
        logger.error(f"Error retrieving certificate file from database: {e}")
        return None

def list_certificates_from_db(limit: int = 100, offset: int = 0) -> list:
    """List certificates from database with pagination"""
    try:
        conn = get_db_connection()
        if conn is None:
            return []
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        select_query = """
        SELECT certificate_id, certificate_no, company_name, company_reg_no, 
               issue_date, created_at, updated_at 
        FROM certificates 
        ORDER BY created_at DESC 
        LIMIT %s OFFSET %s;
        """
        
        cur.execute(select_query, (limit, offset))
        results = cur.fetchall()
        
        cur.close()
        conn.close()
        
        # Convert to list of dicts and handle date serialization
        certificates = []
        for result in results:
            cert_data = dict(result)
            if cert_data.get('issue_date'):
                cert_data['issue_date'] = cert_data['issue_date'].strftime('%Y-%m-%d')
            if cert_data.get('created_at'):
                cert_data['created_at'] = cert_data['created_at'].isoformat()
            if cert_data.get('updated_at'):
                cert_data['updated_at'] = cert_data['updated_at'].isoformat()
            certificates.append(cert_data)
        
        logger.info(f"Retrieved {len(certificates)} certificates from database")
        return certificates
        
    except Exception as e:
        logger.error(f"Error listing certificates from database: {e}")
        return []