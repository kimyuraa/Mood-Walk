# src/fetch_osm_water.py
# 출력: data/raw/osm_water.gpkg (layer: lines, polygons)
import osmnx as ox

ox.settings.cache_folder = "cache"

PLACE = "Seoul, South Korea"
TAGS = {
    "waterway": ["river", "stream", "canal"],
    "natural": "water",
}

gdf = ox.features_from_place(PLACE, tags=TAGS).reset_index()
print("전체 객체:", len(gdf))

keep = [c for c in ["name", "waterway", "natural", "water", "geometry"] if c in gdf.columns]
gdf = gdf[keep]

lines = gdf[gdf.geom_type.isin(["LineString", "MultiLineString"])]
polys = gdf[gdf.geom_type.isin(["Polygon", "MultiPolygon"])]
print("선:", len(lines), "| 면:", len(polys))

lines.to_file("data/raw/osm_water.gpkg", layer="lines", driver="GPKG")
polys.to_file("data/raw/osm_water.gpkg", layer="polygons", driver="GPKG")

print("\n== 이름이 있는 선 상위 15개 ==")
print(lines["name"].value_counts().head(15))
print("\n== 이름이 있는 면 상위 10개 ==")
print(polys["name"].value_counts().head(10))