from .base import BaseSource
from .utils import fuzzy_match, log_result, parse_coverage
import pandas as pd
from .decorators import log_call

class ScimagoSource(BaseSource):
    @log_call
    def check(self, venue_name, log=True):
        name = venue_name.strip().lower()
        matches = []

        for y, df in sorted(self.data_by_year.items(), reverse=True):
            df = df.copy()
            df['Title'] = df['Title'].str.strip().str.lower()

            match = df[df['Title'] == name]
            if match.empty:
                best_title = fuzzy_match(name, df['Title'].tolist())
                if best_title:
                    match = df[df['Title'] == best_title]

            if not match.empty and parse_coverage(match.iloc[0]['Coverage'], y):
                matches.append((y, match.iloc[0]))

        if not matches:
            print(f"[SCIMAGO] ❌ Venue non trovato o non coperto in nessun anno: '{venue_name}'")
            return

        years_found = [y for y, _ in matches]
        most_recent_year, row = max(matches, key=lambda x: x[0])

        print(f"[SCIMAGO] ✅ Trovato in {sorted(years_found)} → Anno più recente: {most_recent_year}")
        print(f"   🧭 SJR: {row['SJR']} | 🏅 Quartile: {row['SJR Best Quartile']} | 📈 H-index: {row['H index']}")

        if log:
            log_result("SCIMAGO", row['Title'], most_recent_year, "SJR", row['SJR'])
            log_result("SCIMAGO", row['Title'], most_recent_year, "Quartile", row['SJR Best Quartile'])
            log_result("SCIMAGO", row['Title'], most_recent_year, "H-index", row['H index'])

    def available_years(self):
        return sorted(self.data_by_year.keys())
