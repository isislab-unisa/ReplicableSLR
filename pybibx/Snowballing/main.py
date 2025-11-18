# main.py
import os
import csv
import hashlib
from dotenv import load_dotenv
from Scopus_Fetcher import ScopusFetcher
from Snowballing_analyzer import load_articles, find_article_by_title
from backward_snowballing import BackwardSnowball
from forward_snowballing import ForwardSnowball

# ---------------- CONFIG ----------------
BASE_DIR = r"C:\Users\maria\Desktop\ReplicableSLR\pybibx\Snowballing"
RESULTS_DIR = os.path.join(BASE_DIR, "Results_Snowballing")
os.makedirs(RESULTS_DIR, exist_ok=True)

ENV_PATH = os.path.join(BASE_DIR, "scopus_key.env")
load_dotenv(ENV_PATH)
API_KEY = os.getenv("SCOPUS_API_KEY")
if not API_KEY:
    raise ValueError("⚠️ SCOPUS_API_KEY non trovata!")

# CSV principali
CSV_PATH = os.path.join(BASE_DIR, "scopus_query.csv")
MINIMAL_CSV = os.path.join(BASE_DIR, "scopus_query_minimal.csv")
BACKWARD_CSV = os.path.join(RESULTS_DIR, "backward_snowballing.csv")
FORWARD_CSV = os.path.join(RESULTS_DIR, "forward_snowballing.csv")
LOG_QUERIES_CSV = os.path.join(BASE_DIR, "queries_log.csv")

# ---------------- FUNZIONI ----------------
def hash_query(query):
    """Crea hash MD5 della query per tracking."""
    return hashlib.md5(query.encode("utf-8")).hexdigest()

def update_queries_log(query, csv_path):
    """Aggiorna il log delle query eseguite."""
    if not os.path.exists(LOG_QUERIES_CSV):
        with open(LOG_QUERIES_CSV, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=["query_hash", "query", "csv_path"])
            writer.writeheader()
    with open(LOG_QUERIES_CSV, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["query_hash", "query", "csv_path"])
        writer.writerow({"query_hash": hash_query(query), "query": query, "csv_path": csv_path})

def check_query_cache(query):
    """Verifica se la query è già stata eseguita e ritorna il CSV esistente."""
    query_hash = hash_query(query)
    if os.path.exists(LOG_QUERIES_CSV):
        with open(LOG_QUERIES_CSV, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["query_hash"] == query_hash and os.path.exists(row["csv_path"]):
                    return row["csv_path"]
    return None

# ---------------- COSTRUISCI QUERY ----------------
print("Inserisci la query per Scopus (TITLE-ABS-KEY, AND, OR, NOT, ecc.):")
query = input("> ").strip()
if not query:
    raise ValueError("Query non può essere vuota")

# ---------------- FETCH / CACHE ----------------
cached_csv = check_query_cache(query)
if cached_csv:
    print(f"[INFO] Query già eseguita, riuso CSV: {cached_csv}")
    records = load_articles(cached_csv)
else:
    print("[INFO] Eseguo query Scopus...")
    fetcher = ScopusFetcher(api_key=API_KEY, per_page=25)
    records = fetcher.fetch(query)
    if records:  # controllo per evitare di salvare un CSV vuoto
        fetcher.save_csv(records, CSV_PATH)
        update_queries_log(query, CSV_PATH)
    else:
        print("[WARN] Nessun record recuperato, CSV non salvato.")
    records = load_articles(CSV_PATH) if records else []

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

# ---------------- LOOP ARTICOLI ----------------
while True:
    search_title = input("Inserisci il titolo dell'articolo su cui fare snowballing:\n> ").strip()
    article = find_article_by_title(records, search_title)
    if not article:
        print("❌ Articolo non trovato nel CSV.")
        cont = input("Vuoi provare con un altro titolo? (s/n) ").strip().lower()
        if cont != "s":
            print("[INFO] Fine operazione di snowballing")
            break
        else:
            continue

    scopus_id = article["scopus_id"]
    origin_title = article["title"]
    origin_year = article.get("year", "")
    print(f"[INFO] Articolo selezionato: {origin_title} (SCOPUS ID: {scopus_id})")

    # ---------------- BACKWARD SNOWBALLING ----------------
    existing_backward_ids = set()
    if os.path.exists(BACKWARD_CSV):
        with open(BACKWARD_CSV, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                sid = row.get("scopus_id") or row.get("doi") or ""
                if sid:
                    existing_backward_ids.add(sid)

    new_backward = []
    bs = BackwardSnowball(api_key=API_KEY)
    for r in bs.backward(scopus_id):
        sid = r.get("scopus_id") or r.get("doi") or ""
        if sid not in existing_backward_ids:
            new_backward.append(r)

    print(f"[INFO] Articoli citati (backward) nuovi trovati: {len(new_backward)}")

    if new_backward:
        fieldnames = list(new_backward[0].keys())
        mode = "a" if existing_backward_ids else "w"
        with open(BACKWARD_CSV, mode, newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if mode == "w":
                writer.writeheader()
            writer.writerows(new_backward)
        print(f"[INFO] Backward snowballing aggiornato in {BACKWARD_CSV}")
    else:
        print("[INFO] Nessun nuovo articolo citato da aggiungere per backward snowballing")

    # ---------------- FORWARD SNOWBALLING ----------------
    existing_forward_ids = set()
    if os.path.exists(FORWARD_CSV):
        with open(FORWARD_CSV, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                fid = row.get("scopus_id") or row.get("doi") or ""
                if fid:
                    existing_forward_ids.add(fid)

    forward_snowball = ForwardSnowball(api_key=API_KEY, per_page=25)
    new_forward = []
    for r in forward_snowball.forward_snowball(scopus_id, origin_title, origin_year):
        fid = r.get("scopus_id") or r.get("doi") or ""
        if fid not in existing_forward_ids:
            new_forward.append(r)

    print(f"[INFO] Articoli che citano (forward) nuovi trovati: {len(new_forward)}")
    forward_snowball.append_csv(new_forward, FORWARD_CSV, mode="a" if existing_forward_ids else "w")

    # ---------------- CONTINUA? ----------------
    cont = input("Vuoi trovare citanti e citati di un altro articolo? (s/n) ").strip().lower()
    if cont != "s":
        print("[INFO] Fine operazione di snowballing")
        break
