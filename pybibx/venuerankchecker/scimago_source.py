from .base import BaseSource
from .utils import fuzzy_match
from .decorators import log_call
import pandas as pd
import os

class ScimagoSource(BaseSource):
    @log_call
    def check(self, venue_name, log=True, results_dir=r"C:\Users\maria\Desktop\ReplicableSLR\pybibx\VenueRank-Results"):
        # 🔹 Normalize name
        name_only = venue_name.split(",")[0].strip().lower()
        input_year = None
        if "," in venue_name:
            try:
                input_year = int(venue_name.split(",")[-1])
            except:
                pass

        best_title = None

        # 🔹 Step 1: check input year if available
        if input_year in self.data_by_year:
            df_check = self.data_by_year[input_year].copy()
            df_check['Title'] = df_check['Title'].str.strip().str.lower()
            titles_list = df_check['Title'].tolist()
            if name_only in titles_list:
                best_title = name_only
            else:
                best_title = fuzzy_match(name_only, titles_list)

        # 🔹 Step 2: if not found, global fuzzy match across all years
        if not best_title:
            all_titles = []
            for df in self.data_by_year.values():
                all_titles += df['Title'].str.strip().str.lower().tolist()
            best_title = fuzzy_match(name_only, all_titles)

        if not best_title:
            print(f"[SCIMAGO] ❌ Venue not found: '{venue_name}'")
            return

        # 🔹 Step 3: find the most recent record
        matches = []
        for y, df in sorted(self.data_by_year.items(), reverse=True):
            df_copy = df.copy()
            df_copy['Title'] = df_copy['Title'].str.strip().str.lower()
            match = df_copy[df_copy['Title'] == best_title]
            if not match.empty:
                matches.append((y, match))

        if not matches:
            print(f"[SCIMAGO] ❌ No record found for '{best_title}'")
            return

        most_recent_year, df_match = max(matches, key=lambda x: x[0])
        row = df_match.iloc[0]

        categories = str(row.get('Categories', '')).split(';')
        areas = str(row.get('Areas', '')).split(';')

        print(f"[SCIMAGO] ✅ Found → Most recent year: {most_recent_year}")
        print("   📂 Categories:")

        results = []
        for i, cat in enumerate(categories):
            cat = cat.strip()
            area = areas[i].strip() if i < len(areas) else "N/A"

            if cat:
                quartile = "N/A"
                if '(' in cat and ')' in cat:
                    quartile = cat.split('(')[-1].replace(')', '').strip()
                    cat_name = cat.split('(')[0].strip()
                else:
                    cat_name = cat

                print(f"      - {area} > {cat_name} - {quartile}")

                results.append({
                    "Source": "SCIMAGO",
                    "ID": row.get("ID", "N/A"),
                    "Venue": row["Title"],
                    "Year": most_recent_year,
                    "Category": cat_name,
                    "Area": area,
                    "Quartile": quartile
                })

        # 🔹 Step 4: Save cumulative CSV
        if log:
            os.makedirs(results_dir, exist_ok=True)
            csv_path = os.path.join(results_dir, "SCIMAGO-results.csv")
            new_df = pd.DataFrame(results)
            if os.path.exists(csv_path):
                old_df = pd.read_csv(csv_path)
                df_final = pd.concat([old_df, new_df], ignore_index=True)
            else:
                df_final = new_df
            df_final.to_csv(csv_path, index=False)
            print(f"\n💾 Results appended to: {csv_path}")

    def available_years(self):
        """Returns the list of available years in SCIMAGO data."""
        return sorted(self.data_by_year.keys())
