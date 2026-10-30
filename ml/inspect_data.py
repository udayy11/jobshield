import pandas as pd
import json

df = pd.read_csv("ml/data/fake_job_postings.csv")
print("Dataset Shape:", df.shape)
print("\nColumns and Types:")
print(df.dtypes)

target_col = None
for col in df.columns:
    if col.lower() in ["fraudulent", "fraud", "label", "target", "is_fake", "class"]:
        target_col = col
        break

if target_col:
    print(f"\nTarget Column: {target_col}")
    print(df[target_col].value_counts(dropna=False))
    print(df[target_col].value_counts(normalize=True, dropna=False) * 100)
else:
    print("\nTarget column not immediately identified among common names. Columns are:", df.columns.tolist())

print("\nMissing Values:")
print(df.isnull().sum())

print("\nFirst 2 Rows:")
print(df.head(2).to_dict(orient="records"))
