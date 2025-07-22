import pandas as pd
import requests
import os
from pathlib import Path
import time
import logging
from urllib.parse import urlparse
import re
from tqdm import tqdm
import json

class SimpleDOIDownloader:
    def __init__(self, csv_file: str, output_dir: str = "~/Desktop/downloadedresearchpapers000"):
        self.csv_file = csv_file
        self.output_dir = Path(output_dir).expanduser()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.output_dir / 'download_log.txt'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Session with proper headers to avoid blocking
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',  # Avoid brotli
            'Connection': 'keep-alive',
        })
        
        # Stats
        self.stats = {'total': 0, 'success': 0, 'failed': 0, 'skipped': 0}

    def load_dois(self):
        """Load DOI links from CSV file"""
        try:
            df = pd.read_csv(self.csv_file)
            # Try common column names for DOI
            doi_columns = ['doi', 'DOI', 'Doi', 'doi_link', 'url', 'link']
            doi_column = None
            
            for col in doi_columns:
                if col in df.columns:
                    doi_column = col
                    break
            
            if doi_column is None:
                doi_column = df.columns[0]
                self.logger.warning(f"No standard DOI column found. Using '{doi_column}'")
            
            dois = df[doi_column].dropna().tolist()
            self.logger.info(f"Loaded {len(dois)} DOI links from {self.csv_file}")
            return dois
            
        except Exception as e:
            self.logger.error(f"Error loading CSV file: {e}")
            return []

    def normalize_doi(self, doi: str) -> str:
        """Normalize DOI to standard format"""
        doi = doi.strip()
        prefixes_to_remove = [
            'doi:', 'DOI:', 'https://doi.org/', 'http://doi.org/',
            'https://dx.doi.org/', 'http://dx.doi.org/'
        ]
        
        for prefix in prefixes_to_remove:
            if doi.startswith(prefix):
                doi = doi[len(prefix):]
                break
        
        return doi

    def download_single_paper(self, doi: str) -> dict:
        """Download a single paper"""
        normalized_doi = self.normalize_doi(doi)
        safe_filename = re.sub(r'[^\w\-_\.]', '_', normalized_doi)
        
        # Check if file already exists
        #existing_files = list(self.output_dir.glob(f"{safe_filename}*"))
        #if existing_files:
            #self.stats['skipped'] += 1
            #return {'doi': doi, 'success': True, 'filename': str(existing_files[0]), 'status': 'already_exists'}
        

        
        # multiple approaches
        download_urls = [
            f"https://doi.org/{normalized_doi}",
            f"https://sci-hub.se/{normalized_doi}",
            f"https://sci-hub.st/{normalized_doi}",
        ]
        
        for url in download_urls:
            try:
                self.logger.info(f"Trying to download {doi} from {url}")
                
                # Get the page first
                response = self.session.get(url, timeout=30, allow_redirects=True)
                
                if response.status_code == 200:
                    content_type = response.headers.get('content-type', '').lower()
                    
                    # If it's already a PDF
                    if 'pdf' in content_type and response.content.startswith(b'%PDF'):
                        filename = f"{safe_filename}.pdf"
                        filepath = self.output_dir / filename
                        
                        with open(filepath, 'wb') as f:
                            f.write(response.content)
                        
                        self.stats['success'] += 1
                        self.logger.info(f" Downloaded: {filename}")
                        return {'doi': doi, 'success': True, 'filename': filename, 'status': 'downloaded'}
                    
                    # If it's HTML, look for PDF links
                    elif 'html' in content_type:
                        pdf_links = self.extract_pdf_links(response.text, url)
                        
                        for pdf_link in pdf_links[:5]:  # Try first 5 PDF links
                            if self.download_pdf_from_link(pdf_link, safe_filename):
                                self.stats['success'] += 1
                                filename = f"{safe_filename}.pdf"
                                self.logger.info(f"Downloaded: {filename}")
                                return {'doi': doi, 'success': True, 'filename': filename, 'status': 'downloaded'}
                
                # Add delay between attempts
                time.sleep(2)
                
            except Exception as e:
                self.logger.warning(f"Error with {url}: {e}")
                continue
        
        self.stats['failed'] += 1
        self.logger.warning(f" Failed to download: {doi}")
        return {'doi': doi, 'success': False, 'filename': None, 'status': 'failed'}

    def extract_pdf_links(self, html_content: str, base_url: str) -> list:
        """Extract PDF links from HTML"""
        pdf_links = []
        
        # Look for common PDF link patterns
        patterns = [
            r'href=["\']([^"\']*\.pdf[^"\']*)["\']',
            r'href=["\']([^"\']*pdf[^"\']*)["\']',
            r'src=["\']([^"\']*\.pdf[^"\']*)["\']',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            for match in matches:
                if match.startswith('http'):
                    pdf_links.append(match)
                elif match.startswith('/'):
                    # Absolute path
                    base_domain = f"{urlparse(base_url).scheme}://{urlparse(base_url).netloc}"
                    pdf_links.append(base_domain + match)
                else:
                    # Relative path
                    pdf_links.append(base_url.rstrip('/') + '/' + match.lstrip('/'))
        
        return list(set(pdf_links))

    def download_pdf_from_link(self, pdf_url: str, safe_filename: str) -> bool:
        """Download PDF from direct link"""
        try:
            response = self.session.get(pdf_url, timeout=30)
            
            if response.status_code == 200 and response.content.startswith(b'%PDF'):
                filename = f"{safe_filename}.pdf"
                filepath = self.output_dir / filename
                
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                
                return True
        except Exception as e:
            self.logger.debug(f"Failed to download from {pdf_url}: {e}")
        
        return False

    def run(self):
        """Main execution function"""
        self.logger.info(f"Starting download to {self.output_dir}")
        
        dois = self.load_dois()
        if not dois:
            return
        
        self.stats['total'] = len(dois)
        results = []
        
        # Download with progress bar
        with tqdm(total=len(dois), desc="Downloading papers") as pbar:
            for doi in dois:
                result = self.download_single_paper(doi)
                results.append(result)
                
                pbar.update(1)
                pbar.set_postfix({
                    'Success': self.stats['success'],
                    'Failed': self.stats['failed'],
                    'Skipped': self.stats['skipped']
                })
                
                # Small delay to be respectful to servers
                time.sleep(1)
        
        # Save results
        results_file = self.output_dir / 'download_results.json'
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        # Print final stats
        self.logger.info("=" * 50)
        self.logger.info("DOWNLOAD SUMMARY")
        self.logger.info("=" * 50)
        self.logger.info(f"Total DOIs: {self.stats['total']}")
        self.logger.info(f"Successfully downloaded: {self.stats['success']}")
        self.logger.info(f"Failed: {self.stats['failed']}")
        self.logger.info(f"Skipped (already exists): {self.stats['skipped']}")
        success_rate = (self.stats['success'] / self.stats['total'] * 100) if self.stats['total'] > 0 else 0
        self.logger.info(f"Success rate: {success_rate:.1f}%")
        self.logger.info("=" * 50)

if __name__ == "__main__":
    # file path
    downloader = SimpleDOIDownloader(
        csv_file="/Users/vineetakhanna/Desktop/COMP 797 - vk/pubmed_doi.csv",
        output_dir="~/Desktop/downloadedresearchpapers"
    )
    
    downloader.run()