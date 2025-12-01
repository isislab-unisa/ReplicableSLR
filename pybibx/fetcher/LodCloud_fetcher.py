import requests
import csv
import time

BASE_CATALOG_URL = "https://lod-cloud.net/versions/2025-09-02/lod-data.json"
BASE_PAGE_URL = "https://lod-cloud.net/dataset/"

class LodCloudFetcher:
    def __init__(self, max_retries=3, delay=2):
        self.catalog = {}
        self.max_retries = max_retries
        self.delay = delay

    def fetch_catalog(self):
        """Download the LOD Cloud catalog (official JSON)"""
        if self.catalog:
            return
        print("[INFO] Downloading LOD Cloud catalog...")
        retries = 0
        while retries < self.max_retries:
            try:
                response = requests.get(BASE_CATALOG_URL, timeout=30)
                if response.status_code == 200:
                    self.catalog = response.json()
                    print(f"[INFO] Catalog downloaded: {len(self.catalog)} datasets")
                    return
                else:
                    print(f"[WARN] Status {response.status_code}, retry in {self.delay}s...")
            except requests.exceptions.RequestException as e:
                print(f"[WARN] Error: {e}, retry in {self.delay}s...")
            time.sleep(self.delay)
            retries += 1
        raise Exception(f"Failed to download catalog after {self.max_retries} attempts")

    def _normalize_text(self, value, lang='en'):
        """Convert dict/list/None to a clean string, taking only the desired language"""
        if isinstance(value, str):
            return value
        elif isinstance(value, dict):
            return str(value.get(lang, ''))
        elif isinstance(value, list):
            return " ".join([self._normalize_text(v, lang) for v in value])
        return ""

    def filter_dataset(self, dataset, include_terms, exclude_terms, year_min=2014, year_max=2027):
        """Filter datasets according to TITLE/ABS/KEY and year"""
        text = " ".join([
            self._normalize_text(dataset.get('title', ''), lang='en'),
            self._normalize_text(dataset.get('description', ''), lang='en'),
            self._normalize_text(dataset.get('tags', []), lang='en')
        ]).lower()

        # AND group 1
        if not any(term.lower() in text for term in include_terms[0]):
            return False
        # AND group 2
        if not any(term.lower() in text for term in include_terms[1]):
            return False
        # NOT group
        if any(term.lower() in text for term in exclude_terms):
            return False

        # Filter by year
        created = dataset.get('created')
        if created:
            try:
                year = int(created)
                if year < year_min or year > year_max:
                    return False
            except ValueError:
                pass

        return True

    def fetch(self, include_terms, exclude_terms, year_min=2014, year_max=2027):
        """Return datasets filtered according to the provided query"""
        self.fetch_catalog()
        results = []
        for dataset_id, entry in self.catalog.items():
            dataset = {
                'id': dataset_id,
                'title': entry.get('title', ''),
                'description': entry.get('description', ''),
                'tags': entry.get('keywords', []) or entry.get('tags', []),
                'created': entry.get('issued', '')[:4] if 'issued' in entry else None,
                'url': f"{BASE_PAGE_URL}{dataset_id}"
            }

            if self.filter_dataset(dataset, include_terms, exclude_terms, year_min, year_max):
                results.append(dataset)

        # Deduplication based on English title
        seen = set()
        unique_results = []
        for r in results:
            key = self._normalize_text(r.get('title', ''), lang='en').lower()
            if key not in seen:
                unique_results.append(r)
                seen.add(key)

        print(f"[INFO] Filtered and unique datasets: {len(unique_results)}")
        return unique_results

    def save_as_csv(self, datasets, filename='lodcloud_results.csv'):
        if not datasets:
            print("[WARN] No datasets to save.")
            return
        fieldnames = ['title', 'description', 'tags', 'created', 'url']
        with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for d in datasets:
                writer.writerow({
                    'title': self._normalize_text(d['title'], lang='en'),
                    'description': self._normalize_text(d['description'], lang='en'),
                    'tags': self._normalize_text(d['tags'], lang='en'),
                    'created': d['created'],
                    'url': d['url']
                })
        print(f"[INFO] CSV file saved: {filename}")

    def save_as_bib(self, datasets, filename='lodcloud_results.bib'):
        if not datasets:
            print("[WARN] No datasets to save in BibTeX.")
            return

        def escape(s):
            if not s:
                return ''
            return s.replace('&', '\\&').replace('%', '\\%').replace('#', '\\#') \
                    .replace('_', '\\_').replace('{', '\\{').replace('}', '\\}')

        with open(filename, 'w', encoding='utf-8') as f:
            for i, d in enumerate(datasets):
                key = f"lodcloud{i+1}"
                title = escape(self._normalize_text(d['title'], lang='en'))
                year = d['created'] if d['created'] else ''
                url = d['url']
                note_parts = []
                desc = self._normalize_text(d['description'], lang='en')
                tags = self._normalize_text(d['tags'], lang='en')
                if desc:
                    note_parts.append(escape(desc))
                if tags:
                    note_parts.append(f"Tags: {escape(tags)}")
                note = " -- ".join(note_parts)
                f.write(
                    f"@misc{{{key},\n"
                    f"  title={{{title}}},\n"
                    f"  year={{{year}}},\n"
                    f"  howpublished={{\\url{{{url}}}}},\n"
                    f"  note={{{note}}}\n"
                    f"}}\n\n"
                )
        print(f"[INFO] BibTeX file saved: {filename}")
