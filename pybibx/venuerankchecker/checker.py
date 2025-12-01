import os
import pandas as pd

class VenueRankChecker:
    def __init__(self, core_source, scimago_source):
        self.core = core_source
        self.scimago = scimago_source

    def check_all(self, venue_name, log=True):
        print(f"\n🔎 Checking venue: '{venue_name}'")
        self.core.check(venue_name, log)
        self.scimago.check(venue_name, log)

    def show_log(self, log_path="venue_rank_log.csv"):
        if not os.path.exists(log_path):
            print("⚠️ No log found.")
            return
        log_df = pd.read_csv(log_path)
        if log_df.empty:
            print("📄 The log is empty.")
        else:
            print("\n📚 Saved search log:")
            print(log_df.to_string(index=False))

    def available_years(self):
        print("📅 Available years:")
        print(f"CORE: {self.core.available_years()}")
        print(f"SCIMAGO: {self.scimago.available_years()}")
