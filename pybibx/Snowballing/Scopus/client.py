import requests

class ScopusClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base = "https://api.elsevier.com/content"
        self.headers = {
            'Accept': 'application/json',
            'X-ELS-APIKey': self.api_key
        }

    def get_abstract(self, eid):
        url = f"{self.base}/abstract/eid/{eid}"
        r = requests.get(url, headers=self.headers)
        r.raise_for_status()
        return r.json()

    def get_references(self, eid):
        url = f"{self.base}/abstract/eid/{eid}/references"
        r = requests.get(url, headers=self.headers)
        r.raise_for_status()
        return r.json()

    def get_citers(self, eid):
        url = f"{self.base}/abstract/citations/eid/{eid}"
        r = requests.get(url, headers=self.headers)
        r.raise_for_status()
        return r.json()
