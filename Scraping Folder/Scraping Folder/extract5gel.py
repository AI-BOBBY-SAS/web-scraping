import os
import re
import requests
from Bio import Entrez
from time import sleep
import pandas as pd

# Set your email for Entrez
Entrez.email = "vkhanna5744@sdu.edu"

# Create output folders
download_dir = os.path.join(os.path.expanduser("~"), "Desktop", "papers1")
os.makedirs(download_dir, exist_ok=True)

download_pdf_dir = os.path.join(os.path.expanduser("~"), "Desktop", "downloaded_papers1")
os.makedirs(download_pdf_dir, exist_ok=True)

# Protein-related keywords
protein_keywords = [
    "Protein", "Protein Isolate", "Protein Concentrate", "Soy Protein", "Soy Protein Isolate", "SPI",
    "Soy Protein Concentrate", "SPC", "Pea Protein", "Pea Protein Concentrate", "PPC",
    "Pea Protein Isolate", "PPI", "Yellow Pea Protein Concentrate", "YPC", "Yellow Pea Protein Isolate", "YPPI",
    "Potato Protein", "Potato Protein Isolate", "Mung Bean Protein Isolate", "MBPI",
    "Chickpea Protein Isolate", "Chickpea Protein Concentrate", "CChPC", "Faba Bean Protein",
    "Faba Bean Protein Concentrate", "FPC", "Faba Bean Flour", "FBF", "Cotyledon Flour",
    "Hull flour", "Peanut Protein", "Peanut Protein Isolate",
    "Peanut protein isolate & Arachin", "Arachin",
    "Peanut protein isolate & Conarachin", "Conarachin",
    "Soy protein isolate & β-conglycinin", "β-conglycinin",
    "M. oleifera protein isolate & Micellized Protein", "Micellized Protein",
    "M. oleifera protein isolate & Isoelectric Protein", "Isoelectric Protein",
    "Soy Protein Isolate & Glycinin", "Glycinin"
]

# Search queries related to gelation
search_queries = [
    '"gelation + hardness" AND "gelation + WHC"',
    '("protein gels" OR "protein gel")',
    '("protein gels" NOT "polysaccharide gels")',
    '("protein gels + hardness" AND "protein gels + WHC")',
    '("plant-based gels" OR "plant-based gelation")',
    '"plant protein gelation + hardness" AND "plant protein gelation + WHC"',
    '"animal protein gelation + hardness" AND "animal protein gelation + WHC"'
]

