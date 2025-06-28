import pandas as pd

df = pd.read_csv("packages_with_coords_merged.csv")
cols = list(df.columns)
zip_index = cols.index('Zip')
for c in ['Latitude', 'Longitude']:
    cols.remove(c)
cols = cols[:zip_index+1] + ['Latitude', 'Longitude'] + cols[zip_index+1:]
df[cols].to_csv("packages.csv", index=False)