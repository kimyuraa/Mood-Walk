# src/eda_cluster.py
# 입력 : data/processed/segment_features.csv
# 출력 : data/processed/segment_clusters.csv
#        reports/figures/*.png
import os

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.preprocessing import StandardScaler

K = 4           # 군집 수. 아래 k 탐색 결과를 보고 바꿔도 돼 (임시 기준)
SEED = 42
os.makedirs("reports/figures", exist_ok=True)

df = pd.read_csv("data/processed/segment_features.csv")
df["log_water_big_dist"] = np.log1p(df["water_big_dist_m"])
df["log_stream_dist"] = np.log1p(df["stream_dist_m"])

# 분위기를 가르는 변수(환경)만 군집화에 쓰고, 난이도·편의·접근성은 해석용으로 따로 본다
CLUSTER_FEATS = ["forest_on_trail", "forest_ratio_300m",
                 "water_big_frac_100m", "log_water_big_dist",
                 "stream_frac_100m", "log_stream_dist"]
PROFILE_FEATS = ["forest_on_trail", "forest_ratio_300m",
                 "water_big_frac_100m", "water_big_dist_m",
                 "stream_frac_100m", "stream_dist_m",
                 "ele_gain_m", "avg_abs_grade_pct", "poi_amenity", "poi_view",
                 "subway_dist_m", "bike_dist_m"]

X = StandardScaler().fit_transform(df[CLUSTER_FEATS])
print("구간:", len(df), "| 군집화 변수:", CLUSTER_FEATS)

# 1) 변수 간 상관(스피어만)
corr = df[CLUSTER_FEATS].corr(method="spearman")
print("\n== 스피어만 상관 ==")
print(corr.round(2).to_string())
fig, ax = plt.subplots(figsize=(7, 6))
im = ax.imshow(corr, vmin=-1, vmax=1, cmap="coolwarm")
ax.set_xticks(range(len(CLUSTER_FEATS)))
ax.set_xticklabels(CLUSTER_FEATS, rotation=60, ha="right")
ax.set_yticks(range(len(CLUSTER_FEATS)))
ax.set_yticklabels(CLUSTER_FEATS)
fig.colorbar(im)
fig.savefig("reports/figures/01_corr.png", dpi=150, bbox_inches="tight")
plt.close(fig)

# 2) PCA
pca = PCA().fit(X)
print("\n== PCA 설명 분산 비율 ==")
print(np.round(pca.explained_variance_ratio_, 3))
load = pd.DataFrame(pca.components_[:2].T, index=CLUSTER_FEATS, columns=["PC1", "PC2"])
print("\n== PC1, PC2 적재값 ==")
print(load.round(2).to_string())
Z = pca.transform(X)[:, :2]

# 3) k 탐색
print("\n== k 탐색 (KMeans) ==")
ks, sils, inertias = [], [], []
for k in range(2, 9):
    km = KMeans(n_clusters=k, n_init=20, random_state=SEED).fit(X)
    ks.append(k)
    sils.append(silhouette_score(X, km.labels_))
    inertias.append(km.inertia_)
    print(f"k={k}: silhouette={sils[-1]:.3f} | inertia={inertias[-1]:.1f}")
fig, axs = plt.subplots(1, 2, figsize=(9, 3.5))
axs[0].plot(ks, inertias, marker="o")
axs[0].set_title("inertia")
axs[1].plot(ks, sils, marker="o")
axs[1].set_title("silhouette")
for a in axs:
    a.set_xlabel("k")
fig.savefig("reports/figures/02_k_scan.png", dpi=150, bbox_inches="tight")
plt.close(fig)

# 4) 최종 군집
km = KMeans(n_clusters=K, n_init=20, random_state=SEED).fit(X)
df["cluster"] = km.labels_
print(f"\n== K={K} 군집 프로필 (평균) ==")
prof = df.groupby("cluster")[PROFILE_FEATS].mean().round(2)
prof.insert(0, "n", df.groupby("cluster").size())
print(prof.to_string())

print("\n== 코스 x 군집 (구간 수) ==")
ct = pd.crosstab(df["course"], df["cluster"])
print(ct.to_string())
ct.plot(kind="bar", stacked=True, figsize=(8, 4))
plt.xlabel("course")
plt.ylabel("segments")
plt.savefig("reports/figures/03_course_cluster.png", dpi=150, bbox_inches="tight")
plt.close()

fig, ax = plt.subplots(figsize=(7, 6))
for c in range(K):
    m = df["cluster"] == c
    ax.scatter(Z[m, 0], Z[m, 1], s=18, label=f"C{c}")
ax.set_xlabel("PC1")
ax.set_ylabel("PC2")
ax.legend()
fig.savefig("reports/figures/04_pca_cluster.png", dpi=150, bbox_inches="tight")
plt.close(fig)

# 5) 군집 대표 구간 (중심에 가장 가까운 3개) -> 지도에서 직접 찾아보면 이름 붙이기 쉽다
print("\n== 군집 대표 구간 (좌표를 지도에 찍어보세요) ==")
for c in range(K):
    idx = np.where(df["cluster"] == c)[0]
    d = np.linalg.norm(X[idx] - km.cluster_centers_[c], axis=1)
    for i in idx[np.argsort(d)[:3]]:
        r = df.iloc[i]
        print(f"C{c}: {r.seg_id} (코스 {int(r.course)}) {r.center_lat:.5f}, {r.center_lon:.5f}")

# 6) 안정성: 80% 부분표본으로 다시 군집화해서 원래 군집과 얼마나 같은지 (ARI)
rng = np.random.default_rng(SEED)
aris = []
for _ in range(30):
    sub = rng.choice(len(df), size=int(len(df) * 0.8), replace=False)
    km_s = KMeans(n_clusters=K, n_init=10, random_state=int(rng.integers(1e6))).fit(X[sub])
    aris.append(adjusted_rand_score(df["cluster"].values[sub], km_s.labels_))
print(f"\n== 안정성 (80% 부분표본 30회, ARI) 평균 {np.mean(aris):.3f} | 표준편차 {np.std(aris):.3f}")

df[["seg_id", "course", "seg_idx", "cluster", "center_lat", "center_lon"]].to_csv(
    "data/processed/segment_clusters.csv", index=False, encoding="utf-8-sig")
print("\n저장 완료: data/processed/segment_clusters.csv, reports/figures/*.png")