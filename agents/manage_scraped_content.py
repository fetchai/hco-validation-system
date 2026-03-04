#!/usr/bin/env python3
"""
Command-line utility to manage scraped website content.
This script allows you to initialize, update, and view stored content.
"""

import sys
import argparse
from website_scraper import scraper, HCO_URLS, initialize_content_storage

def main():
    parser = argparse.ArgumentParser(description="Manage scraped website content")
    parser.add_argument('action', choices=['init', 'update', 'status', 'refresh'],
                       help='Action to perform')
    parser.add_argument('--url', help='Specific URL to update (optional)')
    parser.add_argument('--force', action='store_true', 
                       help='Force update even if content is fresh')
    
    args = parser.parse_args()
    
    if args.action == 'init':
        print("Initializing content storage for all HCO URLs...")
        results = initialize_content_storage()
        
        success_count = 0
        error_count = 0
        
        for url, content in results.items():
            if content.startswith("Error"):
                print(f"✗ {url}: {content[:100]}...")
                error_count += 1
            else:
                print(f"✓ {url}: {len(content)} characters")
                success_count += 1
        
        print(f"\nSummary: {success_count} successful, {error_count} errors")
        
    elif args.action == 'update':
        if args.url:
            urls = [args.url]
        else:
            urls = HCO_URLS
        
        print(f"Updating content for {len(urls)} URL(s)...")
        
        if args.force:
            results = scraper.scrape_multiple_urls(urls, use_cache=False)
        else:
            results = scraper.scrape_multiple_urls(urls, use_cache=True)
        
        for url, content in results.items():
            if content.startswith("Error"):
                print(f"✗ {url}: Failed to update")
            else:
                print(f"✓ {url}: Updated ({len(content)} characters)")
    
    elif args.action == 'status':
        info = scraper.get_storage_info()
        
        print("Storage Information:")
        print(f"  Directory: {info['storage_dir']}")
        print(f"  Content files: {info['content_files']}")
        print(f"  Metadata files: {info['metadata_files']}")
        print(f"  Total size: {info['total_size_mb']} MB")
        
        if 'files' in info:
            print("\nRecent files:")
            for file in info['files']:
                print(f"  - {file}")
    
    elif args.action == 'refresh':
        print("Force refreshing all content...")
        results = scraper.update_all_content(HCO_URLS)
        
        success_count = sum(1 for content in results.values() if not content.startswith("Error"))
        print(f"Successfully refreshed {success_count}/{len(HCO_URLS)} URLs")

if __name__ == '__main__':
    main()