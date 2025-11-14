# main.py
import os
import csv
from dotenv import load_dotenv
from Scopus_Fetcher import ScopusFetcher
from Snowballing_analyzer import load_articles, find_article_by_title
from backward_snowballing import BackwardSnowball
from forward_snowballing import ForwardSnowball

# ---------------- CONFIG ----------------
BASE_DIR = r"C:\Users\maria\Desktop\ReplicableSLR\pybibx\Snowballing"
CSV_PATH = os.path.join(BASE_DIR, "scopus_query.csv")
MINIMAL_CSV = os.path.join(BASE_DIR, "scopus_query_minimal.csv")
RESULTS_DIR = os.path.join(BASE_DIR, "Results_Snowballing")
BACKWARD_CSV = os.path.join(RESULTS_DIR, "backward_snowballing.csv")
FORWARD_CSV = os.path.join(RESULTS_DIR, "forward_snowballing.csv")
ENV_PATH = os.path.join(BASE_DIR, "scopus_key.env")

os.makedirs(RESULTS_DIR, exist_ok=True)

# ---------------- LOAD API KEY ----------------
load_dotenv(ENV_PATH)
API_KEY = os.getenv("SCOPUS_API_KEY")
if not API_KEY:
    raise ValueError("⚠️ SCOPUS_API_KEY non trovata!")

# ---------------- COSTRUISCI QUERY ----------------
print("Inserisci la query per Scopus (TITLE-ABS-KEY, AND, OR, NOT, ecc.):")
query = input("> ").strip()
if not query:
    raise ValueError("Query non può essere vuota")

# ---------------- FETCH RESULTS ----------------
fetch_data = True
if os.path.exists(CSV_PATH):
    with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        if rows:
            print(f"[INFO] CSV esistente trovato con {len(rows)} risultati, riuso i dati")
            records = rows
            fetch_data = False

if fetch_data:
    fetcher = ScopusFetcher(api_key=API_KEY, per_page=25)
    records = fetcher.fetch(query)
    fetcher.save_csv(records, CSV_PATH)
    print(f"[INFO] Risultati salvati in {CSV_PATH}")

# ---------------- SALVATAGGIO CSV RIDOTTO ----------------
if records:
    minimal_fields = ["scopus_id", "eid", "title", "references", "cited_by"]
    minimal_records = [
        {
            "scopus_id": r.get("scopus_id", ""),
            "eid": r.get("eid", ""),
            "title": r.get("title", ""),
            "references": r.get("references", ""),
            "cited_by": r.get("cited_by", r.get("citations", 0))
        } for r in records
    ]
    with open(MINIMAL_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=minimal_fields)
        writer.writeheader()
        writer.writerows(minimal_records)
    print(f"[INFO] CSV minimale salvato in {MINIMAL_CSV}")

# ---------------- LOAD CSV ----------------
records = load_articles(CSV_PATH)

# ---------------- SELEZIONE ARTICOLO ----------------
search_title = input("Inserisci il titolo dell'articolo su cui fare snowballing:\n> ").strip()
article = find_article_by_title(records, search_title)
if not article:
    print("❌ Articolo non trovato nel CSV. Esco.")
    exit(1)

scopus_id = article["scopus_id"]
origin_title = article["title"]
origin_year = article.get("year", "")
print(f"[INFO] Articolo selezionato: {origin_title} (SCOPUS ID: {scopus_id})")

# ---------------- BACKWARD SNOWBALLING ----------------
backward = BackwardSnowball(api_key=API_KEY).backward(scopus_id)
print(f"[INFO] Articoli citati (backward) trovati: {len(backward)}")
if backward:
    fieldnames = list(backward[0].keys())
    with open(BACKWARD_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(backward)
    print(f"[INFO] Backward snowballing salvato in {BACKWARD_CSV}")
else:
    print("[INFO] Nessun articolo citato trovato per backward snowballing")

# ---------------- FORWARD SNOWBALLING ----------------
forward_snowball = ForwardSnowball(api_key=API_KEY, per_page=25)
forward = forward_snowball.forward_snowball(scopus_id, origin_title, origin_year)
print(f"[INFO] Articoli che citano (forward) trovati: {len(forward)}")
forward_snowball.append_csv(forward, FORWARD_CSV, mode="w")
