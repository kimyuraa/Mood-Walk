# src/clean_subway.py
# 입력 : data/raw/subway_stations.xlsx
# 출력 : data/processed/subway_seoul_clean.csv
import pandas as pd
import geopandas as gpd
import osmnx as ox

df = pd.read_excel("data/raw/subway_stations.xlsx")
df["lat"] = pd.to_numeric(df["역위도"], errors="coerce")
df["lon"] = pd.to_numeric(df["역경도"], errors="coerce")
df = df.dropna(subset=["lat", "lon"])

pts = gpd.GeoDataFrame(
    df, geometry=gpd.points_from_xy(df.lon, df.lat), crs=4326
).to_crs(5179)

# 서울 경계 (하천 정제와 같은 방식, 경계 밖 1km까지 포함)
boundary = ox.geocode_to_gdf("Seoul, South Korea").to_crs(5179)
seoul_poly = boundary.geometry.iloc[0]
near_poly = seoul_poly.buffer(1000)

pts["in_seoul"] = pts.geometry.within(seoul_poly)
pts = pts[pts.geometry.within(near_poly)].copy()
print("행(역x노선):", len(pts), "| 서울 경계 안:", int(pts["in_seoul"].sum()))

# 주소는 서울인데 걸러진 행 = 좌표 오류 의심
bad = df[df["역사도로명주소"].fillna("").str.startswith("서울")]
bad = bad[~bad["역사명"].isin(pts["역사명"])]
print("\n주소는 서울인데 걸러진 행:")
print(bad[["역사명", "노선명", "역사도로명주소", "lat", "lon"]].to_string())

# 환승역은 노선마다 한 줄이라서 역 이름 기준으로 합치기
pts["x"] = pts.geometry.x
pts["y"] = pts.geometry.y
agg = pts.groupby("역사명").agg(
    lat=("lat", "mean"),
    lon=("lon", "mean"),
    n_lines=("노선명", "nunique"),
    lines=("노선명", lambda s: ",".join(sorted(set(s)))),
    in_seoul=("in_seoul", "max"),
    sx=("x", lambda s: s.max() - s.min()),
    sy=("y", lambda s: s.max() - s.min()),
).reset_index()
agg["spread_m"] = (agg.sx ** 2 + agg.sy ** 2) ** 0.5

print("\n같은 이름인데 좌표가 300m 넘게 벌어진 역 (다른 역일 수 있음):")
print(agg[agg.spread_m > 300][["역사명", "lines", "spread_m"]].to_string())

out = agg.rename(columns={"역사명": "station_name"})[
    ["station_name", "lat", "lon", "n_lines", "lines", "in_seoul"]
]
out.to_csv("data/processed/subway_seoul_clean.csv", index=False, encoding="utf-8-sig")
print(f"\n{len(pts)}행 -> {len(out)}개 역 (서울 안: {int(out.in_seoul.sum())}) 저장 완료")