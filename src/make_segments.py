# src/make_segments.py
# 입력 : data/raw/seoul_trail/course_1.gpx ~ course_8.gpx
# 출력 : data/processed/segments.csv   (구간별 속성, 위경도)
#        data/processed/segments.gpkg  (구간 선 도형, EPSG:5179)
import glob
import os
import re
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd
import geopandas as gpd
from pyproj import Transformer
from shapely.geometry import LineString, Point
from shapely.ops import substring

SEG_LEN = 500        # 목표 구간 길이(m). 임시 기준
POI_MAX_DIST = 50    # 코스에서 이 거리(m)보다 먼 웨이포인트는 제외. 임시 기준
SMOOTH_WIN = 5       # 고도 이동평균 창(점 개수). 임시 기준

# 웨이포인트 이름 -> 컬럼. 이름이 달라도 같은 종류로 묶은 것은 내 판단(임시)
NAME_TO_COL = {
    "갈림길": "poi_fork",
    "쉼터": "poi_rest", "둘레길 쉼터": "poi_rest",
    "화장실": "poi_toilet",
    "벤치": "poi_bench",
    "정자": "poi_pavilion",
    "음수대": "poi_water", "약수터": "poi_water",
    "이정표": "poi_signpost",
    "횡단보도": "poi_crosswalk",
    "둘레길 방향 정보": "poi_direction",
    "둘레길 단풍": "poi_maple",
    "둘레길 전망": "poi_view", "조망점": "poi_view",
}
COLS = list(dict.fromkeys(NAME_TO_COL.values()))
AMENITY = ["poi_rest", "poi_toilet", "poi_bench", "poi_pavilion", "poi_water"]

to_5179 = Transformer.from_crs(4326, 5179, always_xy=True)
to_4326 = Transformer.from_crs(5179, 4326, always_xy=True)


def tag(el):
    return el.tag.split("}")[-1]


def read_gpx(path):
    root = ET.parse(path).getroot()
    trk, wpt = [], []
    for el in root.iter():
        t = tag(el)
        if t == "trkpt":
            ele = next((c.text for c in el if tag(c) == "ele"), None)
            trk.append((float(el.get("lat")), float(el.get("lon")),
                        float(ele) if ele else np.nan))
        elif t == "wpt":
            name = next((c.text for c in el if tag(c) == "name"), None)
            wpt.append((name, float(el.get("lat")), float(el.get("lon"))))
    return (pd.DataFrame(trk, columns=["lat", "lon", "ele"]),
            pd.DataFrame(wpt, columns=["name", "lat", "lon"]))


rows, geoms = [], []
unmatched_names = {}
files = sorted(glob.glob("data/raw/seoul_trail/course_*.gpx"),
               key=lambda p: int(re.search(r"course_(\d+)", p).group(1)))

for path in files:
    course = int(re.search(r"course_(\d+)", path).group(1))
    trk, wpt = read_gpx(path)

    x, y = to_5179.transform(trk["lon"].values, trk["lat"].values)
    line = LineString(list(zip(x, y)))
    step = np.hypot(np.diff(x), np.diff(y))
    cum = np.concatenate([[0], np.cumsum(step)])
    total = cum[-1]

    n = max(1, int(round(total / SEG_LEN)))
    bounds = np.linspace(0, total, n + 1)
    seg_len = total / n

    ele_s = trk["ele"].rolling(SMOOTH_WIN, center=True, min_periods=1).mean().values
    seg_of_pt = np.clip(np.searchsorted(bounds, cum, side="right") - 1, 0, n - 1)

    # 웨이포인트를 구간에 배정
    counts = np.zeros((n, len(COLS)), dtype=int)
    other = np.zeros(n, dtype=int)
    far = 0
    wx, wy = to_5179.transform(wpt["lon"].values, wpt["lat"].values)
    for (name, _, _), px, py in zip(wpt.itertuples(index=False), wx, wy):
        p = Point(px, py)
        if line.distance(p) > POI_MAX_DIST:
            far += 1
            continue
        i = int(min(line.project(p) // seg_len, n - 1))
        key = (name or "").strip()
        if key in NAME_TO_COL:
            counts[i, COLS.index(NAME_TO_COL[key])] += 1
        else:
            other[i] += 1
            unmatched_names[key] = unmatched_names.get(key, 0) + 1

    for i in range(n):
        m = seg_of_pt == i
        e = ele_s[m]
        d = np.diff(e) if len(e) > 1 else np.array([0.0])
        gain, loss = abs(d[d > 0].sum()), abs(d[d < 0].sum())
        g = substring(line, bounds[i], bounds[i + 1])
        c = g.interpolate(0.5, normalized=True)
        clon, clat = to_4326.transform(c.x, c.y)
        row = {
            "seg_id": f"c{course}_{i:03d}",
            "course": course,
            "seg_idx": i,
            "start_m": round(bounds[i]),
            "length_m": round(seg_len, 1),
            "ele_gain_m": round(gain, 1),
            "ele_loss_m": round(loss, 1),
            "ele_min_m": round(np.nanmin(e), 1) if len(e) else np.nan,
            "ele_max_m": round(np.nanmax(e), 1) if len(e) else np.nan,
            "avg_abs_grade_pct": round((gain + loss) / seg_len * 100, 2),
            "center_lat": round(clat, 6),
            "center_lon": round(clon, 6),
        }
        for col, cnt in zip(COLS, counts[i]):
            row[col] = int(cnt)
        row["poi_other"] = int(other[i])
        row["poi_amenity"] = int(sum(row[c_] for c_ in AMENITY))
        rows.append(row)
        geoms.append(g)

    print(f"코스 {course}: {total/1000:.1f} km -> {n}구간 (구간당 {seg_len:.0f} m)"
          f" | 웨이포인트 {len(wpt)}개 중 코스에서 {POI_MAX_DIST}m 초과 {far}개 제외")

df = pd.DataFrame(rows)
gdf = gpd.GeoDataFrame(df, geometry=geoms, crs=5179)

os.makedirs("data/processed", exist_ok=True)
df.to_csv("data/processed/segments.csv", index=False, encoding="utf-8-sig")
gdf.to_file("data/processed/segments.gpkg", layer="segments", driver="GPKG")

print(f"\n총 {len(df)}구간 저장 완료")
print("\n== 구간별 요약 ==")
print(df[["length_m", "ele_gain_m", "ele_loss_m", "avg_abs_grade_pct",
          "poi_amenity", "poi_fork"]].describe().round(1).to_string())
print("\n편의시설이 0개인 구간:", int((df.poi_amenity == 0).sum()), "/", len(df))
print("\n분류에 안 들어간 웨이포인트 이름 상위 10:")
print(pd.Series(unmatched_names).sort_values(ascending=False).head(10).to_string())