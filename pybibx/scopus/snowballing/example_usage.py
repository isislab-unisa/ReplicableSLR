from pybibx.scopus.snowballing import ScopusSnowballing

API_KEY = "INSERISCI-LA-TUA-API-KEY"
IDENTIFIER = "10.1016/j.future.2019.05.024"  # oppure EID: "2-s2.0-85070600192"

sb = ScopusSnowballing(API_KEY)

# 1. Citazioni totali
print(f"[INFO] Citazioni totali: {sb.get_citations_count(IDENTIFIER)}")

# 2. Articoli che citano (forward)
forward = sb.get_forward_citations(IDENTIFIER)
print("[FORWARD] Articoli che citano:")
for f in forward:
    print(" -", f.get("dc:title", "[Sconosciuto]"))

# 3. Articoli citati (backward)
backward = sb.get_references(IDENTIFIER)
print("[BACKWARD] Articoli citati:")
for b in backward:
    print(" -", b.get("ref-title", "[Sconosciuto]"))

# 4. Salvataggio CSV
sb.save_forward_to_csv(IDENTIFIER, filename="citanti.csv")
sb.save_backward_to_csv(IDENTIFIER, filename="citati.csv")