# Full list of journals (shortened here for preview)
journals =  [
    "Nature Sustainability",
    "Nature Food",
    "Trends in Food Science and Technology",
    "Comprehensive Reviews in Food Science and Food Safety",
    "Food Hydrocolloids",
    "Global Food Security",
    "Advances in Nutrition",
    "Annual review of food science and technology",
    "Food Policy",
    "Critical Reviews in Food Science and Nutrition",
    "Food Chemistry",
    "Food Frontiers",
    "Current Opinion in Food Science",
    "Food Security",
    "Food Research International",
    "Food Packaging and Shelf Life",
    "Journal of Animal Science and Biotechnology",
    "Innovative Food Science and Emerging Technologies",
    "Food Reviews International",
    "Meat Science",
    "LWT",
    "Nutrients",
    "Postharvest Biology and Technology",
    "Antioxidants",
    "Journal of Dairy Science",
    "Journal of Food Engineering",
    "Food Chemistry: X",
    "Food Structure",
    "Food Control",
    "Grain and Oil Science and Technology",
    "Food Science and Human Wellness",
    "Food Quality and Preference",
    "Current Nutrition Reports",
    "Food and Function",
    "Journal of the Academy of Nutrition and Dietetics",
    "Current Research in Food Science",
    "Future Foods",
    "Food and Energy Security",
    "Molecular Nutrition and Food Research",
    "Food Microbiology",
    "International Journal of Food Microbiology",
    "Applied and Environmental Microbiology",
    "Food and Bioprocess Technology",
    "Biosystems Engineering",
    "NFS Journal",
    "Annals of Agricultural Sciences",
    "npj Science of Food",
    "Food Bioscience",
    "Journal of Integrative Agriculture",
    "Journal of the International Society of Sports Nutrition",
    "Food Hydrocolloids for Health",
    "Chemical and Biological Technologies in Agriculture",
    "Journal of Cereal Science",
    "Journal of Functional Foods",
    "EFSA Journal",
    "Journal of Future Foods",
    "Journal of Insects as Food and Feed",
    "Foods",
    "International Journal of Food Contamination",
    "Frontiers in Sustainable Food Systems",
    "Agribusiness",
    "Agriculture and Food Security",
    "Food and Nutrition Research",
    "Current Developments in Nutrition",
    "Frontiers in Nutrition",
    "Applied Food Research",
    "Food Chemistry: Molecular Sciences",
    "Journal of Agriculture and Food Research",
    "Food Production, Processing and Nutrition",
    "British Food Journal",
    "Food and Waterborne Parasitology",
    "GM Crops and Food",
    "Journal of Food Science",
    "Legume Science",
    "Agricultural and Food Economics",
    "Environmental Research Communications",
    "Food and Chemical Toxicology",
    "Journal of Animal Science",
    "International Dairy Journal",
    "Bioresources and Bioprocessing",
    "Food Science and Nutrition",
    "Journal of the Science of Food and Agriculture",
    "Natural Products and Bioprospecting",
    "Advanced Agrochem",
    "International Journal of Food Sciences and Nutrition",
    "Journal of Food Composition and Analysis",
    "Food and Bioproducts Processing",
    "Food Biophysics",
    "NJAS - Wageningen Journal of Life Sciences",
    "Food Quality and Safety",
    "Journal of Food Biochemistry",
    "Food Science of Animal Resources",
    "Journal of Loss Prevention in the Process Industries",
    "International Journal of Food Science and Technology",
    "eFood",
    "European Food Research and Technology",
    "Biocatalysis and Agricultural Biotechnology",
    "Journal of Texture Studies",
    "CABI Agriculture and Bioscience",
    "Journal of Food Science and Technology",
    "Food and Nutrition Bulletin",
    "International Journal of Food Properties",
    "Plant Foods for Human Nutrition",
    "Journal of Stored Products Research",
    "Bioscience of Microbiota, Food and Health",
    "Iraqi Journal of Agricultural Sciences",
    "International Journal of Dairy Technology",
    "Journal of Nutritional Science",
    "Animal Bioscience",
    "Food Chemistry Advances",
    "Bioactive Carbohydrates and Dietary Fibre",
    "Journal of Food Measurement and Characterization",
    "International Journal of Gastronomy and Food Science",
    "International Journal of Food Science",
    "Journal of Food and Drug Analysis",
    "Cereal Chemistry",
    "Agriculture (Switzerland)",
    "Meat and Muscle Biology",
    "Food Science and Biotechnology",
    "Journal of Dietary Supplements",
    "Journal of Food Products Marketing",
    "Journal of Food Process Engineering",
    "Journal of Health, Population and Nutrition",
    "Beverages",
    "Journal of Foodservice Business Research",
    "Food and Environmental Virology",
    "Annual Plant Reviews Online",
    "Potato Research",
    "Journal of Food Quality",
    "ES Food and Agroforestry",
    "Food Additives and Contaminants: Part B Surveillance",
    "Recent patents on food, nutrition & agriculture",
    "Renewable Agriculture and Food Systems",
    "Nutrition Research and Practice",
    "Fermentation",
    "Foodborne Pathogens and Disease",
    "Nutrition and Metabolic Insights",
    "Journal of Nutrition and Metabolism",
    "Lifestyle Genomics",
    "Journal of Animal Science and Technology",
    "Journal of Dairy Research",
    "British Poultry Science",
    "Systems Microbiology and Biomanufacturing",
    "Animal Science Journal",
    "Food Additives and Contaminants - Part A Chemistry, Analysis, Control, Exposure and Risk Assessment",
    "CYTA - Journal of Food",
    "Journal of Food Processing and Preservation",
    "Phytochemical Analysis",
    "AgriEngineering",
    "Starch/Staerke",
    "Food Science and Technology International",
    "Journal of the American Society of Brewing Chemists",
    "Measurement: Food",
    "Journal of Food Safety",
    "Applied Animal Science",
    "Food Analytical Methods",
    "ACS Food Science and Technology",
    "Oeno One",
    "Beverage Plant Research",
    "European Journal of Lipid Science and Technology",
    "Journal of Food Protection",
    "Bio-based and Applied Economics",
    "Journal of Agricultural and Food Industrial Organization",
    "American Journal of Enology and Viticulture",
    "Cogent Food and Agriculture",
    "PharmaNutrition",
    "Turkish Journal of Agriculture and Forestry",
    "Food Technology and Biotechnology",
    "Polish Journal of Food and Nutrition Sciences",
    "ACS Agricultural Science and Technology",
    "Journal of the Institute of Brewing",
    "Flavour and Fragrance Journal",
    "Journal of Wine Economics",
    "Journal of Sustainable Forestry",
    "Q Open",
    "Nutrition and Healthy Aging",
    "International Food and Agribusiness Management Review",
    "Ecology of Food and Nutrition",
    "Preventive Nutrition and Food Science",
    "Journal of the ASABE",
    "Journal of Ethnic Foods",
    "Journal of International Food and Agribusiness Marketing",
    "OCL - Oilseeds and fats, Crops and Lipids",
    "Quality Assurance and Safety of Crops and Foods",
    "AIMS Agriculture and Food",
    "Animal Production Science",
    "Journal of Environmental Science and Health - Part B Pesticides, Food Contaminants, and Agricultural Wastes",
    "Journal of AOAC International",
    "World Mycotoxin Journal",
    "Journal of Sensory Studies",
    "Food Ethics",
    "Food, Culture and Society",
    "Food Biotechnology",
    "International Journal of Food Engineering",
    "Acta Scientiarum Polonorum, Technologia Alimentaria",
    "Agricultural and Food Science",
    "Human Nutrition and Metabolism",
    "Food and Agricultural Immunology",
    "Agricultural Research",
    "Italian Journal of Food Safety",
    "Food Additives and Contaminants",
    "Ciencia e Agrotecnologia",
    "AgBioForum",
    "Journal of Aquatic Food Product Technology",
    "Bioactive Compounds in Health and Disease",
    "Advances in Agriculture",
    "Journal of Animal and Feed Sciences",
    "Czech Journal of Food Sciences",
    "Asian Fisheries Science",
    "Caraka Tani: Journal of Sustainable Agriculture",
    "Food and Foodways",
    "Journal of Berry Research",
    "Journal of Inclusion Phenomena and Macrocyclic Chemistry",
    "Journal fur Verbraucherschutz und Lebensmittelsicherheit",
    "Ciencia e Tecnica Vitivinicola",
    "Italian Journal of Food Science",
    "Boletin de la Asociacion Espanola de Entomologia",
    "Culture, Agriculture, Food and Environment",
    "Irish Journal of Agricultural and Food Research",
    "Foods and Raw Materials",
    "Eastern-European Journal of Enterprise Technologies",
    "Acta Scientiarum - Animal Sciences",
    "South African Journal of Enology and Viticulture",
    "Nutrition and Food Science",
    "Journal of Wine Research",
    "Mljekarstvo",
    "Italian Review of Agricultural Economics",
    "Nestle Nutrition Institute Workshop Series",
    "Grasas y Aceites",
    "Journal of Horticultural Research",
    "International Journal of Food Design",
    "Jurnal Ilmiah Perikanan dan Kelautan",
    "Journal of Applied Biology and Biotechnology",
    "Applied Food Biotechnology",
    "Italus Hortus",
    "Functional Foods in Health and Disease",
    "Range Management and Agroforestry",
    "International Journal on Food System Dynamics",
    "Journal of Applied Botany and Food Quality",
    "Wine Economics and Policy",
    "Global Food History",
    "Food Bioengineering",
    "Journal of Culinary Science and Technology",
    "Journal of Oil Palm Research",
    "Emirates Journal of Food and Agriculture",
    "Outlooks on Pest Management",
    "Agriculture and Forestry",
    "Journal of the Korean Society of Food Science and Nutrition",
    "Shokuhin eiseigaku zasshi. Journal of the Food Hygienic Society of Japan",
    "Journal of Nanjing Forestry University (Natural Sciences Edition)",
    "Food Research",
    "Food Science and Technology Research",
    "Current Research in Nutrition and Food Science",
    "Brazilian Journal of Food Technology",
    "Canrea Journal: Food Technology, Nutritions, and Culinary Journal",
    "Revista Iberoamericana de Viticultura Agroindustria y Ruralidad",
    "Arabian Journal of Medicinal and Aromatic Plants",
    "Revista Brasileira de Fruticultura",
    "Mediterranean Journal of Nutrition and Metabolism",
    "Eurobiotech Journal",
    "Acta Alimentaria",
    "Biotech Studies",
    "Journal of Microbiology, Biotechnology and Food Sciences",
    "International Journal of Sociology of Agriculture and Food",
    "Annals of the University Dunarea de Jos of Galati, Fascicle VI: Food Technology",
    "Potravinarstvo",
    "Current Nutrition and Food Science",
    "Journal of Food and Nutrition Research",
    "Journal of Food Chemistry and Nanotechnology",
    "Pakistan Journal of Agricultural Sciences",
    "Recent Advances in Food, Nutrition and Agriculture",
    "Revista Facultad Nacional de Agronomia Medellin",
    "Squalen Bulletin of Marine and Fisheries Postharvest and Biotechnology",
    "Korean Journal of Food Science and Technology",
    "International Journal of Food Studies",
    "International Food Research Journal",
    "Korean Journal of Food Preservation",
    "Ukrainian Food Journal",
    "Coffee Science",
    "Linguistic Variation",
    "Fruits",
    "INMATEH - Agricultural Engineering",
    "Journal of Food Quality and Hazards Control",
    "World Review of Nutrition and Dietetics",
    "Universal Journal of Agricultural Research",
    "Revista Chilena de Nutricion",
    "Progress in Nutrition",
    "Malaysian Journal of Nutrition",
    "International Journal of Nutrition Sciences",
    "Journal of Tea Science",
    "Journal of Fruit Science",
    "Vitae",
    "Asian Journal of Dairy and Food Research",
    "Agronomia Mesoamericana",
    "Future of Food: Journal on Food, Agriculture and Society",
    "Revue d'Elevage et de Medecine Veterinaire des Pays Tropicaux",
    "African Journal of Food, Agriculture, Nutrition and Development",
    "Shipin Kexue/Food Science",
    "Indonesian Journal of Agricultural Science",
    "Economia Agro-Alimentare",
    "Food Protection Trends",
    "Journal of Agricultural and Food Information",
    "Journal of Food Science and Technology (China)",
    "Membrane Technology",
    "Japan Journal of Food Engineering",
    "Indonesian Journal of Biotechnology",
    "Nutrire",
    "Engineering in Agriculture, Environment and Food",
    "Carpathian Journal of Food Science and Technology",
    "Theory and Practice of Meat Processing",
    "Journal of Food Science Education",
    "Revista Espanola de Nutricion Humana y Dietetica",
    "Indian Journal of Natural Products and Resources",
    "Uludag Aricilik Dergisi",
    "Acta Fytotechnica et Zootechnica",
    "Voprosy Detskoi Dietologii",
    "Animal Production Research",
    "Journal of Nutrition and Food Security",
    "Food Processing: Techniques and Technology",
    "Journal of Research and Innovation in Food Science and Technology",
    "Science and Engineering Journal",
    "Online Journal of Animal and Feed Research",
    "Agrochimica",
    "Food Engineering Progress",
    "Pisevye Sistemy/Food Systems",
    "Journal of Food Distribution Research",
    "Food Science and Technology (United States)",
    "Revista de Ciencias Agroveterinarias",
    "BrewingScience",
    "Zywnosc. Nauka. Technologia. Jakosc/Food. Science Technology. Quality",
    "Journal of Chinese Institute of Food Science and Technology",
    "Food and Fermentation Industries",
    "Journal of the Zhejiang University - Agriculture and Life Science",
    "Journal of the Chinese Cereals and Oils Association",
    "Akademik Gida",
    "Bulletin of the Transilvania University of Brasov, Series II: Forestry, Wood Industry, Agricultural Food Engineering",
    "Journal of Food Science and Biotechnology",
    "Revista Academica Ciencia Animal",
    "Revista de la Facultad de Agronomia",
    "Journal of Food Science and Technology (Iran)",
    "Agrarforschung Schweiz",
    "Science and Technology of Food Industry",
    "Agricultural Research Journal",
    "International Journal of Postharvest Technology and Innovation",
    "Meat Technology",
    "International Journal Bioautomation",
    "Organic Farming",
    "Food and History",
    "Modern Food Science and Technology",
    "Japanese Journal of Crop Science",
    "Biomedical and Biopharmaceutical Research",
    "Food Science and Technology",
    "Zeitschrift fur Arznei- und Gewurzpflanzen",
    "Iranian Journal of Nutrition Sciences and Food Technology",
    "Zuckerindustrie",
    "Science and Technology of Cereals, Oils and Foods",
    "Journal of Food Legumes",
    "Nippon Shokuhin Kagaku Kogaku Kaishi",
    "Journal of Excipients and Food Chemicals",
    "Nigerian Journal of Nutritional Sciences",
    "Food Technology",
    "Analytical Science and Technology",
    "Pesticide Research Journal",
    "Archiv fur Lebensmittelhygiene",
    "INFORM",
    "Nova Biotechnologica et Chimica",
    "Revista Cientifica de la Facultad de Ciencias Veterinarias de la Universidad del Zulia",
    "European Food and Feed Law Review",
    "Elelmiszervizsgalati Kozlemenyek",
    "Fourrages",
    "Journal of Caffeine and Adenosine Research",
    "Food Studies",
    "Kufa Journal for Agricultural Sciences",
    "Agroalimentaria",
    "China Condiment",
    "Food Chemistry, Function and Analysis",
    "International Sugar Journal",
    "Deutsche Lebensmittel-Rundschau",
    "Industrie Alimentari",
    "Dairy Industries International",
    "Fleischwirtschaft",
    "Taiwanese Journal of Agricultural Chemistry and Food Science",
    "Ernahrung",
    "Correspondances en MHND",
    "Seibutsu-kogaku Kaishi",
    "Food Manufacture",
    "Food Safety and Risk",
    "Food Science and Technology (Brazil) (discontinued)",
    "Journal of Agriculture and Crops (discontinued)",
    "Journal of Hygienic Engineering and Design (discontinued)",
    "Sustainable Food Technology"
]


