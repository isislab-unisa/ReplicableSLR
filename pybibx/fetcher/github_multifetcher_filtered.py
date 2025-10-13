import os
import requests
import csv
from datetime import datetime
from dotenv import load_dotenv
from tabulate import tabulate


class GitHubFetcher:
    def __init__(self, token=None):
        self.base_url = "https://api.github.com/search/repositories"
        self.headers = {}
        if token:
            self.headers['Authorization'] = f'token {token}'

    def fetch_repositories(self, query, max_results=100):
        print(f"[INFO] Eseguo query: {query}")
        all_results = []
        page = 1

        while len(all_results) < max_results:
            params = {
                'q': query,
                'per_page': 100,
                'page': page,
                'sort': 'stars',
                'order': 'desc'
            }
            response = requests.get(self.base_url, headers=self.headers, params=params)
            if response.status_code != 200:
                raise Exception(f"Errore API GitHub: {response.status_code} - {response.text}")
            data = response.json()
            items = data.get("items", [])
            if not items:
                break
            for item in items:
                all_results.append({
                    'title': item.get('name'),
                    'author': item.get('owner', {}).get('login'),
                    'description': item.get('description'),
                    'created': item.get('created_at'),
                    'updated': item.get('updated_at'),
                    'language': item.get('language'),
                    'stars': item.get('stargazers_count'),
                    'url': item.get('html_url'),
                    'license': item.get('license', {}).get('name') if item.get('license') else None
                })
            if len(items) < 100:
                break
            page += 1
        print(f"[INFO] Trovati {len(all_results)} risultati per la query")
        return all_results

    def save_as_csv(self, data, filename):
        if not data:
            print("[WARN] Nessun dato da salvare.")
            return
        data_sorted = sorted(data, key=lambda x: x.get('stars', 0), reverse=True)
        with open(filename, mode='w', newline='', encoding='utf-8-sig') as csvfile:
            fieldnames = ['title', 'author', 'description', 'created', 'updated', 'language', 'stars', 'url', 'license']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data_sorted)
        print(f"[INFO] File CSV salvato come '{filename}'")

    def save_as_bib(self, data, filename):
        if not data:
            print("[WARN] Nessun dato da salvare.")
            return
        with open(filename, 'w', encoding='utf-8') as f:
            for i, rec in enumerate(data):
                key = f"github{i+1}"
                title = rec.get('title', '')
                author = rec.get('author', '')
                year = ''
                if rec.get('created'):
                    try:
                        year = datetime.strptime(rec['created'], '%Y-%m-%dT%H:%M:%SZ').year
                    except Exception:
                        pass
                url = rec.get('url', '')
                note = f"Language: {rec.get('language', '')}, Stars: {rec.get('stars', '')}, License: {rec.get('license', '')}"
                f.write(f"@misc{{{key}, title={{{title}}}, author={{{author}}}, year={{{year}}}, howpublished={{\\url{{{url}}}}}, note={{{note}}}}}\n\n")
        print(f"[INFO] File BibTeX salvato come '{filename}'")


if __name__ == "__main__":
    load_dotenv("token.env")
    token = os.getenv("GITHUB_TOKEN")
    fetcher = GitHubFetcher(token=token)

    # 🔹 Sotto-query (ognuna <256 caratteri)
    queries = [
        '"cloud computing" ontology language:English created:>2014-01-01',
        '"multi-cloud" ontology language:English created:>2014-01-01',
        '"cloud interoperability" ontology language:English created:>2014-01-01',
        '"cloud migration" ontology language:English created:>2014-01-01',
        '"application portability" ontology language:English created:>2014-01-01',
        '"semantic interoperability" cloud language:English created:>2014-01-01',
        '"semantic web" cloud language:English created:>2014-01-01',
        '"knowledge graph" cloud language:English created:>2014-01-01',
        '"linked data" cloud language:English created:>2014-01-01',
        '"linked open data" cloud language:English created:>2014-01-01'
    ]

    all_results = []
    for q in queries:
        results = fetcher.fetch_repositories(query=q, max_results=500)
        all_results.extend(results)

    # Rimuove duplicati in base all’URL
    seen = set()
    unique_results = []
    for r in all_results:
        if r['url'] not in seen:
            unique_results.append(r)
            seen.add(r['url'])

    print(f"[INFO] Totale risultati unici combinati: {len(unique_results)}")

    fetcher.save_as_csv(unique_results, "github_combined.csv")
    fetcher.save_as_bib(unique_results, "github_combined.bib")
