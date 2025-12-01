# backward_snowballing.py
import requests

class BackwardSnowball:
    """
    Retrieves the references of a Scopus article given its SCOPUS ID.
    Uses the Scopus Abstract Retrieval API and, if not available, falls back to CrossRef via DOI.
    Returns a list of dicts with: title, authors, doi, year, source.
    """

    def __init__(self, api_key):
        if not api_key:
            raise ValueError("Scopus API key required")
        self.api_key = api_key
        self.base_url = "https://api.elsevier.com/content/abstract/scopus_id/{scopus_id}?view=FULL"
        self.headers = {"X-ELS-APIKey": self.api_key, "Accept": "application/json"}
        self.crossref_url = "https://api.crossref.org/works/{doi}"

    def backward(self, scopus_id):
        if not scopus_id:
            raise ValueError("SCOPUS ID not provided")

        references = []

        # 🔹 1) Scopus Abstract Retrieval API
        url = self.base_url.format(scopus_id=scopus_id)
        doi_main = None
        try:
            r = requests.get(url, headers=self.headers)
            if r.status_code == 200:
                data = r.json()

                # Save main DOI for CrossRef fallback
                doi_main = data.get("abstracts-retrieval-response", {}) \
                               .get("coredata", {}) \
                               .get("prism:doi", None)

                # List of references
                ref_list = data.get("abstracts-retrieval-response", {}) \
                               .get("references", {}) \
                               .get("reference", [])

                for ref in ref_list:
                    ref_info = ref.get("ref-info", {})
                    title = ref_info.get("ref-title", {}).get("content", "")
                    
                    authors = ""
                    if "ref-authors" in ref and ref["ref-authors"]:
                        authors_list = ref["ref-authors"].get("author", [])
                        authors = "; ".join([a.get("ce:indexed-name", "") for a in authors_list if a])

                    doi = ref_info.get("ref-doi", "")
                    year = ref_info.get("ref-publicationyear", "")
                    source = ref_info.get("ref-publicationname", "")

                    references.append({
                        "title": title,
                        "authors": authors,
                        "doi": doi,
                        "year": year,
                        "source": source
                    })
            else:
                print(f"[WARN] Abstract API failed for {scopus_id}, status {r.status_code}")

        except Exception as e:
            print(f"[ERROR] Error during Scopus retrieval: {e}")

        # 🔹 2) CrossRef fallback if no references and DOI is available
        if not references and doi_main:
            print(f"[INFO] No references found in Scopus, trying CrossRef for DOI {doi_main}")
            try:
                r = requests.get(self.crossref_url.format(doi=doi_main))
                if r.status_code == 200:
                    data = r.json()
                    items = data.get("message", {}).get("reference", [])
                    for ref in items:
                        references.append({
                            "title": ref.get("article-title", ""),
                            "authors": ref.get("author", ""),
                            "doi": ref.get("DOI", ""),
                            "year": ref.get("year", ""),
                            "source": ref.get("journal-title", "")
                        })
                else:
                    print(f"[WARN] CrossRef failed for DOI {doi_main}, status {r.status_code}")
            except Exception as e:
                print(f"[ERROR] Error during CrossRef fallback: {e}")

        if not references:
            print(f"[INFO] No references retrieved for SCOPUS ID {scopus_id}")

        return references
