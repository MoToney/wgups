import pandas as pd
from geopy.geocoders import Nominatim
from time import sleep

# Load your CSV data
df = pd.read_csv("../../data/packages.csv")

# Build full address strings
df["FullAddress"] = df["Address"] + ", " + df["City"] + ", " + df["State"] + " " + df["Zip"].astype(str)

# Initialize geocoder (with custom user_agent per Nominatim policy)
geolocator = Nominatim(user_agent="wgups-routing-batch")

# Functions to geocode with some rate limiting to avoid bans
def geocode_address(address):
    try:
        location = geolocator.geocode(address, timeout=10)
        if location:
            return location.latitude, location.longitude
        return None, None
    except Exception:
        return None, None

# Apply to your DataFrame
latitudes = []
longitudes = []

for address in df["FullAddress"]:
    lat, lon = geocode_address(address)
    latitudes.append(lat)
    longitudes.append(lon)
    sleep(1)  # Nominatim requests 1-second delay per their usage policy!

df["Latitude"] = latitudes
df["Longitude"] = longitudes

# Save to new CSV for easy reuse in Streamlit/etc.
df.to_csv("packages_with_coords.csv", index=False)

print("Done! Coordinates added.")