import requests
import csv
from datetime import datetime
from tabulate import tabulate


class GitHubFetcher:
    def __init__(self, token=None):
        """
        Inizializza la classe con un token GitHub opzionale (consigliato per limiti più alti).
        """
        self.base_url = "https://api.github.com/search/repositories"
        self.headers = {}
        if token:
            self.headers['Authorization'] = f'token {token}'

    def fetch_repositories(self, query, max_results=50):
        """
        Esegue la ricerca su GitHub per la 'query' fornita e restituisce una lista di dict.
        """
        if max_results > 100:
            max_results = 100  # Limite GitHub

        params = {
            'q': query,
            'per_page': max_results,
            'sort': 'stars',
            'order': 'desc'
        }

        print(f"[INFO] Chiamata API GitHub per query: '{query}' con max {max_results} risultati")
        response = requests.get(self.base_url, headers=self.headers, params=params)
        if response.status_code != 200:
            raise Exception(f"Errore API GitHub: {response.status_code} - {response.text}")

        data = response.json()
        items = data.get("items", [])
        records = []

        for item in items:
            record = {
                'title': item.get('name'),
                'author': item.get('owner', {}).get('login'),
                'description': item.get('description'),
                'created': item.get('created_at'),
                'updated': item.get('updated_at'),
                'language': item.get('language'),
                'stars': item.get('stargazers_count'),
                'url': item.get('html_url'),
                'license': item.get('license', {}).get('name') if item.get('license') else None
            }
            records.append(record)

        print(f"[INFO] Trovati {len(records)} repository")
        return records

    def save_as_csv(self, data, filename='output.csv'):
        """
        Salva i dati dei repository in un file CSV ordinato per stelle (desc), con indice numerico.
        """
        if not data:
            print("[WARN] Nessun dato da salvare.")
            return

        # Ordina i dati per 'stars' in modo decrescente
        data_sorted = sorted(data, key=lambda x: x.get('stars', 0), reverse=True)

        # Aggiungi numerazione
        for i, row in enumerate(data_sorted, start=1):
            row['n'] = i  # Colonna con numero progressivo

        # Intestazioni: 'n' come prima colonna
        fieldnames = ['n'] + [key for key in data_sorted[0].keys() if key != 'n']

        with open(filename, mode='w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for row in data_sorted:
                formatted_row = {
                    k: " ".join(str(v).split()) if isinstance(v, str) else v
                    for k, v in row.items()
                }
                writer.writerow(formatted_row)

        print(f"[INFO] File CSV salvato come '{filename}' con {len(data_sorted)} elementi ordinati per stelle.")

    def save_as_bib(self, records, filename='output.bib'):
        """
        Salva i dati dei repository in formato BibTeX, ordinati per stelle (desc).
        """
        if not records:
            print("[WARN] Nessun record da salvare in BibTeX.")
            return

        # Ordina per numero di stelle, decrescente
        records_sorted = sorted(records, key=lambda x: x.get('stars', 0), reverse=True)

        def escape_bibtex(s):
            if not s:
                return ''
            s = s.replace('&', '\\&').replace('%', '\\%').replace('#', '\\#')
            s = s.replace('_', '\\_').replace('{', '\\{').replace('}', '\\}')
            return s

        with open(filename, 'w', encoding='utf-8') as f:
            for i, rec in enumerate(records_sorted):
                key = f"github{i+1}"
                title = escape_bibtex(rec.get('title', 'NoTitle'))
                author = escape_bibtex(rec.get('author', 'NoAuthor'))
                year = ''
                if rec.get('created'):
                    try:
                        year = datetime.strptime(rec['created'], '%Y-%m-%dT%H:%M:%SZ').year
                    except Exception:
                        year = ''
                url = rec.get('url', '')
                note_parts = []
                if rec.get('description'):
                    note_parts.append(escape_bibtex(rec['description']))
                if rec.get('language'):
                    note_parts.append(f"Language: {escape_bibtex(rec['language'])}")
                if rec.get('stars') is not None:
                    note_parts.append(f"Stars: {rec['stars']}")
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

        print(f"[INFO] File BibTeX salvato: {filename} con {len(records_sorted)} record ordinati per stelle.")


if __name__ == "__main__":
    # esempio di uso standalone
    import os
    from dotenv import load_dotenv

    # Specifica esplicitamente il file .env da caricare
    load_dotenv("token.env")

    # Recupera il token
    token = os.getenv("GITHUB_TOKEN")

    # Usa il token
    fetcher = GitHubFetcher(token=token)
    query = "machine learning"
    results = fetcher.fetch_repositories(query=query, max_results=100)
    # Stampa riassuntiva tabellare dei primi 10 risultati
    print("\n[INFO] Anteprima risultati GitHub (Top 10):\n")
    table_data = []
    for i, r in enumerate(results[:10], start=1):
        table_data.append([
            i,
            r['title'],
            r['author'],
            r['language'],
            r['stars'],
            r['license'] or '',
            r['url']
        ])

    headers = ["#", "Title", "Author", "Lang", "Stars", "License", "URL"]
    print(tabulate(table_data, headers=headers, tablefmt="grid", maxcolwidths=[None, 30, 15, 10, 7, 15, 40]))

    # Salva CSV e BibTeX
    fetcher.save_as_csv(results, "github_results.csv")
    fetcher.save_as_bib(results, "github_results.bib")
 # Funzioni per aprire i file localmente (solo su Windows)
    def open_file_local(filename):
        try:
            os.startfile(filename)  # Funziona solo su Windows
            print(f"[INFO] File '{filename}' aperto nel programma associato.")
        except Exception as e:
            print(f"[ERRORE] Impossibile aprire il file: {e}")

    def download_csv_file(filename='github_results.csv'):
        open_file_local(filename)

    def download_bib_file(filename='github_results.bib'):
        open_file_local(filename)