from .base import BaseSource
from .utils import fuzzy_match, log_result
import pandas as pd

class CoreSource(BaseSource):
    def check(self, venue_name, log=True):
        name = venue_name.strip().lower()
        matches = []

        for y, df in sorted(self.data_by_year.items(), reverse=True):
            df = df.copy()
            df['Title'] = df['Title'].str.strip().str.lower()
            df['Acronym'] = df['Acronym'].astype(str).str.strip().str.lower()

            match = df[(df['Title'] == name) | (df['Acronym'] == name)]
            if match.empty:
                best_title = fuzzy_match(name, df['Title'].tolist())
                match = df[df['Title'] == best_title] if best_title else None
                if match is None:
                    best_acronym = fuzzy_match(name, df['Acronym'].tolist())
                    match = df[df['Acronym'] == best_acronym] if best_acronym else None

            if match is not None and not match.empty:
                matches.append((y, match.iloc[0]))

        if not matches:
            print(f"[CORE] ❌ Venue non trovato: '{venue_name}'")
            return

        years_found = [y for y, _ in matches]
        most_recent_year, row = max(matches, key=lambda x: x[0])
        print(f"[CORE] ✅ Trovato in {sorted(years_found)} → Rank: {row['Rank']} (Anno: {most_recent_year})")

        if log:
            log_result("CORE", row['Title'], most_recent_year, "Rank", row['Rank'])

    def available_years(self):
        return sorted(self.data_by_year.keys())
