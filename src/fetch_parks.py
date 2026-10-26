# src/fetch_parks.py
import os, time
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv(override=True)
KEY = os.environ["DATA_GO_KR_KEY"]      # Encoding 키 그대로
URL = "https://api.data.go.kr/openapi/tn_pubr_public_cty_park_info_api"

PER_PAGE = 1000
rows, page = [], 1
while True:
    try:
        r = requests.get(
            f"{URL}?serviceKey={KEY}&pageNo={page}&numOfRows={PER_PAGE}&type=json",
            timeout=60,
        )
        body = r.json()["body"]
    except Exception as e:
        print("실패:", str(e).replace(KEY, "***KEY***")[:300])
        print(r.text[:300].replace(KEY, "***KEY***"))
        break

    items = body["items"]["item"] if body.get("items") else []
    if isinstance(items, dict):
        items = [items]
    if not items:
        break

    rows += items
    total = int(body["totalCount"])
    print(f"page {page}: {len(rows)} / {total}")
    if len(rows) >= total:
        break
    page += 1
    time.sleep(0.3)

df = pd.DataFrame(rows)

# 서울 필터: 주소나 관리기관이 '서울'로 시작하는 것만
# ('서울대공원'처럼 이름에만 서울이 들어간 경기도 공원은 걸러냄)
is_seoul = (
    df["rdnmadr"].str.startswith("서울", na=False)
    | df["lnmadr"].str.startswith("서울", na=False)
    | df["insttNm"].str.startswith("서울", na=False)
)
seoul = df[is_seoul].copy()

for c in ["latitude", "longitude", "parkAr"]:
    seoul[c] = pd.to_numeric(seoul[c], errors="coerce")

seoul.to_csv("data/raw/parks_seoul.csv", index=False, encoding="utf-8-sig")
print("전국", len(df), "건 -> 서울", len(seoul), "건")
print(seoul[["parkNm", "parkSe", "latitude", "longitude", "parkAr"]].head())
print("좌표 없는 행:", seoul["latitude"].isna().sum())