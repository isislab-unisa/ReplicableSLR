from pybibx.Snowballing.Scopus.client import ScopusClient

class SnowballingEngine:
    def __init__(self, api_key):
        self.client = ScopusClient(api_key)

    def snowball(self, eid):
        result = {}

        # Info base e citazioni ricevute
        base = self.client.get_abstract(eid)
        core = base['abstracts-retrieval-response']
        result['title'] = core.get('coredata', {}).get('dc:title')
        result['citations'] = int(core.get('coredata', {}).get('citedby-count', 0))

        # Forward (articoli che citano)
        citers = self.client.get_citers(eid)
        result['forward'] = [
            {
                'title': i.get('dc:title'),
                'eid': i.get('eid')
            }
            for i in citers.get('search-results', {}).get('entry', [])
        ]

        # Backward (articoli citati)
        refs = self.client.get_references(eid)
        result['backward'] = [
            {
                'title': r.get('ref-info', {}).get('ref-title', {}).get('ref-titletext'),
                'doi': r.get('ref-info', {}).get('refd-itemidlist', [{}])[0].get('$')
            }
            for r in refs.get('abstracts-retrieval-response', {}).get('references', {}).get('reference', [])
        ]

        return result
