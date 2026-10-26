# src/check_osm_water.py
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

lines = gpd.read_file("data/raw/osm_water.gpkg", layer="lines")
polys = gpd.read_file("data/raw/osm_water.gpkg", layer="polygons")

targets = ["한강", "중랑천", "안양천", "탄천", "청계천", "양재천",
           "홍제천", "불광천", "정릉천", "성내천", "도림천"]
for t in targets:
    nl = lines["name"].fillna("").str.contains(t).sum()
    npg = polys["name"].fillna("").str.contains(t).sum()
    print(f"{t}: 선 {nl} | 면 {npg}")

print("\n이름 없는 선:", lines["name"].isna().sum(), "/", len(lines))
print("이름 없는 면:", polys["name"].isna().sum(), "/", len(polys))

fig, ax = plt.subplots(figsize=(10, 8))
polys.plot(ax=ax, color="lightblue")
lines.plot(ax=ax, color="steelblue", linewidth=0.8)
ax.set_axis_off()
fig.savefig("data/processed/osm_water_preview.png", dpi=150, bbox_inches="tight")
print("\n저장: data/processed/osm_water_preview.png")