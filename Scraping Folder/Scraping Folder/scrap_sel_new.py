# Full script with Selenium fallback for PDF download on macOS
# This script fetches metadata and PDFs from PubMed and PMC using Entrez and Selenium.
# It handles various cases including DOI and SDSU proxy for access.
# It also includes error handling and logging for better debugging.
# This is also working on macOS.

import os
import re
import time
import glob
import pandas as pd
from time import sleep
from tqdm import tqdm
from bs4 import BeautifulSoup
import requests
from Bio import Entrez, Medline
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import chromedriver_autoinstaller
from selenium.common.exceptions import NoSuchWindowException, WebDriverException

# Set email for Entrez
Entrez.email = "jshaik2452@sdsu.edu"
browser_closed = False


# PDF download folders
pdf_folder = os.path.join(os.path.expanduser("~"), "Desktop", "downloaded_pdfs")
os.makedirs(pdf_folder, exist_ok=True)

# Load journal data
journal_info = pd.read_excel("All Journals List.xlsx")[['PubMed Abbreviation', 'Issn']].dropna()

# Define keywords
keywords = ['Gel', 'Gelation', 'Gel Hardness']

# Selenium setup
chromedriver_autoinstaller.install()

chrome_options = Options()
chrome_options.add_experimental_option("prefs", {
    "download.default_directory": pdf_folder,
    "download.prompt_for_download": False,
    "plugins.always_open_pdf_externally": True
})
chrome_options.add_argument("--start-maximized")

driver = webdriver.Chrome(options=chrome_options)

def wait_for_download(keyword="", timeout=30):
    for _ in range(timeout):
        pdfs = glob.glob(os.path.join(pdf_folder, "*.pdf"))
        for pdf in pdfs:
            if keyword.lower() in pdf.lower():
                return pdf
        time.sleep(1)
    return None

# Citation count fetcher
def fetch_citation_count(pmid):
    try:
        handle = Entrez.elink(dbfrom="pubmed", db="pubmed", linkname="pubmed_pubmed_citedin", id=pmid)
        records = Entrez.read(handle)
        handle.close()
        linksets = records[0].get("LinkSetDb", [])
        return len(linksets[0]["Link"]) if linksets else 0
    except:
        return 0

