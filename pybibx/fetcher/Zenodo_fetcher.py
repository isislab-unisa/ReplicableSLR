import requests
import csv
from datetime import datetime
import time


class ZenodoFetcher:
    def __init__(self, max_retries=3, delay=5):
        self.base_url = "https://zenodo.org/api/records"
        self.max_retries = max_retries
        self.delay = delay

    def fetch_records(self, query, batch_size=30, max_pages=20):
        all_results = []
        page = 1

        while True:
            if max_pages and page > max_pages:
                break

            retries = 0
            while retries < self.max_retries:
                try:
                    params = {
                        'q': query,
                        'size': batch_size,
                        'page': page,
                        'sort': 'mostdownloaded',
                        'all_versions': 'false'
                    }
                    print(f"[INFO] Chiamata API Zenodo, query: '{query}', pagina {page}")
                    response = requests.get(self.base_url, params=params, timeout=60)

                    if response.status_code == 200:
                        items = response.json().get('hits', {}).get('hits', [])
                        if not items:
                            break  # nessun record, passa alla fine

                        for item in items:
                            metadata = item.get('metadata', {})
                            doc_type = metadata.get('resource_type', {}).get('type', '').lower()
                            if doc_type not in ['publication', 'conferencepaper']:
                                continue

                            created = item.get('created')
                            language = metadata.get('language')

                            # filtro lingua e anno
                            if language and language.lower() != 'en':
                                continue
                            if created:
                                try:
                                    year = datetime.strptime(created, '%Y-%m-%dT%H:%M:%S.%fZ').year
                                    if year < 2014:
                                        continue
                                except:
                                    pass

                            record = {
                                'title': metadata.get('title'),
                                'author': ", ".join([creator.get('name') for creator in metadata.get('creators', [])]),
                                'description': metadata.get('description'),
                                'created': created,
                                'updated': item.get('updated'),
                                'language': language,
                                'downloads': item.get('stats', {}).get('downloads', 0),
                                'url': item.get('links', {}).get('html'),
                                'license': metadata.get('license', {}).get('id') if isinstance(metadata.get('license'), dict) else metadata.get('license')
                            }
                            all_results.append(record)
                        break

                    else:
                        print(f"[WARN] Status {response.status_code}, retry in {self.delay}s...")
                        time.sleep(self.delay)
                        retries += 1
                except requests.exceptions.RequestException as e:
                    print(f"[ERRORE] {e}, retry in {self.delay}s...")
                    time.sleep(self.delay)
                    retries += 1
            else:
                print(f"[ERRORE] Query '{query}', pagina {page} fallita dopo {self.max_retries} tentativi")
                break

            page += 1
            time.sleep(1)

        return all_results

    def save_as_csv(self, data, filename='zenodo_results.csv'):
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

        print(f"[INFO] File CSV salvato come '{filename}' con {len(data_sorted)} record.")

    def save_as_bib(self, records, filename='zenodo_results.bib'):
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

        print(f"[INFO] File BibTeX salvato come '{filename}' con {len(records_sorted)} record.")


if __name__ == "__main__":
    zen = ZenodoFetcher()

    # --- Keywords principali / ontologiche / esclusioni
    keywords_cloud = ['"cloud computing"', '"cloud-computing"', '"multi-cloud"']
    keywords_ontology = [
        '"ontology"', '"ontologies"', '"semantic web"', '"knowledge graph"',
        '"knowledge graphs"', '"linked data"', '"linked open data"'
    ]
    exclusions = ['"internet of things"', 'iot']

    # --- Generazione query Zenodo (solo titolo e keyword, escluso full-text)
    queries = []
    for c in keywords_cloud:
        for o in keywords_ontology:
            # Esclusioni applicate solo sulla descrizione
            excl = " ".join([f'NOT metadata.description:{e}' for e in exclusions])
            # Ricerca solo in titolo e keyword
            q = f'(metadata.title:{c} OR metadata.keywords:{c}) AND (metadata.title:{o} OR metadata.keywords:{o}) {excl}'
            queries.append(q)

    all_records = []
    for q in queries:
        try:
            print(f"[INFO] Esecuzione query limitata ai campi titolo/keyword:\n  → {q}")
            recs = zen.fetch_records(q, batch_size=30, max_pages=20)
            all_records.extend(recs)
            # salvataggio parziale
            zen.save_as_csv(all_records, "zenodo_results_partial.csv")
            time.sleep(2)
        except Exception as e:
            print(f"[ERRORE] Query '{q}' fallita: {e}")

    # --- Deduplicazione (titolo + autore)
    seen = set()
    unique_records = []
    for r in all_records:
        key = (r.get('title'), r.get('author'))
        if key not in seen:
            unique_records.append(r)
            seen.add(key)

    # --- Salvataggio finale
    zen.save_as_csv(unique_records, "zenodo_results.csv")
    zen.save_as_bib(unique_records, "zenodo_results.bib")

    print(f"[INFO] Totale record unici: {len(unique_records)}")