# Search PubMed
def search_pubmed(journal, query, max_results=20):
    search_term = f'({query}) AND "{journal}"[Journal]'
    handle = Entrez.esearch(db="pubmed", term=search_term, retmax=max_results)
    record = Entrez.read(handle)
    handle.close()
    return record["IdList"]

# Fetch metadata
def fetch_metadata(pmid):
    try:
        handle = Entrez.efetch(db="pubmed", id=pmid, rettype="xml", retmode="text")
        record = Entrez.read(handle)
        handle.close()
        article = record["PubmedArticle"][0]["MedlineCitation"]["Article"]
        title = article.get("ArticleTitle", "No Title")
        abstract = article.get("Abstract", {}).get("AbstractText", [""])[0]
        ids = record["PubmedArticle"][0]["PubmedData"]["ArticleIdList"]
        doi = ""
        for aid in ids:
            if aid.attributes["IdType"] == "doi":
                doi = str(aid)
        link = f"https://doi.org/{doi}" if doi else f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
        return title, abstract, link
    except Exception as e:
        print(f"Error fetching metadata for {pmid}: {e}")
        return None, None, None

# Check if relevant based on protein keywords
def is_relevant(text):
    for term in protein_keywords:
        if re.search(re.escape(term), text, re.IGNORECASE):
            return True
    return False

