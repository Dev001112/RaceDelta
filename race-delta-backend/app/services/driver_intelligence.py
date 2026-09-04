# app/services/driver_intelligence.py
"""
Phase 3 — Driver Intelligence, built on the Phase-2 feature store (driver_race_features).

  Module 1  AI Driver Rating   weighted 0–100 score over telemetry-derived dimensions
  Module 2  Driver DNA         per-driver performance vector, cosine/Euclidean similarity, PCA coords
  Module 3  Style Clustering   K-Means / DBSCAN / hierarchical on the DNA vectors, 2-D PCA map

All three share one matrix (matrix_from_frame): every raw feature is first expressed
relative to the field *within the same race* (z-score across that race's drivers, signed so
higher is always better), then averaged over the driver's races. That makes circuits of
different length and character comparable before any cross-driver statistics are done.

The maths is in pure functions that take DataFrames; the *_for_season() wrappers add the
DB read and a cache keyed by the store's row count (so results refresh after every ingest).
"""
import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN, AgglomerativeClustering, KMeans
from sklearn.decomposition import PCA
from sklearn.metrics.pairwise import cosine_similarity, euclidean_distances
from sklearn.preprocessing import StandardScaler

from models import Constructor, Driver, DriverRaceFeature
from app.services import cache_store

CACHE_TTL = 3600

# dimension -> (source column, sign)   sign +1: higher raw = better; -1: lower raw = better
DIMENSIONS = {
    "race_pace":       ("avg_pace_s", -1),
    "qualifying_pace": ("grid_position", -1),   # ponytail: grid as qualifying proxy until Q sessions are stored
    "consistency":     ("lap_consistency_s", -1),
    "tyre_management": ("tyre_degradation_s_per_lap", -1),
    "overtaking":      ("overtake_count", +1),
    "defence":         ("positions_lost", -1),   # derived: max(0, finish - grid)
    "position_gain":   ("position_changes", +1),
    "discipline":      ("penalties", -1),
}
WET = "wet_performance"                          # position_gain restricted to rainfall races
ALL_DIMENSIONS = list(DIMENSIONS) + [WET]

RATING_WEIGHTS = {
    "race_pace": 0.25, "qualifying_pace": 0.15, "consistency": 0.15, "tyre_management": 0.10,
    "overtaking": 0.10, "defence": 0.05, "position_gain": 0.10, "wet_performance": 0.05, "discipline": 0.05,
}
LOW_SAMPLE_RACES = 3

CLUSTER_LABELS = {
    "race_pace": "Race Pace Leaders", "qualifying_pace": "Qualifying Specialists",
    "consistency": "Smooth & Consistent", "tyre_management": "Tyre Managers",
    "overtaking": "Aggressive Overtakers", "defence": "Defensive Specialists",
    "position_gain": "Race-Day Climbers", "wet_performance": "Wet Weather Specialists",
    "discipline": "Clean Racers",
}
SOURCE_COLUMNS = ["avg_pace_s", "grid_position", "finish_position", "lap_consistency_s",
                  "tyre_degradation_s_per_lap", "overtake_count", "position_changes", "penalties"]


