import pandas as pd
import json

# Load the diagnostics results (make sure the file exists)
csv_path = "team_search_diagnostics.csv"  # Adjust if saved elsewhere
df = pd.read_csv(csv_path)

# Keep only the top-ranked result for each search term
top_results = df[df["result_rank"] == 1]

# Build the mapping dictionary
mapping = {
    "_comment": "Manual mappings for teams that can't be found via exact search",
    "_usage": "Format: 'Input Name': {'api_id': ..., 'api_name': ..., 'country': ...}"
}

for _, row in top_results.iterrows():
    mapping[row["search_term"]] = {
        "api_id": int(row["team_id"]),
        "api_name": row["team_name"],
        "country": row["country"]
    }

# Save as JSON
with open("manual_team_mappings.json", "w", encoding="utf-8") as f:
    json.dump(mapping, f, indent=2)

print("Generated manual_team_mappings.json successfully.")
