from pybibx.scopus.snowballing import ScopusSnowballing

API_KEY = "INSERISCI-LA-TUA-API-KEY"
IDENTIFIER = "10.1016/j.future.2019.05.024"  # può essere anche "2-s2.0-85070600192"

sb = ScopusSnowballing(API_KEY)

# Citazioni totali
count = sb.get_citations_count(IDENTIFIER)
print(f"[INFO] Citazioni totali: {count}")

# Articoli che citano (forward)
forward = sb.get_forward_citations(IDENTIFIER)
print(f"[FORWARD] Articoli che citano:")
for f in forward:
    print(f" - {f.get('dc:title', '[Nessun titolo]')}")

# Articoli citati (backward)
backward = sb.get_references(IDENTIFIER)
print(f"[BACKWARD] Articoli citati:")
for b in backward:
    print(f" - {b.get('ref-title', '[Nessun titolo]')}")
