# src/check_subway_pairs.py
import pandas as pd
import geopandas as gpd

df = pd.read_csv("data/processed/subway_seoul_clean.csv")
g = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.lon, df.lat), crs=4326).to_crs(5179)

pairs = []
for i in range(len(g)):
    for j in range(i + 1, len(g)):
        d = g.geometry.iloc[i].distance(g.geometry.iloc[j])
        if d < 250:
            pairs.append((g.station_name.iloc[i], g.station_name.iloc[j], round(d)))

print(f"250m 안의 역 쌍: {len(pairs)}")
for a, b, d in sorted(pairs, key=lambda x: x[2]):
    print(f"{a} | {b} | {d}m")