import requests
import csv
from datetime import datetime
import os
import time

class ZenodoFetcher:
    def __init__(self, max_retries=3, delay=5):
        self.base_url = "https://zenodo.org/api/records"
        self.max_retries = max_retries
        self.delay = delay

    def fetch_records(self, query, max_results=50):
        """
        Cerca record su Zenodo usando la query specificata.
        Restituisce una lista di dizionari con metadati essenziali.
        """
        results = []
        size = min(max_results, 100)
        retries = 0

        while retries < self.max_retries:
            try:
                params = {
                    'q': query,
                    'size': size,
                    'sort': 'mostdownloaded',
                    'all_versions': 'false'
                }

                print(f"[INFO] Chiamata API Zenodo per query: '{query}' con max {size} risultati")
                response = requests.get(self.base_url, params=params, timeout=30)

                if response.status_code == 200:
                    items = response.json().get('hits', {}).get('hits', [])
                    for item in items:
                        metadata = item.get('metadata', {})
                        record = {
                            'title': metadata.get('title'),
                            'author': ", ".join([creator.get('name') for creator in metadata.get('creators', [])]),
                            'description': metadata.get('description'),
                            'created': item.get('created'),
                            'updated': item.get('updated'),
                            'language': metadata.get('language'),
                            'downloads': item.get('stats', {}).get('downloads', 0),
                            'url': item.get('links', {}).get('html'),
                            'license': metadata.get('license', {}).get('id') if isinstance(metadata.get('license'), dict) else metadata.get('license')
                        }
                        results.append(record)
                    return results
                else:
                    print(f"[WARN] Ricevuto status {response.status_code}, retry in {self.delay}s...")
                    time.sleep(self.delay)
                    retries += 1
            except requests.exceptions.RequestException as e:
                print(f"[ERRORE] {e}, retry in {self.delay}s...")
                time.sleep(self.delay)
                retries += 1

        raise Exception(f"Errore API Zenodo persistente dopo {self.max_retries} tentativi.")

    def save_as_csv(self, data, filename='zenodo_output.csv'):
        if not data:
            print("[WARN] Nessun dato da salvare.")
            return

        data_sorted = sorted(data, key=lambda x: x.get('downloads', 0), reverse=True)
        for i, row in enumerate(data_sorted, start=1):
            row['n'] = i

        fieldnames = ['n'] + [k for k in data_sorted[0].keys() if k != 'n']

        with open(filename, mode='w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in data_sorted:
                formatted_row = {k: " ".join(str(v).split()) if isinstance(v, str) else v for k, v in row.items()}
                writer.writerow(formatted_row)

        print(f"[INFO] File CSV Zenodo salvato come '{filename}' con {len(data_sorted)} record.")

    def save_as_bib(self, records, filename='zenodo_output.bib'):
        if not records:
            print("[WARN] Nessun record da salvare in BibTeX.")
            return

        records_sorted = sorted(records, key=lambda x: x.get('downloads', 0), reverse=True)

        def escape_bibtex(s):
            if not s: return ''
            s = s.replace('&', '\\&').replace('%', '\\%').replace('#', '\\#')
            s = s.replace('_', '\\_').replace('{', '\\{').replace('}', '\\}')
            return s

        with open(filename, 'w', encoding='utf-8') as f:
            for i, rec in enumerate(records_sorted):
                key = f"zenodo{i+1}"
                title = escape_bibtex(rec.get('title', 'NoTitle'))
                author = escape_bibtex(rec.get('author', 'NoAuthor'))
                year = ''
                if rec.get('created'):
                    try:
                        year = datetime.strptime(rec['created'], '%Y-%m-%dT%H:%M:%S.%fZ').year
                    except:
                        year = ''
                url = rec.get('url', '')
                note_parts = []
                if rec.get('description'):
                    note_parts.append(escape_bibtex(rec['description']))
                if rec.get('language'):
                    note_parts.append(f"Language: {escape_bibtex(rec['language'])}")
                if rec.get('downloads') is not None:
                    note_parts.append(f"Downloads: {rec['downloads']}")
                if rec.get('license'):
                    note_parts.append(f"License: {escape_bibtex(rec['license'])}")
                note = ' -- '.join(note_parts)

                bib_entry = f"""@misc{{{key},
  title = {{{title}}},
  author = {{{author}}},
  year = {{{year}}},
  howpublished = {{\\url{{{url}}}}},
  note = {{{note}}}
}}\n
"""
                f.write(bib_entry)

        print(f"[INFO] File BibTeX Zenodo salvato come '{filename}' con {len(records_sorted)} record.")

    def print_records(self, records, max_display=10):
        if not records:
            print("[INFO] Nessun record da visualizzare.")
            return

        records_sorted = sorted(records, key=lambda x: x.get('downloads', 0), reverse=True)
        for i, rec in enumerate(records_sorted[:max_display], start=1):
            print(f"\n=== Record {i} ===")
            print(f"Titolo     : {rec.get('title', 'N/A')}")
            print(f"Autore/i   : {rec.get('author', 'N/A')}")
            print(f"Creato il  : {rec.get('created', 'N/A')}")
            print(f"Lingua     : {rec.get('language', 'N/A')}")
            print(f"Download   : {rec.get('downloads', 0)}")
            print(f"Licenza    : {rec.get('license', 'N/A')}")
            print(f"URL        : {rec.get('url', 'N/A')}")
            print(f"Descrizione: {(rec.get('description', '')[:300] + '...') if rec.get('description') and len(rec['description']) > 300 else rec.get('description', 'N/A')}")

# === ESEMPIO DI USO CON SOTTO-QUERY ===
if __name__ == "__main__":
    zen = ZenodoFetcher()
    queries = [
        '"cloud computing" ontology NOT "internet of things" NOT iot NOT healthcare',
        '"multi-cloud" ontology NOT "internet of things"',
        '"cloud interoperability" ontology',
        '"cloud migration" ontology',
        '"application portability" ontology'
    ]

    all_records = []
    for q in queries:
        try:
            recs = zen.fetch_records(q, max_results=50)
            all_records.extend(recs)
            time.sleep(2)  # pausa tra chiamate
        except Exception as e:
            print(f"[ERRORE] Query '{q}' fallita: {e}")

    # Rimuove duplicati (basato su titolo e autore)
    seen = set()
    unique_records = []
    for r in all_records:
        key = (r.get('title'), r.get('author'))
        if key not in seen:
            seen.add(key)
            unique_records.append(r)

    zen.print_records(unique_records, max_display=10)
    zen.save_as_csv(unique_records, "zenodo_results.csv")
    zen.save_as_bib(unique_records, "zenodo_results.bib")
