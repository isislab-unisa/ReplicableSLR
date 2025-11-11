import os
from dotenv import load_dotenv
from Snowballing_fetcher import SnowballingFetcher
from Snowballing_analyzer import load_articles, analyze_article

BASE_DIR = r"C:\Users\maria\Desktop\ReplicableSLR\pybibx\Snowballing"
CSV_PATH = os.path.join(BASE_DIR, "scopus_query.csv")
ENV_PATH = os.path.join(BASE_DIR, "scopus_key.env")

load_dotenv(ENV_PATH)
API_KEY = os.getenv("SCOPUS_API_KEY")
if not API_KEY:
    raise ValueError("⚠️ SCOPUS_API_KEY non trovata!")

fetcher = SnowballingFetcher(API_KEY)

# Se il CSV non esiste, eseguo la query iniziale
if not os.path.exists(CSV_PATH):
    print("[INFO] Nessun file di risultati trovato. Eseguo la query iniziale...")
    query = 'TITLE-ABS-KEY("cloud computing" AND "ontology")'
    results = fetcher.fetch_query(query)
    fetcher.save_csv(results, CSV_PATH)
else:
    print("[INFO] File CSV trovato, procedo con l’analisi...")

# Carica articoli e analizza
records = load_articles(CSV_PATH)
analyze_article(fetcher, records, BASE_DIR)