# ============================================================ pure maths
def matrix_from_frame(df: pd.DataFrame):
    """
    Per-race feature rows (one per driver per race) -> (season_vector, races)
      season_vector : DataFrame index=driver_code, columns=ALL_DIMENSIONS, higher = better,
                      in within-race z units averaged over the driver's races (0 = field average)
      races         : Series driver_code -> number of races
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=ALL_DIMENSIONS), pd.Series(dtype=int)
    d = df.copy()
    for c in SOURCE_COLUMNS:
        d[c] = pd.to_numeric(d[c], errors="coerce") if c in d else np.nan
    d["positions_lost"] = (d["finish_position"] - d["grid_position"]).clip(lower=0)
    d["rainfall"] = d["rainfall"].fillna(False).astype(bool) if "rainfall" in d else False

    for dim, (col, sign) in DIMENSIONS.items():
        grp = d.groupby("round")[col]
        std = grp.transform("std").replace(0, np.nan)
        d[dim] = (d[col] - grp.transform("mean")) / std * sign
    d[WET] = d["position_gain"].where(d["rainfall"])

    vec = d.groupby("driver_code")[ALL_DIMENSIONS].mean().fillna(0.0)
    races = d.groupby("driver_code")["round"].nunique().reindex(vec.index).fillna(0).astype(int)
    return vec, races


def rating_from_matrix(vec: pd.DataFrame, races: pd.Series, weights: dict = None) -> list:
    """Module 1: min-max each dimension to 0–100 across the field, then weighted sum."""
    weights = weights or RATING_WEIGHTS
    if vec.empty:
        return []
    scores = vec.copy()
    for c in scores.columns:
        lo, hi = scores[c].min(), scores[c].max()
        scores[c] = 50.0 if hi == lo else (scores[c] - lo) / (hi - lo) * 100.0
    overall = sum(scores[dim] * w for dim, w in weights.items()) / sum(weights.values())
    out = []
    for rank, code in enumerate(overall.sort_values(ascending=False).index, 1):
        comps = {dim: round(float(scores.loc[code, dim]), 1) for dim in weights}
        out.append({
            "rank": rank, "driver_code": code, "rating": round(float(overall[code]), 1),
            "races": int(races.get(code, 0)), "low_sample": int(races.get(code, 0)) < LOW_SAMPLE_RACES,
            "components": comps, "strongest": max(comps, key=comps.get),
        })
    return out


def _scaled(vec: pd.DataFrame) -> np.ndarray:
    return StandardScaler().fit_transform(vec.values) if len(vec) > 1 else np.zeros_like(vec.values, dtype=float)


def _pca(X: np.ndarray):
    n_comp = min(2, X.shape[0], X.shape[1])
    if X.shape[0] < 2 or n_comp < 1:
        return np.zeros((X.shape[0], 2)), [0.0, 0.0]
    pca = PCA(n_components=n_comp).fit(X)
    coords = pca.transform(X)
    if coords.shape[1] < 2:
        coords = np.c_[coords, np.zeros(len(coords))]
    ev = [round(float(v), 4) for v in pca.explained_variance_ratio_] + [0.0] * (2 - n_comp)
    return coords, ev


def dna_from_matrix(vec: pd.DataFrame, races: pd.Series, driver_code: str, k: int = 5) -> dict:
    """Module 2: z-scored vector for one driver, nearest drivers by cosine similarity, PCA coords."""
    code = driver_code.upper()
    if code not in vec.index:
        raise ValueError(f"No feature data for {code}")
    X = _scaled(vec)
    i = list(vec.index).index(code)
    cos = cosine_similarity(X)[i] if len(vec) > 1 else np.ones(1)
    euc = euclidean_distances(X)[i] if len(vec) > 1 else np.zeros(1)
    coords, ev = _pca(X)
    order = [j for j in np.argsort(-cos) if j != i][:k]
    return {
        "driver_code": code, "races": int(races.get(code, 0)),
        "vector": {dim: round(float(X[i, n]), 3) for n, dim in enumerate(vec.columns)},
        "relative": {dim: round(float(vec.loc[code, dim]), 3) for dim in vec.columns},
        "similar": [{"driver_code": vec.index[j], "cosine_similarity": round(float(cos[j]), 4),
                     "euclidean_distance": round(float(euc[j]), 4)} for j in order],
        "pca": {"x": round(float(coords[i, 0]), 4), "y": round(float(coords[i, 1]), 4), "explained_variance": ev},
        "dimensions": list(vec.columns),
    }


def clusters_from_matrix(vec: pd.DataFrame, races: pd.Series, method: str = "kmeans",
                         k: int = 4, eps: float = 1.5, min_samples: int = 2) -> dict:
    """Module 3: cluster the z-scored vectors and place every driver on a 2-D PCA map."""
    n = len(vec)
    if n == 0:
        return {"method": method, "k": 0, "n_clusters": 0, "explained_variance": [0.0, 0.0],
                "points": [], "clusters": [], "dimensions": ALL_DIMENSIONS}
    X = _scaled(vec)
    method = method.lower()
    k = max(1, min(int(k), n))
    if n == 1:
        labels = np.zeros(1, dtype=int)
    elif method == "kmeans":
        labels = KMeans(n_clusters=k, n_init=10, random_state=42).fit_predict(X)
    elif method == "dbscan":
        labels = DBSCAN(eps=float(eps), min_samples=int(min_samples)).fit_predict(X)
    elif method in ("hierarchical", "agglomerative"):
        labels = AgglomerativeClustering(n_clusters=k).fit_predict(X)
    else:
        raise ValueError(f"Unknown clustering method '{method}' (kmeans | dbscan | hierarchical)")
    coords, ev = _pca(X)

    points = [{"driver_code": code, "cluster": int(labels[i]), "x": round(float(coords[i, 0]), 4),
               "y": round(float(coords[i, 1]), 4), "races": int(races.get(code, 0))}
              for i, code in enumerate(vec.index)]
    clusters = []
    for label in sorted(set(int(l) for l in labels)):
        idx = np.where(labels == label)[0]
        profile = {dim: round(float(X[idx, n_].mean()), 3) for n_, dim in enumerate(vec.columns)}
        if label == -1:
            name = "Outliers"
        else:
            top = max(profile, key=profile.get)
            name = CLUSTER_LABELS[top] if profile[top] >= 0.2 else "Balanced All-Rounders"
        clusters.append({"cluster": label, "label": name, "size": int(len(idx)),
                         "members": [vec.index[i] for i in idx], "profile": profile})
    return {"method": method, "k": k, "n_clusters": len([c for c in clusters if c["cluster"] != -1]),
            "explained_variance": ev, "points": points, "clusters": clusters, "dimensions": list(vec.columns)}


# ============================================================ DB wrappers
def load_season_frame(season: int):
    """Feature-store rows for a season as a DataFrame, plus {code: {name, team, photo}}."""
    rows = DriverRaceFeature.query.filter_by(season=season).all()
    if not rows:
        return pd.DataFrame(), {}
    drivers = {d.driver_id: d for d in Driver.query.filter(Driver.driver_id.in_({r.driver_id for r in rows})).all()}
    teams = {c.constructor_id: c.name for c in Constructor.query.all()}
    df = pd.DataFrame([{**{c: getattr(r, c) for c in SOURCE_COLUMNS},
                        "driver_code": r.driver_code, "round": r.round, "rainfall": r.rainfall,
                        "driver_id": r.driver_id, "constructor_id": r.constructor_id} for r in rows])
    meta = {}
    for code, g in df.sort_values("round").groupby("driver_code"):
        last = g.iloc[-1]
        d = drivers.get(last["driver_id"])
        meta[code] = {"name": d.full_name if d else code, "team": teams.get(last["constructor_id"]),
                      "photo": d.photo_url if d else None}
    return df, meta


def _cached(key_parts, build):
    season = key_parts[1]
    n_rows = DriverRaceFeature.query.filter_by(season=season).count()
    key = ":".join(str(p) for p in key_parts) + f":rows={n_rows}"
    return cache_store.cached("derived", key, cache_store.LONG_TTL, build)


def _with_meta(items, meta):
    for it in items:
        it.update(meta.get(it["driver_code"], {"name": it["driver_code"], "team": None, "photo": None}))
    return items


def rating_for_season(season: int) -> dict:
    def build():
        df, meta = load_season_frame(season)
        vec, races = matrix_from_frame(df)
        drivers = _with_meta(rating_from_matrix(vec, races), meta)
        return {"season": season, "method": "within-race z-score → min-max 0–100 → weighted sum",
                "weights": RATING_WEIGHTS, "count": len(drivers), "drivers": drivers, "source": "feature_store"}
    return _cached(["ai_rating:v1", season], build)


def resolve_driver_code(season: int, text: str) -> str:
    """'ANT', 'Antonelli', 'Kimi Antonelli' -> 'ANT'.

    The analyst LLM passes whatever the user typed, usually a surname, while the feature store
    keys on the three-letter code. Falls back to the input so an unknown driver still 404s
    with a sensible message instead of silently resolving to somebody else.
    """
    t = (text or "").strip()
    if len(t) == 3 and t.isalpha():
        return t.upper()          # already a code; skip the DB round-trip
    _, meta = load_season_frame(season)
    if t.upper() in meta:
        return t.upper()
    tl = t.lower()
    for code, m in meta.items():
        name = (m.get("name") or "").lower()
        if name and (tl == name or tl in name.split() or tl in name):
            return code
    return t.upper()


def dna_for_season(season: int, driver_code: str, k: int = 5) -> dict:
    driver_code = resolve_driver_code(season, driver_code)

    def build():
        df, meta = load_season_frame(season)
        vec, races = matrix_from_frame(df)
        dna = dna_from_matrix(vec, races, driver_code, k)
        dna.update(meta.get(dna["driver_code"], {}))
        _with_meta(dna["similar"], meta)
        dna["season"] = season
        dna["source"] = "feature_store"
        return dna
    return _cached(["ai_dna:v1", season, driver_code.upper(), k], build)


def clusters_for_season(season: int, method: str = "kmeans", k: int = 4,
                        eps: float = 1.5, min_samples: int = 2) -> dict:
    def build():
        df, meta = load_season_frame(season)
        vec, races = matrix_from_frame(df)
        res = clusters_from_matrix(vec, races, method, k, eps, min_samples)
        _with_meta(res["points"], meta)
        res["season"] = season
        res["source"] = "feature_store"
        return res
    return _cached(["ai_clusters:v1", season, method.lower(), k, eps, min_samples], build)