# Extract protein type
def extract_protein_type(text):
    for term in protein_keywords:
        if re.search(re.escape(term), text, re.IGNORECASE):
            return term
    return ""

# Try to download PDF via PubMed Central
def try_download_pdf(pmid, title):
    try:
        base_url = f"https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/?ids={pmid}&format=json"
        r = requests.get(base_url)
        data = r.json()
        records = data.get("records", [])
        if not records or "pmcid" not in records[0]:
            return "No PDF link"

        pmcid = records[0]["pmcid"]
        pdf_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/pdf/"
        response = requests.get(pdf_url, headers={"User-Agent": "Mozilla/5.0"})
        if response.status_code == 200:
            safe_title = re.sub(r'[\\/*?:"<>|]', "", title)[:80] + ".pdf"
            with open(os.path.join(download_pdf_dir, safe_title), "wb") as f:
                f.write(response.content)
            return "Downloaded"
        else:
            return "PDF access denied"
    except Exception as e:
        return f"Failed: {e}"

# Store results
results = []

# Main search loop
for query in search_queries:
    for journal in journals:
        print(f"\n Searching: {query} in {journal}")
        try:
            pmids = search_pubmed(journal, query, max_results=50)
        except Exception as e:
            print(f"⚠️ Skipped {journal} | Error: {e}")
            continue
        sleep(0.5)
        for pmid in pmids:
            title, abstract, link = fetch_metadata(pmid)
            if not title or not abstract:
                continue
            full_text = f"{title} {abstract}"
            if is_relevant(full_text):
                protein_type = extract_protein_type(full_text)
                download_status = try_download_pdf(pmid, title)
                results.append({
                    "PMID": pmid,
                    "Title": title,
                    "Abstract": abstract[:500] + "...",
                    "Link": link,
                    "Protein Type (guessed)": protein_type,
                    "PDF Download": download_status
                })
            sleep(0.3)

# Save results
df = pd.DataFrame(results)
csv_path = os.path.join(download_dir, "gelation_results4.csv")
df.to_csv(csv_path, index=False)

print(f"\nDone. {len(results)} relevant papers saved.")
print(f"Metadata saved to: {csv_path}")
print(f" PDFs saved to: {download_pdf_dir}")
