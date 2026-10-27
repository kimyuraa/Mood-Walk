# src/check_osm_water_stats.py
import geopandas as gpd

lines = gpd.read_file("data/raw/osm_water.gpkg", layer="lines").to_crs(5179)
polys = gpd.read_file("data/raw/osm_water.gpkg", layer="polygons").to_crs(5179)

lines["len_km"] = lines.length / 1000
polys["area_ha"] = polys.area / 10000

targets = ["한강", "중랑천", "안양천", "탄천", "청계천", "양재천",
           "홍제천", "불광천", "정릉천", "성내천", "도림천"]
print("== 하천별 선 길이 합(km) / 면 면적 합(ha) ==")
for t in targets:
    l = lines[lines["name"].fillna("").str.contains(t)]["len_km"].sum()
    a = polys[polys["name"].fillna("").str.contains(t)]["area_ha"].sum()
    print(f"{t}: {l:.1f} km | {a:.1f} ha")

print("\n== 면 면적 분포(ha) ==")
print(polys["area_ha"].describe())
print("면적 1ha 미만 면:", (polys["area_ha"] < 1).sum(), "/", len(polys))

for col in ["natural", "water"]:
    if col in polys.columns:
        print(f"\n면 {col} 태그:")
        print(polys[col].value_counts(dropna=False).head(10))
if "waterway" in lines.columns:
    print("\n선 waterway 태그:")
    print(lines["waterway"].value_counts(dropna=False))

print("\n이름 없는 면의 면적 중앙값(ha):", polys[polys["name"].isna()]["area_ha"].median())