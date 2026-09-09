# ============================================================
# COIMBATORE PUBLIC AMENITIES
# Mapping and Accessibility Analysis
# ============================================================

import osmnx as ox
import geopandas as gpd
import pandas as pd
import numpy as np
import folium
import time
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union
from branca.colormap import LinearColormap
import warnings

warnings.filterwarnings("ignore")

# ------------------------------------------------------------
# 1. SETTINGS
# ------------------------------------------------------------

PLACE = "Coimbatore, Tamil Nadu, India"

# Accessibility radius in metres
ACCESS_RADIUS = 1000

# Grid size in metres
GRID_SIZE = 500

# ------------------------------------------------------------
# 2. GET COIMBATORE CITY BOUNDARY
# ------------------------------------------------------------

print("Downloading Coimbatore boundary...")

boundary = ox.geocode_to_gdf(PLACE)

# Convert to a projected CRS for metre-based calculations
boundary_proj = boundary.to_crs(epsg=32643)

city_polygon = boundary_proj.geometry.iloc[0]

# Map centre
center_lat = boundary.geometry.centroid.iloc[0].y
center_lon = boundary.geometry.centroid.iloc[0].x

print("Boundary downloaded.")

# ------------------------------------------------------------
# 3. DOWNLOAD AMENITIES FROM OPENSTREETMAP
# ------------------------------------------------------------

amenity_tags = {
    "Hospitals": {"amenity": ["hospital"]},
    "Schools & Colleges": {"amenity": ["school", "college", "university"]},
    "Police Stations": {"amenity": ["police"]},
    "Bus Stops": {"highway": ["bus_stop"]},
    "ATMs & Banks": {"amenity": ["atm", "bank"]},
    "Public Toilets": {"amenity": ["toilets"]},
    "Parks": {"leisure": ["park"]},
    "Markets": {"amenity": ["marketplace"]}
}

amenities = {}

for category, tags in amenity_tags.items():
    print(f"Downloading {category}...")
    success = False
    retries = 3
    for i in range(retries):
        try:
            gdf = ox.features_from_polygon(boundary.geometry.iloc[0], tags)
            if not gdf.empty:
                gdf = gdf[gdf.geometry.notna()].copy()
                gdf = gdf.to_crs(epsg=32643)
                gdf["geometry"] = gdf.geometry.representative_point()
                gdf = gdf.drop_duplicates(subset=["geometry"])
                amenities[category] = gdf
                print(f"   Found {len(gdf)} locations")
            else:
                amenities[category] = gpd.GeoDataFrame(geometry=[], crs="EPSG:32643")
                print(f"   Found 0 locations")
            success = True
            break
        except Exception as e:
            print(f"   Attempt {i+1} failed: {e}")
            time.sleep(2 ** i) # Exponential backoff
    
    if not success:
        print(f"   Final failure for {category}. Skipping.")
        amenities[category] = gpd.GeoDataFrame(geometry=[], crs="EPSG:32643")

# ------------------------------------------------------------
# 4. CREATE ACCESSIBILITY GRID
# ------------------------------------------------------------

print("\nCreating accessibility grid...")
minx, miny, maxx, maxy = city_polygon.bounds
cells = []
x = minx
while x < maxx:
    y = miny
    while y < maxy:
        cell = Polygon([(x, y), (x + GRID_SIZE, y), (x + GRID_SIZE, y + GRID_SIZE), (x, y + GRID_SIZE)])
        if cell.intersects(city_polygon):
            clipped = cell.intersection(city_polygon)
            if not clipped.is_empty:
                cells.append(clipped)
        y += GRID_SIZE
    x += GRID_SIZE

grid = gpd.GeoDataFrame({"geometry": cells}, crs="EPSG:32643")

# ------------------------------------------------------------
# 5. CALCULATE ACCESSIBILITY SCORE
# ------------------------------------------------------------

essential_categories = ["Hospitals", "Schools & Colleges", "Police Stations", "Bus Stops"]
service_areas = {}
for category in essential_categories:
    gdf = amenities[category]
    if len(gdf) > 0:
        buffers = gdf.geometry.buffer(ACCESS_RADIUS)
        service_areas[category] = unary_union(buffers)
    else:
        service_areas[category] = None

grid["centroid"] = grid.geometry.centroid
grid["Accessibility Score"] = 0
for category in essential_categories:
    service = service_areas[category]
    if service is not None:
        grid.loc[grid["centroid"].apply(service.contains), "Accessibility Score"] += 1

# ------------------------------------------------------------
# 6. CLASSIFY ACCESSIBILITY
# ------------------------------------------------------------

def classify(score):
    if score == 0: return "Very Poor"
    elif score == 1: return "Poor"
    elif score == 2: return "Moderate"
    elif score == 3: return "Good"
    else: return "Very Good"

grid["Accessibility"] = grid["Accessibility Score"].apply(classify)
print("Accessibility analysis completed.")

# ------------------------------------------------------------
# 7. CREATE FOLIUM MAP
# ------------------------------------------------------------

m = folium.Map(location=[center_lat, center_lon], zoom_start=11, tiles="CartoDB positron")

score_colors = {0: "#d73027", 1: "#fc8d59", 2: "#fee08b", 3: "#91cf60", 4: "#1a9850"}

for _, row in grid.iterrows():
    score = int(row["Accessibility Score"])
    geom_wgs84 = gpd.GeoSeries([row.geometry], crs="EPSG:32643").to_crs(epsg=4326).iloc[0]
    feature_geojson = {
        "type": "Feature",
        "geometry": geom_wgs84.__geo_interface__,
        "properties": {"score": score, "accessibility": row["Accessibility"]}
    }
    folium.GeoJson(
        feature_geojson,
        style_function=lambda feature: {
            "fillColor": score_colors[feature["properties"]["score"]],
            "color": "white", "weight": 0.3, "fillOpacity": 0.45
        },
        tooltip=folium.GeoJsonTooltip(fields=["accessibility"], aliases=["Accessibility"], labels=True)
    ).add_to(m)

for category, gdf in amenities.items():
    layer = folium.FeatureGroup(name=category)
    color = {"Hospitals":"red", "Schools & Colleges":"blue", "Police Stations":"black", "Bus Stops":"orange", "ATMs & Banks":"purple", "Public Toilets":"darkgreen", "Parks":"green", "Markets":"cadetblue"}[category]
    icon = {"Hospitals":"plus-square", "Schools & Colleges":"graduation-cap", "Police Stations":"shield", "Bus Stops":"bus", "ATMs & Banks":"money-bill", "Public Toilets":"restroom", "Parks":"tree", "Markets":"shopping-cart"}[category]
    for _, row in gdf.head(1000).iterrows():
        p = gpd.GeoSeries([row.geometry], crs="EPSG:32643").to_crs(epsg=4326).iloc[0]
        folium.Marker(location=[p.y, p.x], tooltip=str(row.get("name", category)), icon=folium.Icon(color=color, icon=icon, prefix="fa")).add_to(layer)
    layer.add_to(m)

folium.LayerControl(collapsed=False).add_to(m)
m.save("coimbatore_public_amenities_map.html")
print("\nMAP CREATED SUCCESSFULLY: coimbatore_public_amenities_map.html")