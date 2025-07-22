import pandas as pd
import requests
from pathlib import Path
import time
import logging
from urllib.parse import urlparse
import re
from tqdm import tqdm
import json
from datetime import datetime
from bs4 import BeautifulSoup  # iframe detection

class SimpleDOIDownloader:
    def __init__(self, csv_file: str, output_dir: str = "~/Desktop/downloadedresearchpapers209490"):
        self.csv_file = csv_file
        self.output_dir = Path(output_dir).expanduser()
        self.output_dir.mkdir(parents=True, exist_ok=True)

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
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })

        self.stats = {'total': 0, 'success': 0, 'failed': 0}

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
        for prefix in ['doi:', 'DOI:', 'https://doi.org/', 'http://doi.org/',
                       'https://dx.doi.org/', 'http://dx.doi.org/']:
            if doi.startswith(prefix):
                doi = doi[len(prefix):]
                break
        return doi

    def download_single_paper(self, doi: str) -> dict:
        normalized_doi = self.normalize_doi(doi)
        safe_filename = re.sub(r'[^\w\-_\.]', '_', normalized_doi)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"{safe_filename}_{timestamp}.pdf"
        filepath = self.output_dir / filename

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
                        with open(filepath, 'wb') as f:
                            f.write(response.content)
                        self.stats['success'] += 1
                        self.logger.info(f"Downloaded: {filename}")
                        return {'doi': doi, 'success': True, 'filename': filename, 'status': 'downloaded'}

                    elif 'html' in content_type:
                        pdf_links = self.extract_pdf_links(response.text, url)

                        if not pdf_links:
                            self.logger.debug(f"No PDF links found in HTML for {doi}")
                            # Save HTML fallback for debugging
                            html_path = self.output_dir / f"{safe_filename}_debug.html"
                            with open(html_path, 'w', encoding='utf-8') as f:
                                f.write(response.text)
                            self.logger.info(f"Saved fallback HTML for inspection: {html_path}")

                        for pdf_link in pdf_links[:5]:
                            if self.download_pdf_from_link(pdf_link, filepath):
                                self.stats['success'] += 1
                                self.logger.info(f"Downloaded via link: {filename}")
                                return {'doi': doi, 'success': True, 'filename': filename, 'status': 'downloaded'}

                time.sleep(2)
            except Exception as e:
                self.logger.warning(f"Error with {url}: {e}")
                continue

        self.stats['failed'] += 1
        self.logger.warning(f"Failed to download: {doi}")
        return {'doi': doi, 'success': False, 'filename': None, 'status': 'failed'}

    def extract_pdf_links(self, html_content: str, base_url: str) -> list:
        pdf_links = []
        patterns = [
            r'href=["\']([^"\']*\.pdf[^"\']*)["\']',
            r'src=["\']([^"\']*\.pdf[^"\']*)["\']',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            for match in matches:
                if match.startswith('http'):
                    pdf_links.append(match)
                elif match.startswith('/'):
                    base = f"{urlparse(base_url).scheme}://{urlparse(base_url).netloc}"
                    pdf_links.append(base + match)
                else:
                    pdf_links.append(base_url.rstrip('/') + '/' + match.lstrip('/'))

        soup = BeautifulSoup(html_content, 'html.parser')
        for tag in soup.find_all(['iframe', 'embed']):
            src = tag.get('src')
            if src and '.pdf' in src:
                if src.startswith('http'):
                    pdf_links.append(src)
                elif src.startswith('/'):
                    base = f"{urlparse(base_url).scheme}://{urlparse(base_url).netloc}"
                    pdf_links.append(base + src)
                else:
                    pdf_links.append(base_url.rstrip('/') + '/' + src.lstrip('/'))

        return list(set(pdf_links))

    def download_pdf_from_link(self, pdf_url: str, filepath: Path) -> bool:
        try:
            response = self.session.get(pdf_url, timeout=30)
            if response.status_code == 200 and response.content.startswith(b'%PDF'):
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                return True
        except Exception as e:
            self.logger.debug(f"Failed to download from {pdf_url}: {e}")
        return False

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
        success_rate = (self.stats['success'] / self.stats['total'] * 100) if self.stats['total'] > 0 else 0
        self.logger.info(f"Success rate: {success_rate:.1f}%")
        self.logger.info("=" * 50)


if __name__ == "__main__":
    downloader = SimpleDOIDownloader(
        csv_file="/Users/vineetakhanna/Desktop/COMP 797 - vk/pubmed_doi.csv",
        output_dir="~/Desktop/downloadedresearchpapers200903"
    )
    downloader.run()
