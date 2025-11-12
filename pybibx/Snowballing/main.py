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

if not os.path.exists(CSV_PATH):
    print("[INFO] Nessun file di risultati trovato. Eseguo la query iniziale...")
    query = 'TITLE-ABS-KEY("cloud computing" AND "ontology")'
    results = fetcher.fetch_query(query)
    fetcher.append_csv(results, CSV_PATH, "initial", "query")
else:
    print("[INFO] File CSV trovato, procedo con l’analisi...")

records = load_articles(CSV_PATH)

# --- Loop interattivo per analisi multipla ---
while True:
    analyze_article(fetcher, records, BASE_DIR)
    cont = input("\nVuoi analizzare un altro articolo? (s/n): ").strip().lower()
    if cont != "s":
        print("👋 Fine sessione di snowballing.")
        break
