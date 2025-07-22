import pandas as pd
import requests
import os
from pathlib import Path
import time
import logging
from urllib.parse import urlparse
import re
import json
from tqdm import tqdm
from bs4 import BeautifulSoup
import difflib
from fpdf import FPDF

class SimpleDOIDownloader:
    def __init__(self, csv_file: str, output_dir: str = "~/Desktop/downloadedresearchpapers100"):
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

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        })

        self.stats = {'total': 0, 'success': 0, 'failed': 0, 'skipped': 0}

    def load_dois(self):
        try:
            df = pd.read_csv(self.csv_file)
            doi_columns = ['doi', 'DOI', 'Doi', 'doi_link', 'url', 'link']
            doi_column = next((col for col in doi_columns if col in df.columns), df.columns[0])
            dois = df[doi_column].dropna().tolist()
            self.logger.info(f"Loaded {len(dois)} DOI links from {self.csv_file}")
            return dois
        except Exception as e:
            self.logger.error(f"Error loading CSV file: {e}")
            return []

    def normalize_doi(self, doi: str) -> str:
        doi = doi.strip()
        for prefix in ['doi:', 'DOI:', 'https://doi.org/', 'http://doi.org/', 'https://dx.doi.org/', 'http://dx.doi.org/']:
            if doi.startswith(prefix):
                doi = doi[len(prefix):]
                break
        return doi

    def run(self):
        self.logger.info(f"Starting download to {self.output_dir}")
        dois = self.load_dois()
        if not dois:
            return
        self.stats['total'] = len(dois)
        results = []

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
                time.sleep(1)

        results_file = self.output_dir / 'download_results.json'
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)

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

    def download_single_paper(self, doi: str) -> dict:
        normalized_doi = self.normalize_doi(doi)
        safe_filename = re.sub(r'[^\w\-_\.]', '_', normalized_doi)
        #existing_files = list(self.output_dir.glob(f"{safe_filename}*"))
        #if existing_files:
            #self.stats['skipped'] += 1
            #return {'doi': doi, 'success': True, 'filename': str(existing_files[0]), 'status': 'already_exists'}

        download_urls = [
            f"https://doi.org/{normalized_doi}",
            f"https://sci-hub.se/{normalized_doi}",
            f"https://sci-hub.st/{normalized_doi}",
        ]

        for url in download_urls:
            try:
                self.logger.info(f"Trying to download {doi} from {url}")
                response = self.session.get(url, timeout=30, allow_redirects=True)

                if response.status_code == 200:
                    content_type = response.headers.get('content-type', '').lower()

                    if 'pdf' in content_type and response.content.startswith(b'%PDF'):
                        filename = f"{safe_filename}.pdf"
                        filepath = self.output_dir / filename
                        with open(filepath, 'wb') as f:
                            f.write(response.content)
                        self.stats['success'] += 1
                        return {'doi': doi, 'success': True, 'filename': filename, 'status': 'downloaded'}

                    elif 'html' in content_type:
                        html = response.text
                        pdf_links = self.extract_pdf_links(html, url)

                        for pdf_link in pdf_links[:5]:
                            if self.download_pdf_from_link(pdf_link, safe_filename):
                                filename = f"{safe_filename}.pdf"
                                self.stats['success'] += 1
                                return {'doi': doi, 'success': True, 'filename': filename, 'status': 'downloaded'}

                        # Try saving fallback text
                        text = self.extract_text_content(html)
                        if len(text.strip()) > 500:
                            fallback_name = f"{safe_filename}_htmlfallback.pdf"
                            fallback_path = self.output_dir / fallback_name
                            self.save_text_as_pdf(text, fallback_path)
                            self.stats['success'] += 1
                            return {'doi': doi, 'success': True, 'filename': fallback_name, 'status': 'html_text_saved'}

                time.sleep(2)

            except Exception as e:
                self.logger.warning(f"Error with {url}: {e}")
                continue

        self.stats['failed'] += 1
        return {'doi': doi, 'success': False, 'filename': None, 'status': 'failed'}

    def extract_pdf_links(self, html_content: str, base_url: str) -> list:
        pdf_links = set()
        patterns = [
            r'href=["\']([^"\']*\.pdf[^"\']*)["\']',
            r'src=["\']([^"\']*\.pdf[^"\']*)["\']',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            for match in matches:
                pdf_links.add(self._resolve_link(base_url, match))

        soup = BeautifulSoup(html_content, 'html.parser')
        for tag in soup.find_all(['a', 'button']):
            text = tag.get_text(strip=True).lower()
            title_attr = tag.get('title', '').lower()
            if 'epdf' in title_attr or 'epdf' in text:
                href = tag.get('href') or tag.get('data-href') or ''
                if href:
                    pdf_links.add(self._resolve_link(base_url, href))
            if difflib.get_close_matches(text, ['download', 'get pdf', 'full text'], cutoff=0.6):
                href = tag.get('href') or tag.get('data-href') or ''
                if href:
                    pdf_links.add(self._resolve_link(base_url, href))

        return list(pdf_links)

    def _resolve_link(self, base_url: str, path: str) -> str:
        if path.startswith('http'):
            return path
        elif path.startswith('/'):
            return f"{urlparse(base_url).scheme}://{urlparse(base_url).netloc}{path}"
        else:
            return base_url.rstrip('/') + '/' + path.lstrip('/')

    def download_pdf_from_link(self, pdf_url: str, safe_filename: str) -> bool:
        try:
            response = self.session.get(pdf_url, timeout=30)
            if response.status_code == 200 and response.content.startswith(b'%PDF'):
                filepath = self.output_dir / f"{safe_filename}.pdf"
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                return True
        except Exception as e:
            self.logger.debug(f"Failed to download from {pdf_url}: {e}")
        return False

    def extract_text_content(self, html: str) -> str:
        soup = BeautifulSoup(html, 'html.parser')
        for script in soup(['script', 'style']):
            script.decompose()
        return soup.get_text(separator='\n')

    def save_text_as_pdf(self, text: str, filepath: Path):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.set_font("Arial", size=10)
        for line in text.splitlines():
            if line.strip():
                pdf.multi_cell(0, 10, line.strip())
        pdf.output(str(filepath))

if __name__ == "__main__":
    downloader = SimpleDOIDownloader(
        csv_file="/Users/vineetakhanna/Desktop/COMP 797 - vk/pubmed_doi.csv",
        output_dir="~/Desktop/downloadedresearchpapers"
    )
    downloader.run()
