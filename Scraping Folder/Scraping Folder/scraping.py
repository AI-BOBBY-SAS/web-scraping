import pandas as pd
from Bio import Entrez, Medline
from time import sleep
from tqdm import tqdm

Entrez.email = "jshaik2452@sdsu.edu"

# Load journal abbreviations and ISSNs
df = pd.read_excel("All Journals List.xlsx")
journal_info = df[['PubMed Abbreviation', 'Issn']].dropna()

# Define keywords
keywords = ['Gel', 'Gelation', 'Gel Hardness']

# Fetch citation count
def fetch_citation_count(pmid):
    try:
        handle = Entrez.elink(dbfrom="pubmed", db="pubmed", linkname="pubmed_pubmed_citedin", id=pmid)
        records = Entrez.read(handle)
        handle.close()
        linksets = records[0].get("LinkSetDb", [])
        if linksets:
            return len(linksets[0]["Link"])
        else:
            return 0
    except:
        return 0

# Fetch all matching articles
def fetch_full_pubmed_papers(journal_query, keywords, start_year=2015):
    keyword_query = " OR ".join([f'"{kw}"[All Fields]' for kw in keywords])
    query = f'("{journal_query}"[Journal]) AND ({keyword_query}) AND ("{start_year}"[PDAT] : "3000"[PDAT])'

    try:
        # Get search count
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
                db="pubmed",
                rettype="medline",
                retmode="text",
                retstart=start,
                retmax=batch_size,
                webenv=webenv,
                query_key=query_key
            )
            records = Medline.parse(fetch_handle)

            for record in records:
                pmid = record.get("PMID", "")
                authors = "; ".join(record.get("AU", []))
                title = record.get("TI", "")
                journal = record.get("JT", "")
                pub_date = record.get("DP", "")
                abstract = record.get("AB", "")
                citation_count = fetch_citation_count(pmid)
                pubmed_url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"

                all_papers.append({
                    "Title": title,
                    "Authors": authors,
                    "Journal": journal,
                    "Publication Date": pub_date,
                    "Abstract": abstract,
                    "Citations Count": citation_count,
                    "PubMed URL": pubmed_url
                })

            fetch_handle.close()
            sleep(1)

        return all_papers
    except Exception as e:
        print(f"❗ Error for {journal_query}: {e}")
        return []

# Run full extraction with ISSN fallback (now handles multiple ISSNs)
all_results = []

for index, row in tqdm(journal_info.iterrows(), total=len(journal_info), desc="Fetching Full Metadata from PubMed"):
    abbrev = str(row['PubMed Abbreviation']).strip()
    raw_issns = str(row['Issn']).strip().replace(" ", "")  # remove whitespace
    issn_list = [issn.strip() for issn in raw_issns.split(",") if issn.strip()]

    print(f"\n🔍 Searching with Abbreviation: {abbrev}")
    papers = fetch_full_pubmed_papers(abbrev, keywords, start_year=2015)

    # If abbreviation fails, go through each ISSN variant
    if not papers:
        for issn in issn_list:
            print(f"⚠️ No results with abbreviation. Trying raw ISSN: {issn}")
            papers = fetch_full_pubmed_papers(issn, keywords, start_year=2015)

            if papers:
                print(f"✅ Found {len(papers)} papers with ISSN: {issn}")
                break  # stop if papers found

            if len(issn) == 8:
                formatted_issn = issn[:4] + '-' + issn[4:]
                print(f"🔁 Trying formatted ISSN: {formatted_issn}")
                papers = fetch_full_pubmed_papers(formatted_issn, keywords, start_year=2015)

                if papers:
                    print(f"✅ Found {len(papers)} papers with formatted ISSN: {formatted_issn}")
                    break  # stop if papers found

    if papers:
        print(f"✅ Final success — {len(papers)} papers added.")
    else:
        print(f"❌ No papers found for {abbrev} / {raw_issns}")

    all_results.extend(papers)
    sleep(1)


# Save results
df_out = pd.DataFrame(all_results)
df_out.to_csv("PubMed_Gelation_FullData_2015_2025.csv", index=False)

print(f"\n✅ Extraction complete. Total papers: {len(df_out)}")
print("📄 File saved: PubMed_Gelation_FullData_2015_2025.csv")
