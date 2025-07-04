import os
import pandas as pd

class VenueRankChecker:
    def __init__(self, core_source, scimago_source):
        self.core = core_source
        self.scimago = scimago_source

    def check_all(self, venue_name, log=True):
        print(f"\n🔎 Verifica della venue: '{venue_name}'")
        self.core.check(venue_name, log)
        self.scimago.check(venue_name, log)

    def show_log(self, log_path="venue_rank_log.csv"):
        if not os.path.exists(log_path):
            print("⚠️ Nessun log trovato.")
            return
        log_df = pd.read_csv(log_path)
        if log_df.empty:
            print("📄 Il log è vuoto.")
        else:
            print("\n📚 Log delle ricerche salvate:")
            print(log_df.to_string(index=False))

    def available_years(self):
        print("📅 Anni disponibili:")
        print(f"CORE: {self.core.available_years()}")
        print(f"SCIMAGO: {self.scimago.available_years()}")
