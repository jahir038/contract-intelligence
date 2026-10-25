from pathlib import Path

import pandas as pd
import requests

DATA_URL = (
    "https://huggingface.co/datasets/theatticusproject/cuad/"
    "resolve/main/CUAD_v1/master_clauses.csv"
)

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

csv_path = DATA_DIR / "master_clauses.csv"

if not csv_path.exists():
    print("Downloading CUAD master clauses CSV...")

    response = requests.get(DATA_URL, timeout=60)
    response.raise_for_status()

    csv_path.write_bytes(response.content)
    print(f"Saved to: {csv_path}")

print("\nLoading CSV...")
df = pd.read_csv(csv_path)


# Inspect all columns related to Governing Law
for column in df.columns:
    if "Governing Law" in column:
        print(f"\nColumn: {column}")
        print("Value:", df.iloc[0][column])


# print("\nFirst contract record:")
# print(df.iloc[0].to_string()[:3000])


# # Inspect the column names related to governing law
# print("\nColumns containing 'Governing Law':")

# for column in df.columns:
#     if "Governing Law" in column:
#         print(column)

# # Display the first contract's values for these columns
# print("\nGoverning Law fields for the first contract:")

# for column in df.columns:
#     if "Effective Date" in column:
#         print(f"\n{column}:")
#         print(df.iloc[0][column])

