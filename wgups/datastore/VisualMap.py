import streamlit as st
import folium
from streamlit_folium import st_folium

import pandas as pd

df = pd.read_csv("../dataloader/packages_with_coords.csv")
df = df.dropna(subset=["Latitude", "Longitude"])

map_center = [df['Latitude'].mean(), df['Longitude'].mean()]
m = folium.Map(location=map_center, zoom_start=12)

# Draw route as PolyLine (optional)
coords = list(zip(df['Latitude'], df['Longitude']))
folium.PolyLine(coords, color="blue", weight=2.5, opacity=1).add_to(m)

for idx, row in df.iterrows():
    folium.Marker(
        location=[row['Latitude'], row['Longitude']],
        popup=f"Package ID: {row['Package ID']}<br>{row['FullAddress']}",
        tooltip=row['FullAddress']
    ).add_to(m)


st.subheader("Package Data Table")
st.dataframe(df)

package_ids = df["Package ID"].unique()
selected_ids = st.multiselect("Select Package IDs", package_ids, default=package_ids)

filtered_df = df[df["Package ID"].isin(selected_ids)]

st.title("WGUPS Package Visualization")
st_folium(m, width=800, height=500)



