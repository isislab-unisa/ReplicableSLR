import requests
import csv
from datetime import datetime
import os

class ZenodoFetcher:
    def __init__(self):
        self.base_url = "https://zenodo.org/api/records"

    def fetch_records(self, query, max_results=50):
        """
        Cerca record su Zenodo usando la query specificata.
        Restituisce una lista di dizionari con metadati essenziali.
        """
        params = {
            'q': query,
            'size': min(max_results, 100),
            'sort': 'mostdownloaded',
            'all_versions': 'false'
        }

        print(f"[INFO] Chiamata API Zenodo per query: '{query}' con max {params['size']} risultati")
        response = requests.get(self.base_url, params=params)

        if response.status_code != 200:
            raise Exception(f"Errore API Zenodo: {response.status_code} - {response.text}")

        items = response.json().get('hits', {}).get('hits', [])
        records = []

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
            records.append(record)

        print(f"[INFO] Trovati {len(records)} record Zenodo")
        return records

    def save_as_csv(self, data, filename='zenodo_output.csv'):
        """
        Salva i dati Zenodo in formato CSV, ordinati per numero di download (discendente).
        """
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
                formatted_row = {
                    k: " ".join(str(v).split()) if isinstance(v, str) else v
                    for k, v in row.items()
                }
                writer.writerow(formatted_row)

        print(f"[INFO] File CSV Zenodo salvato come '{filename}' con {len(data_sorted)} record.")

    def save_as_bib(self, records, filename='zenodo_output.bib'):
        """
        Salva i dati Zenodo in formato BibTeX, ordinati per numero di download.
        """
        if not records:
            print("[WARN] Nessun record da salvare in BibTeX.")
            return

        records_sorted = sorted(records, key=lambda x: x.get('downloads', 0), reverse=True)

        def escape_bibtex(s):
            if not s:
                return ''
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
}}

"""
                f.write(bib_entry)

        print(f"[INFO] File BibTeX Zenodo salvato come '{filename}' con {len(records_sorted)} record.")

    def print_records(self, records, max_display=10):
        """
        Stampa a schermo una selezione di record.
        """
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


if __name__ == "__main__":
    zen = ZenodoFetcher()
    records = zen.fetch_records("machine learning", max_results=30)

    # Stampa i primi 5 record
    zen.print_records(records, max_display=5)

    # Salva i risultati
    zen.save_as_csv(records, "zenodo_ml.csv")
    zen.save_as_bib(records, "zenodo_ml.bib")

    # Funzioni per aprire i file localmente (solo su Windows)
    def open_file_local(filename):
        try:
            os.startfile(filename)  # Solo su Windows
            print(f"[INFO] File '{filename}' aperto nel programma associato.")
        except Exception as e:
            print(f"[ERRORE] Impossibile aprire il file: {e}")

    def download_csv_file(filename='zenodo_ml.csv'):
        open_file_local(filename)

    def download_bib_file(filename='zenodo_ml.bib'):
        open_file_local(filename)

    # Esempio: apri CSV (facoltativo)
    # download_csv_file()
    # download_bib_file()
