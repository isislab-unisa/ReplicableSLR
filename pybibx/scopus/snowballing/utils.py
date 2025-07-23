import requests

class ScopusAPI:
    BASE_URL = "https://api.elsevier.com/content"
    
    def __init__(self, api_key):
        self.api_key = api_key
    
    def headers(self):
        return {
            "X-ELS-APIKey": self.api_key,
            "Accept": "application/json"
        }
    
    def get_json(self, url, params=None):
        response = requests.get(url, headers=self.headers(), params=params)
        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")
        return response.json()
    
    def get_eid_from_doi(self, doi):
        url = f"{self.BASE_URL}/search/scopus"
        params = {"query": f"DOI({doi})"}
        data = self.get_json(url, params)
        entries = data.get("search-results", {}).get("entry", [])
        if not entries:
            raise Exception(f"No EID found for DOI {doi}")
        return entries[0]["eid"]
