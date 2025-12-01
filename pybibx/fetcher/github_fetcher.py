import os
import requests
import csv
from datetime import datetime
from dotenv import load_dotenv
import time

class GitHubFetcher:
    def __init__(self, token=None):
        self.base_url = "https://api.github.com/search/repositories"
        self.headers = {}
        if token:
            self.headers['Authorization'] = f'token {token}'

    def fetch_repositories(self, query, max_results=100):
        print(f"[INFO] Executing query: {query}")
        all_results = []
        page = 1

        while len(all_results) < max_results:
            params = {
                'q': query,
                'per_page': 100,
                'page': page
            }
            response = requests.get(self.base_url, headers=self.headers, params=params)

            # --- 🔹 Automatic rate limit handling
            if response.status_code == 403 and "rate limit" in response.text.lower():
                reset_time = response.headers.get('X-RateLimit-Reset')
                if reset_time:
                    reset_timestamp = datetime.fromtimestamp(int(reset_time))
                    wait_seconds = max(0, (reset_timestamp - datetime.utcnow()).seconds) + 5
                    print(f"[WARN] API rate limit reached — waiting {wait_seconds} seconds until {reset_timestamp}...")
                    time.sleep(wait_seconds)
                else:
                    print("[WARN] API rate limit reached — waiting 60 seconds...")
                    time.sleep(60)
                continue  # retry request after waiting

            if response.status_code != 200:
                raise Exception(f"GitHub API error: {response.status_code} - {response.text}")

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

            # --- 🔹 Rate limit info
            remaining = response.headers.get('X-RateLimit-Remaining')
            print(f"[INFO] Page {page} completed ({len(items)} results). Remaining limit: {remaining}")

            # --- 🔹 Safety pause between requests
            time.sleep(3)

            if len(items) < 100:
                break
            page += 1

        print(f"[INFO] Retrieved {len(all_results)} results for the query")
        return all_results


    def save_as_csv(self, data, filename):
        if not data:
            print("[WARN] No data to save.")
            return
        with open(filename, mode='w', newline='', encoding='utf-8-sig') as csvfile:
            fieldnames = ['title', 'author', 'description', 'created', 'updated',
                          'language', 'stars', 'url', 'license']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        print(f"[INFO] CSV file saved as '{filename}'")

    def save_as_bib(self, data, filename):
        if not data:
            print("[WARN] No data to save.")
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
        print(f"[INFO] BibTeX file saved as '{filename}'")
