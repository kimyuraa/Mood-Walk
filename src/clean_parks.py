# src/clean_parks.py
import pandas as pd

df = pd.read_csv("data/raw/parks_seoul.csv")

print("== 면적 상위 10개 ==")
print(df.nlargest(10, "parkAr")[["parkNm", "parkSe", "parkAr", "lnmadr"]].to_string())

bad = (
    (df.latitude > 37.72) | (df.latitude < 37.41)
    | (df.longitude < 126.76) | (df.longitude > 127.19)
)
print("\n제거할 행:", bad.sum())
clean = df[~bad].copy()

clean["park_id"] = clean["manageNo"] + "_" + clean["parkNm"]
print("park_id 중복:", clean["park_id"].duplicated().sum())

clean.to_csv("data/processed/parks_seoul_clean.csv", index=False, encoding="utf-8-sig")
print(f"\n{len(df)} -> {len(clean)} 건 저장 완료")