import os
import json
import time
import hashlib
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class WebsiteScraper:
    """Enhanced web scraper with text file storage fallback system"""
    
    def __init__(self, storage_dir: str = "scraped_data"):
        self.storage_dir = storage_dir
        self.ensure_storage_dir()
        
    def ensure_storage_dir(self):
        """Create storage directory if it doesn't exist"""
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)
            logger.info(f"Created storage directory: {self.storage_dir}")
    
    def get_file_path(self, url: str) -> str:
        """Generate a safe file path for storing scraped content"""
        # Create a hash of the URL to use as filename
        url_hash = hashlib.md5(url.encode()).hexdigest()
        domain = url.split('/')[2].replace('www.', '') if '//' in url else 'unknown'
        return os.path.join(self.storage_dir, f"{domain}_{url_hash}.txt")
    
    def get_metadata_path(self, url: str) -> str:
        """Generate path for metadata file"""
        file_path = self.get_file_path(url)
        return file_path.replace('.txt', '_meta.json')
    
    def is_content_fresh(self, url: str, max_age_hours: int = 24) -> bool:
        """Check if stored content is fresh enough"""
        meta_path = self.get_metadata_path(url)
        if not os.path.exists(meta_path):
            return False
        
        try:
            with open(meta_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            scraped_time = datetime.fromisoformat(metadata['scraped_at'])
            if datetime.now() - scraped_time < timedelta(hours=max_age_hours):
                logger.info(f"Using fresh cached content for {url}")
                return True
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Error reading metadata for {url}: {e}")
        
        return False
    
    def save_content(self, url: str, content: str, success: bool = True, error_msg: str = ""):
        """Save scraped content and metadata to files"""
        try:
            # Save content
            file_path = self.get_file_path(url)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Save metadata
            meta_path = self.get_metadata_path(url)
            metadata = {
                'url': url,
                'scraped_at': datetime.now().isoformat(),
                'success': success,
                'error_message': error_msg,
                'content_length': len(content)
            }
            
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"Saved content for {url} to {file_path}")
            
        except Exception as e:
            logger.error(f"Error saving content for {url}: {e}")
    
    def load_content(self, url: str) -> Optional[str]:
        """Load content from stored file"""
        file_path = self.get_file_path(url)
        
        if not os.path.exists(file_path):
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            logger.info(f"Loaded cached content for {url}")
            return content
        except Exception as e:
            logger.error(f"Error loading cached content for {url}: {e}")
            return None
    
    def scrape_with_fallback(self, url: str, use_cache: bool = True, max_age_hours: int = 24) -> str:
        """Scrape URL with fallback to stored content"""
        
        # Check if we should use cached content
        if use_cache and self.is_content_fresh(url, max_age_hours):
            cached_content = self.load_content(url)
            if cached_content:
                return cached_content
        
        # Attempt to scrape fresh content
        try:
            content = self._scrape_url(url)
            self.save_content(url, content, success=True)
            return content
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error scraping {url}: {error_msg}")
            
            # Try to use any stored content as fallback
            fallback_content = self.load_content(url)
            if fallback_content:
                logger.info(f"Using fallback content for {url}")
                return fallback_content
            
            # Save error for future reference
            error_content = f"Error scraping {url}: {error_msg}\nTimestamp: {datetime.now().isoformat()}"
            self.save_content(url, error_content, success=False, error_msg=error_msg)
            
            return error_content
    
    def _scrape_url(self, url: str) -> str:
        """Internal method to scrape a single URL"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer"]):
            script.decompose()
        
        # Extract text content
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        return text
    
    def scrape_multiple_urls(self, urls: List[str], use_cache: bool = True) -> Dict[str, str]:
        """Scrape multiple URLs with fallback support"""
        results = {}
        
        for url in urls:
            logger.info(f"Processing URL: {url}")
            try:
                content = self.scrape_with_fallback(url, use_cache)
                results[url] = content
                time.sleep(1)  # Be respectful to the server
            except Exception as e:
                logger.error(f"Failed to process {url}: {e}")
                results[url] = f"Error processing {url}: {str(e)}"
        
        return results
    
    def get_storage_info(self) -> Dict[str, any]:
        """Get information about stored content"""
        if not os.path.exists(self.storage_dir):
            return {"error": "Storage directory does not exist"}
        
        files = os.listdir(self.storage_dir)
        content_files = [f for f in files if f.endswith('.txt') and not f.endswith('_meta.json')]
        meta_files = [f for f in files if f.endswith('_meta.json')]
        
        total_size = 0
        for file in files:
            try:
                total_size += os.path.getsize(os.path.join(self.storage_dir, file))
            except OSError:
                pass
        
        return {
            "storage_dir": self.storage_dir,
            "content_files": len(content_files),
            "metadata_files": len(meta_files),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "files": content_files[:10]  # Show first 10 files
        }
    
    def update_all_content(self, urls: List[str]) -> Dict[str, str]:
        """Force refresh all URLs and update stored content"""
        logger.info(f"Force updating content for {len(urls)} URLs")
        return self.scrape_multiple_urls(urls, use_cache=False)


# HCO Website URLs
HCO_URLS = [
    "https://www.hcoltd.co.uk/",
    "https://www.hcoltd.co.uk/about",
    "https://www.hcoltd.co.uk/certificationprocess",
    "https://www.hcoltd.co.uk/policies",
    "https://www.hcoltd.co.uk/faq",
    "https://www.hcoltd.co.uk/contact",
    "https://www.hcoltd.co.uk/registration",
    "https://www.hcoltd.co.uk/services",
    "https://www.hcoltd.co.uk/news",
    "http://hcoltd.co.uk/blog",
    "https://www.hcoltd.co.uk/reviews",
    "https://www.hcoltd.co.uk/jobs"
]

# Initialize global scraper instance
scraper = WebsiteScraper()

def initialize_content_storage():
    """Initialize content storage by scraping all HCO URLs"""
    logger.info("Initializing content storage for all HCO URLs")
    results = scraper.scrape_multiple_urls(HCO_URLS)
    
    success_count = sum(1 for content in results.values() if not content.startswith("Error"))
    logger.info(f"Successfully scraped {success_count}/{len(HCO_URLS)} URLs")
    
    return results

def get_relevant_urls(query):
    """Determine which HCO website URLs are relevant to the user's query"""
    query_lower = query.lower()
    
    # Define URL mappings with keywords
    url_mappings = {
        "https://www.hcoltd.co.uk/": ["general", "home", "main", "overview", "hco"],
        "https://www.hcoltd.co.uk/about": ["about", "company", "who", "what is", "background", "history", "mission", "vision"],
        "https://www.hcoltd.co.uk/certificationprocess": ["certification", "process", "how to", "procedure", "steps", "certify", "certificate process"],
        "https://www.hcoltd.co.uk/policies": ["policy", "policies", "terms", "conditions", "rules", "guidelines", "privacy"],
        "https://www.hcoltd.co.uk/faq": ["faq", "question", "questions", "help", "answer", "common", "frequently asked"],
        "https://www.hcoltd.co.uk/contact": ["contact", "phone", "email", "address", "reach", "get in touch", "location"],
        "https://www.hcoltd.co.uk/registration": ["register", "registration", "sign up", "apply", "application", "join"],
        "https://www.hcoltd.co.uk/services": ["service", "services", "offer", "provide", "what do", "offerings"],
        "https://www.hcoltd.co.uk/news": ["news", "updates", "announcement", "latest", "recent", "current"],
        "http://hcoltd.co.uk/blog": ["blog", "article", "post", "insights", "thoughts", "stories"],
        "https://www.hcoltd.co.uk/reviews": ["review", "reviews", "testimonial", "feedback", "rating", "experience"],
        "https://www.hcoltd.co.uk/jobs": ["job", "jobs", "career", "employment", "work", "hiring", "vacancy", "position"]
    }
    
    relevant_urls = []
    
    # Check each URL for keyword matches
    for url, keywords in url_mappings.items():
        for keyword in keywords:
            if keyword in query_lower:
                if url not in relevant_urls:
                    relevant_urls.append(url)
                break
    
    # If no specific matches, include general pages
    if not relevant_urls:
        relevant_urls = [
            "https://www.hcoltd.co.uk/",
            "https://www.hcoltd.co.uk/about",
            "https://www.hcoltd.co.uk/services"
        ]
    
    return relevant_urls

def get_hco_content_with_fallback(query: str) -> str:
    """Enhanced function to get HCO content with fallback support"""
    try:
        relevant_urls = get_relevant_urls(query)
        logger.info(f"Selected relevant URLs for query '{query}': {relevant_urls}")
        
        all_content = []
        for url in relevant_urls:
            content = scraper.scrape_with_fallback(url)
            if content and not content.startswith("Error"):
                all_content.append(f"=== Content from {url} ===\n{content}\n")
            else:
                logger.warning(f"No valid content retrieved from {url}")
        
        if all_content:
            return "\n".join(all_content)
        else:
            return "No content could be extracted from any relevant HCO website pages."
            
    except Exception as e:
        logger.error(f"Error in get_hco_content_with_fallback: {e}")
        return f"Error occurred while retrieving content: {str(e)}"

if __name__ == "__main__":
    # Test the scraper
    print("Testing website scraper...")
    results = initialize_content_storage()
    
    print(f"\nScraping results:")
    for url, content in results.items():
        status = "✓" if not content.startswith("Error") else "✗"
        print(f"{status} {url}: {len(content)} characters")
    
    print(f"\nStorage info: {scraper.get_storage_info()}")