# PDF URL fetcher from PMC
def get_pdf_url_from_pmc(pmid):
    try:
        elink_handle = Entrez.elink(dbfrom="pubmed", db="pmc", id=pmid, linkname="pubmed_pmc")
        elink_record = Entrez.read(elink_handle)
        elink_handle.close()
        linksets = elink_record[0].get("LinkSetDb", [])

        if not linksets:
            return None, None

        pmcid = linksets[0]["Link"][0]["Id"]
        pmc_id_str = f"PMC{pmcid}"
        pmc_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmc_id_str}/"

        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(pmc_url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")

        meta_tag = soup.find("meta", attrs={"name": "citation_pdf_url"})
        if meta_tag and meta_tag.get("content"):
            pdf_url = meta_tag["content"].replace("pmc.ncbi.nlm.nih.gov", "www.ncbi.nlm.nih.gov")
            pdf_url = pdf_url.replace("www.ncbi.nlm.nih.gov/articles", "www.ncbi.nlm.nih.gov/pmc/articles")
            return pdf_url, pmc_id_str

        pdf_link_tag = soup.find("a", string=lambda t: t and "PDF" in t)
        if pdf_link_tag and pdf_link_tag.get("href"):
            href = pdf_link_tag["href"]
            return ("https://www.ncbi.nlm.nih.gov" + href if href.startswith("/") else href), pmc_id_str
        return None, None

    except Exception as e:
        print(f"❌ PDF URL error for PMID {pmid}: {e}")
        return None, None

# Fallback: use Selenium and SDSU proxy to get PDF
def download_via_sdsu_proxy(doi):
    try:
        global browser_closed
        if not driver.window_handles:
            if not browser_closed:
                print("❌ No open Chrome window.")
                browser_closed = True
            return False

        proxy_url = f"https://libproxy.sdsu.edu/login?url=https://doi.org/{doi}"
        driver.get(proxy_url)
        sleep(8)

        if len(driver.window_handles) == 0:
            print("❌ Chrome window closed during loading.")
            return False

        driver.switch_to.window(driver.window_handles[0])

        for xpath in [
            '//a[contains(text(), "View PDF")]',
            '//a[contains(text(), "Download PDF")]',
            '//a[contains(@href, ".pdf")]',
            '//button[contains(text(), "PDF")]'
        ]:
            try:
                pdf_button = driver.find_element(By.XPATH, xpath)
                pdf_button.click()
                print(f"✅ Clicked PDF button: {xpath}")
                sleep(10)
                return True
            except WebDriverException as e:
                if isinstance(e, NoSuchWindowException):
                    print("❌ Browser window was closed. Skipping DOI.")
                    return False
                continue

        print("❌ No PDF button found after all attempts.")
        return False

    except NoSuchWindowException:
        print("❌ Chrome window was closed externally.")
        return False
    except Exception as e:
        print(f"❌ Selenium failed: {e}")
        return False

# Actual PDF downloader
def download_pdf(pdf_url, filename, doi=None):
    try:
        headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/pdf"}
        with requests.get(pdf_url, headers=headers, timeout=20, stream=True, allow_redirects=True) as r:
            if r.status_code == 200 and b"<html" not in r.content[:100].lower():
                with open(filename, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                print(f"✅ PDF saved: {filename}")
                return True
            else:
                raise ValueError("Bot protection or invalid content")
    except:
        if doi:
            return download_via_sdsu_proxy(doi)
        return False

# Fetch all matching articles
def fetch_full_pubmed_papers(journal_query, keywords, start_year=2015):
    keyword_query = " OR ".join([f'\"{kw}\"[All Fields]' for kw in keywords])
    query = f'("{journal_query}"[Journal]) AND ({keyword_query}) AND ("{start_year}"[PDAT] : "3000"[PDAT])'

    try:
        search_handle = Entrez.esearch(db="pubmed", term=query, usehistory="y", retmax=0)
        search_results = Entrez.read(search_handle)
        search_handle.close()

        count = int(search_results["Count"])
        if count == 0:
            return []

        webenv = search_results["WebEnv"]
        query_key = search_results["QueryKey"]

        all_papers = []
        batch_size = 200

        for start in range(0, count, batch_size):
            fetch_handle = Entrez.efetch(
                db="pubmed", rettype="medline", retmode="text",
                retstart=start, retmax=batch_size,
                webenv=webenv, query_key=query_key
            )
            records = Medline.parse(fetch_handle)

            for record in records:
                pmid = record.get("PMID", "")
                authors = "; ".join(record.get("AU", []))
                title = record.get("TI", "")
                journal = record.get("JT", "")
                pub_date = record.get("DP", "")
                abstract = record.get("AB", "")
                doi = record.get("LID", "").split()[0].replace("[doi]", "") if "doi" in record.get("LID", "") else None
                citation_count = fetch_citation_count(pmid)
                pubmed_url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"

                pdf_url, pmc_id = get_pdf_url_from_pmc(pmid)
                pdf_path = ""
                if pdf_url:
                    pdf_filename = os.path.join(pdf_folder, f"{pmc_id or pmid}.pdf")
                    if os.path.exists(pdf_filename):
                        print(f"🔁 Skipping already downloaded: {pdf_filename}")
                        pdf_path = pdf_filename
                    else:
                        if download_pdf(pdf_url, pdf_filename, doi=doi):
                            pdf_path = pdf_filename
                elif doi:
                    if download_via_sdsu_proxy(doi):
                        pdf_path = "Downloaded via SDSU Proxy"

                all_papers.append({
                    "Title": title,
                    "Authors": authors,
                    "Journal": journal,
                    "Publication Date": pub_date,
                    "Abstract": abstract,
                    "Citations Count": citation_count,
                    "PubMed URL": pubmed_url,
                    "PDF Path": pdf_path
                })

            fetch_handle.close()
            sleep(1)

        return all_papers
    except Exception as e:
        print(f"❗ Error for {journal_query}: {e}")
        return []

# Master loop through journal list
all_results = []

for index, row in tqdm(journal_info.iterrows(), total=len(journal_info), desc="Fetching Full Metadata from PubMed"):
    abbrev = str(row['PubMed Abbreviation']).strip()
    raw_issns = str(row['Issn']).strip().replace(" ", "")
    issn_list = [issn.strip() for issn in raw_issns.split(",") if issn.strip()]

    print(f"\n🔍 Searching with Abbreviation: {abbrev}")
    papers = fetch_full_pubmed_papers(abbrev, keywords, start_year=2015)

    if not papers:
        for issn in issn_list:
            print(f"⚠️ No results with abbreviation. Trying raw ISSN: {issn}")
            papers = fetch_full_pubmed_papers(issn, keywords, start_year=2015)
            if papers:
                print(f"✅ Found {len(papers)} papers with ISSN: {issn}")
                break
            if len(issn) == 8:
                formatted_issn = issn[:4] + '-' + issn[4:]
                print(f"🔁 Trying formatted ISSN: {formatted_issn}")
                papers = fetch_full_pubmed_papers(formatted_issn, keywords, start_year=2015)
                if papers:
                    print(f"✅ Found {len(papers)} papers with formatted ISSN: {formatted_issn}")
                    break

    if papers:
        print(f"✅ Final success — {len(papers)} papers added.")
    else:
        print(f"❌ No papers found for {abbrev} / {raw_issns}")

    all_results.extend(papers)
    sleep(1)

# Save results
output_path = "PubMed_Gelation_FullData_2015_2025.csv"
df_out = pd.DataFrame(all_results)
df_out.to_csv(output_path, index=False)
print(f"\n✅ Extraction complete. Total papers: {len(df_out)}")
print(f"📄 File saved: {output_path}")

# Close the Selenium driver
driver.quit()
