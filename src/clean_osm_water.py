# src/clean_osm_water.py
# 입력 : data/raw/osm_water.gpkg
# 출력 : data/processed/osm_water_clean.gpkg (EPSG:5179, 미터 단위)
import geopandas as gpd
import osmnx as ox

lines = gpd.read_file("data/raw/osm_water.gpkg", layer="lines").to_crs(5179)
polys = gpd.read_file("data/raw/osm_water.gpkg", layer="polygons").to_crs(5179)

# 1) 면 필터: 하수/수영장/분수 등 제외 + 1ha 미만 제외 (임시 기준)
#    자르기 전의 원래 면적으로 판단해야 경계에서 잘린 큰 하천이 빠지지 않아
polys["area_ha"] = polys.area / 10000
drop_types = ["wastewater", "pool", "basin", "fountain"]
polys = polys[(~polys["water"].isin(drop_types)) & (polys["area_ha"] >= 1)]

# 2) 서울 경계로 자르기 (가장자리 코스를 위해 1km 여유, 임시 기준)
boundary = ox.geocode_to_gdf("Seoul, South Korea").to_crs(5179)
area = gpd.GeoDataFrame(geometry=boundary.buffer(1000), crs=5179)
lines = gpd.clip(lines, area)
polys = gpd.clip(polys, area)
print("선:", len(lines), "| 면:", len(polys))

# 3) 자른 뒤 길이 확인
lines["len_km"] = lines.length / 1000
print("\n== 하천별 선 길이 합(km), 서울 경계 + 1km 안 ==")
for t in ["한강", "중랑천", "안양천", "탄천", "청계천", "양재천",
          "홍제천", "불광천", "정릉천", "성내천", "도림천"]:
    s = lines[lines["name"].fillna("").str.contains(t)]["len_km"].sum()
    print(f"{t}: {s:.1f} km")

print("\n이름 없는 면(water 태그 None 등):")
print(polys[polys["water"].isna()][["name", "area_ha"]])

polys.to_file("data/processed/osm_water_clean.gpkg", layer="polygons", driver="GPKG")
lines.to_file("data/processed/osm_water_clean.gpkg", layer="lines", driver="GPKG")
print("\n저장 완료")