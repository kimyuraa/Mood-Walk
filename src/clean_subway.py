# src/clean_subway.py
# 입력 : data/raw/subway_stations.xlsx
# 출력 : data/processed/subway_seoul_clean.csv
import re
import pandas as pd
import geopandas as gpd
import osmnx as ox

df = pd.read_excel("data/raw/subway_stations.xlsx")
df["lat"] = pd.to_numeric(df["역위도"], errors="coerce")
df["lon"] = pd.to_numeric(df["역경도"], errors="coerce")
df = df.dropna(subset=["lat", "lon"])

# 1) 좌표 오류로 보이는 행 제외 (역사명, 노선명)
BAD = [("마곡", "5호선"), ("이촌(국립중앙박물관)", "4호선")]
df = df[[(n, l) not in BAD for n, l in zip(df["역사명"], df["노선명"])]].copy()

# 2) 같은 역의 이름 통일
ALIAS = {"총신대입구(이수)": "이수", "이촌역": "이촌"}

def norm1(n):
    n = ALIAS.get(n, n)
    return re.sub(r"\(.*?\)", "", n).strip()

df["name_norm"] = df["역사명"].map(norm1)
names = set(df["name_norm"])
# '지축역' -> '지축' (같은 이름의 역이 따로 있을 때만 '역'을 뗀다. '서울역'은 그대로)
KEEP_SEPARATE = {"신촌역"}   # 2호선 신촌과 경의중앙선 신촌역은 700m 떨어진 별개 역
df["name_norm"] = df["name_norm"].map(
    lambda n: n[:-1] if n.endswith("역") and n[:-1] in names and n not in KEEP_SEPARATE else n
)

# 3) 서울 경계 + 1km 안만 남기기
pts = gpd.GeoDataFrame(
    df, geometry=gpd.points_from_xy(df.lon, df.lat), crs=4326
).to_crs(5179)
boundary = ox.geocode_to_gdf("Seoul, South Korea").to_crs(5179)
seoul_poly = boundary.geometry.iloc[0]
pts["in_seoul"] = pts.geometry.within(seoul_poly)
pts = pts[pts.geometry.within(seoul_poly.buffer(1000))].copy()
print("행(역x노선):", len(pts), "| 서울 경계 안:", int(pts["in_seoul"].sum()))

# 4) 역 이름 기준으로 합치기
out = pts.groupby("name_norm").agg(
    lat=("lat", "mean"),
    lon=("lon", "mean"),
    n_lines=("노선명", "nunique"),
    raw_names=("역사명", lambda s: ",".join(sorted(set(s)))),
    in_seoul=("in_seoul", "max"),
).reset_index().rename(columns={"name_norm": "station_name"})

out.to_csv("data/processed/subway_seoul_clean.csv", index=False, encoding="utf-8-sig")
print(f"{len(pts)}행 -> {len(out)}개 역 (서울 안: {int(out.in_seoul.sum())}) 저장 완료")

# 5) 250m 안에 남은 역 쌍 확인
g = gpd.GeoDataFrame(out, geometry=gpd.points_from_xy(out.lon, out.lat), crs=4326).to_crs(5179)
left = []
for i in range(len(g)):
    for j in range(i + 1, len(g)):
        d = g.geometry.iloc[i].distance(g.geometry.iloc[j])
        if d < 250:
            left.append((g.station_name.iloc[i], g.station_name.iloc[j], round(d)))
print("\n250m 안에 남은 역 쌍:", len(left))
for a, b, d in sorted(left, key=lambda x: x[2]):
    print(f"{a} | {b} | {d}m")