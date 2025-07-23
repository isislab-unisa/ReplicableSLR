import requests
from urllib.parse import quote
import xml.etree.ElementTree as ET

API_KEY = "INSERISCI-LA-TUA-API-KEY"
BASE_URL = "http://ieeexploreapi.ieee.org/api/v1/search/articles"

def search_ieee_by_doi(doi, max_records=1):
    query = f'doi:"{doi}"'
    return search_ieee(query, max_records=max_records)

def search_ieee_by_title(title, max_records=1):
    query = f'"{title}"'
    return search_ieee(query, max_records=max_records)

def search_ieee(query, max_records=10):
    params = {
        "apikey": API_KEY,
        "format": "json",
        "max_records": max_records,
        "start_record": 1,
        "sort_order": "desc",
        "sort_field": "article_number",
        "querytext": query
    }

    response = requests.get(BASE_URL, params=params)
    if response.status_code != 200:
        raise Exception(f"Errore IEEE API: {response.status_code} - {response.text}")
    return response.json()

def get_references(article_number):
    # IEEE non offre una API diretta per le citazioni backward
    # Ma spesso ci sono riferimenti bibliografici nei metadati
    print(f"[INFO] IEEE non supporta direttamente i riferimenti backward tramite API.")
    return []

def get_citations(article_number):
    # IEEE Xplore non supporta forward citations via API
    print(f"[WARN] Forward citations non supportate da IEEE API.")
    return []
