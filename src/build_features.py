# src/build_features.py
# 입력 : data/processed/segments.gpkg            (make_segments.py)
#        data/processed/osm_water_clean.gpkg     (clean_osm_water.py)
#        data/processed/parks_seoul_clean.csv    (clean_parks.py)
#        data/processed/subway_seoul_clean.csv   (clean_subway.py)
#        data/raw/ddareungi_stations.xlsx
# 출력 : data/processed/segment_features.csv / segment_features.gpkg
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.ops import unary_union

WATER_NEAR_M = 100     # 물가로 보는 거리(m). 임시 기준
PARK_BUFFER_M = 300    # 코스 양옆으로 공원을 찾는 폭(m). 임시 기준
BIG_PARK_M2 = 10000    # '큰 공원' 기준 면적(㎡). 임시 기준
STATION_R_M = 500      # 지하철역 반경(m). 임시 기준
BIKE_R_M = 500         # 따릉이 대여소 반경(m). 임시 기준


def to_points(df, lat, lon):
    return gpd.GeoDataFrame(
        df, geometry=gpd.points_from_xy(df[lon], df[lat]), crs=4326
    ).to_crs(5179)


seg = gpd.read_file("data/processed/segments.gpkg", layer="segments").to_crs(5179)
print("구간:", len(seg))

# 1) 물가: 가장 가까운 물까지 거리, 100m 안에 있는 구간 비율
wl = gpd.read_file("data/processed/osm_water_clean.gpkg", layer="lines")
wp = gpd.read_file("data/processed/osm_water_clean.gpkg", layer="polygons")
water = unary_union(list(wl.geometry) + list(wp.geometry))
water_near = water.buffer(WATER_NEAR_M)
seg["water_dist_m"] = seg.geometry.distance(water).round(0)
seg["water_frac_100m"] = [
    round(g.intersection(water_near).length / g.length, 3) for g in seg.geometry
]

# 2) 공원: 코스 300m 안 공원 개수, 큰 공원 녹지 비율
parks = pd.read_csv("data/processed/parks_seoul_clean.csv")
parks = parks.dropna(subset=["latitude", "longitude", "parkAr"])
pg = to_points(parks, "latitude", "longitude")
buf = seg.geometry.buffer(PARK_BUFFER_M)

seg["park_cnt_300m"] = [int(len(pg.sindex.query(b, predicate="intersects"))) for b in buf]

# 큰 공원은 면적이 같은 원으로 근사해서 코스 주변 면적과 겹치는 비율을 계산.
# (공원이 점 데이터라서 큰 산이 코스에서 멀게 찍힐 수 있어서 쓰는 임시 방법)
big = pg[pg["parkAr"] >= BIG_PARK_M2]
circles = [p.buffer(float(np.sqrt(a / np.pi))) for p, a in zip(big.geometry, big["parkAr"])]
green = unary_union(circles)
seg["green_ratio_300m"] = [round(min(1.0, b.intersection(green).area / b.area), 3) for b in buf]

# 3) 지하철역
st = to_points(pd.read_csv("data/processed/subway_seoul_clean.csv"), "lat", "lon")
seg["subway_dist_m"] = [round(st.geometry.distance(g).min()) for g in seg.geometry]
seg["subway_cnt_500m"] = [int((st.geometry.distance(g) <= STATION_R_M).sum()) for g in seg.geometry]

# 4) 따릉이 대여소 (엑셀 위 5줄은 제목)
bike = pd.read_excel("data/raw/ddareungi_stations.xlsx", header=None, skiprows=5)
assert bike.shape[1] == 10, f"컬럼 수가 달라요: {bike.shape[1]}"
bike.columns = ["station_id", "station_name", "gu", "address", "lat", "lon",
                "installed_at", "lcd_racks", "qr_racks", "mode"]
for c in ["lat", "lon", "lcd_racks", "qr_racks"]:
    bike[c] = pd.to_numeric(bike[c], errors="coerce")
bike = bike.dropna(subset=["lat", "lon"])
bike["racks"] = bike["lcd_racks"].fillna(0) + bike["qr_racks"].fillna(0)
bk = to_points(bike, "lat", "lon")
seg["bike_dist_m"] = [round(bk.geometry.distance(g).min()) for g in seg.geometry]
cnt, racks = [], []
for g in seg.geometry:
    m = bk.geometry.distance(g) <= BIKE_R_M
    cnt.append(int(m.sum()))
    racks.append(int(bk.loc[m, "racks"].sum()))
seg["bike_cnt_500m"] = cnt
seg["bike_racks_500m"] = racks

# 저장
seg.drop(columns="geometry").to_csv(
    "data/processed/segment_features.csv", index=False, encoding="utf-8-sig")
seg.to_file("data/processed/segment_features.gpkg", layer="segments", driver="GPKG")

feat = ["water_dist_m", "water_frac_100m", "park_cnt_300m", "green_ratio_300m",
        "subway_dist_m", "subway_cnt_500m", "bike_dist_m", "bike_cnt_500m"]
print("\n== 새 변수 요약 ==")
print(seg[feat].describe().round(2).to_string())
print("\n== 코스별 평균 ==")
print(seg.groupby("course")[feat].mean().round(2).to_string())
print("\n물가 100m 안에 닿는 구간:", int((seg.water_dist_m <= WATER_NEAR_M).sum()), "/", len(seg))
print("녹지 비율 0인 구간:", int((seg.green_ratio_300m == 0).sum()), "/", len(seg))
print("저장 완료: data/processed/segment_features.csv")