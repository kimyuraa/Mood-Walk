# src/check_water_types.py
# 물가 100m 안에 닿는 구간이 큰 물 때문인지, 작은 개울 때문인지 확인
import geopandas as gpd
import pandas as pd
from shapely.ops import unary_union

NEAR = 100  # m. build_features.py의 WATER_NEAR_M과 같은 값

seg = gpd.read_file("data/processed/segments.gpkg", layer="segments").to_crs(5179)
wl = gpd.read_file("data/processed/osm_water_clean.gpkg", layer="lines")
wp = gpd.read_file("data/processed/osm_water_clean.gpkg", layer="polygons")
print("선 태그(waterway):", wl["waterway"].value_counts(dropna=False).to_dict())
print("면 태그(water):", wp["water"].value_counts(dropna=False).to_dict() if "water" in wp else "없음")

cats = {
    "river_line": wl[wl["waterway"] == "river"].geometry,
    "canal_line": wl[wl["waterway"] == "canal"].geometry,
    "stream_line": wl[wl["waterway"] == "stream"].geometry,
    "polygon(1ha+)": wp.geometry,
}
res = pd.DataFrame({"seg_id": seg["seg_id"], "course": seg["course"]})
for k, g in cats.items():
    u = unary_union(list(g)) if len(g) else None
    res[k] = (seg.geometry.distance(u) <= NEAR) if u is not None else False

print(f"\n== {NEAR}m 안에 닿는 구간 수 (전체 {len(seg)}) ==")
print(res[list(cats)].sum().to_string())

big = res["river_line"] | res["canal_line"] | res["polygon(1ha+)"]
only_stream = res["stream_line"] & ~big
print("\n큰 물(강/수로/큰 면)에 닿는 구간:", int(big.sum()))
print("개울에만 닿는 구간:", int(only_stream.sum()))
print("\n== 코스별 (큰 물 / 개울만) ==")
print(pd.DataFrame({"big": big, "only_stream": only_stream, "course": res["course"]})
      .groupby("course").sum().to_string())

# 개울에만 닿는 구간 옆 개울 이름 (이름이 없으면 '이름 없음')
st = wl[wl["waterway"] == "stream"].copy()
st["name"] = st["name"].fillna("이름 없음")
names = {}
for g in seg.geometry[only_stream.values]:
    near = st[st.geometry.distance(g) <= NEAR]
    for n in set(near["name"]):
        names[n] = names.get(n, 0) + 1
print("\n== 개울에만 닿는 구간 옆 개울 이름 상위 10 (구간 수) ==")
print(pd.Series(names).sort_values(ascending=False).head(10).to_string())