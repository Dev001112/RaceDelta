# app/services/pace_model.py
"""
Per-race lap-time model for the Strategy Lab (Phase 4).

    lap_time_s ~ f(driver, compound, tyre_life, lap_number)

learned on that race's clean laps. XGBoost is the documented predictor and is used when
installed; a per-(driver, compound) linear model  base + degradation x tyre_life + fuel x lap
is the always-available fallback and what the unit tests exercise. Tree models cannot
extrapolate beyond the longest stint seen, so beyond that age the linear degradation slope
is added on top of the XGBoost prediction.
"""
import numpy as np
import pandas as pd

try:
    from xgboost import XGBRegressor
    HAS_XGBOOST = True
except Exception:  # pragma: no cover - environment without xgboost
    XGBRegressor = None
    HAS_XGBOOST = False

GREEN = "1"
FUEL_EFFECT_S_PER_LAP = -0.03   # ponytail: fixed fuel-burn gain; fit it once a race with wide lap coverage per stint exists
DEG_CLAMP = (-0.15, 0.35)        # sane per-lap degradation range for extrapolation (s/lap)
XGB_PARAMS = dict(n_estimators=250, max_depth=4, learning_rate=0.06, subsample=0.9,
                  min_child_weight=3, reg_lambda=1.0, n_jobs=2)


def clean_laps(laps: pd.DataFrame) -> pd.DataFrame:
    """Green-flag, accurate, non-pit laps with a compound and tyre age."""
    if laps is None or laps.empty:
        return laps
    m = laps["lap_time_s"].notna() & laps["compound"].notna() & laps["tyre_life"].notna()
    if "is_accurate" in laps:
        m &= laps["is_accurate"].fillna(False).astype(bool)
    for col in ("is_pit_in", "is_pit_out"):
        if col in laps:
            m &= ~laps[col].fillna(False).astype(bool)
    if "track_status" in laps:
        m &= laps["track_status"].astype(str) == GREEN
    return laps[m]


class PaceModel:
    def __init__(self, laps: pd.DataFrame, use_xgboost: bool = True, random_state: int = 42):
        df = clean_laps(laps)
        self.n_train = int(len(df)) if df is not None else 0
        self.kind = "linear"
        self.rmse = 1.0
        self.rmse_linear = None
        self._xgb = None
        self._lin = {}
        self._global = (90.0, 0.0)
        self._max_life = {}
        if self.n_train == 0:
            self.drivers, self.compounds, self._d, self._c = [], [], {}, {}
            return
        self.drivers = sorted(df["driver_code"].dropna().astype(str).unique().tolist())
        self.compounds = sorted(df["compound"].dropna().astype(str).unique().tolist())
        self._d = {d: i for i, d in enumerate(self.drivers)}
        self._c = {c: i for i, c in enumerate(self.compounds)}
        self._max_life = df.groupby("compound")["tyre_life"].max().to_dict()
        self._fit_linear(df)
        if use_xgboost and HAS_XGBOOST and self.n_train >= 60:
            self._fit_xgb(df, random_state)

    # ------------------------------------------------------------ linear fallback
    def _fit_linear(self, df: pd.DataFrame):
        y_adj = df["lap_time_s"].astype(float) - FUEL_EFFECT_S_PER_LAP * df["lap_number"].astype(float)

        def fit(idx):
            g = df.loc[idx]
            A = np.c_[np.ones(len(g)), g["tyre_life"].to_numpy(float)]
            coef, *_ = np.linalg.lstsq(A, y_adj.loc[idx].to_numpy(float), rcond=None)
            base, deg = float(coef[0]), float(np.clip(coef[1], *DEG_CLAMP))
            return base, deg

        self._global = fit(df.index)
        for comp, idx in df.groupby("compound").groups.items():
            if len(idx) >= 5:
                self._lin[("*", str(comp))] = fit(idx)
        for (drv, comp), idx in df.groupby(["driver_code", "compound"]).groups.items():
            if len(idx) >= 5:
                self._lin[(str(drv), str(comp))] = fit(idx)
        pred = self._predict_linear(df["driver_code"].to_numpy(str), df["compound"].to_numpy(str),
                                    df["tyre_life"].to_numpy(float), df["lap_number"].to_numpy(float))
        self.rmse_linear = float(np.sqrt(np.mean((pred - df["lap_time_s"].to_numpy(float)) ** 2)))
        self.rmse = self.rmse_linear

    def _coef(self, driver, compound):
        return self._lin.get((driver, compound)) or self._lin.get(("*", compound)) or self._global

    def _predict_linear(self, driver, compound, tyre_life, lap_number):
        out = np.empty(len(driver))
        for i in range(len(driver)):
            base, deg = self._coef(str(driver[i]), str(compound[i]))
            out[i] = base + deg * tyre_life[i] + FUEL_EFFECT_S_PER_LAP * lap_number[i]
        return out

    # ------------------------------------------------------------ xgboost
    def _X(self, driver, compound, tyre_life, lap_number):
        d = np.array([self._d.get(str(x), -1) for x in driver], dtype=float)
        c = np.array([self._c.get(str(x), -1) for x in compound], dtype=float)
        return np.c_[d, c, np.asarray(tyre_life, dtype=float), np.asarray(lap_number, dtype=float)]

    def _fit_xgb(self, df: pd.DataFrame, seed: int):
        X = self._X(df["driver_code"].to_numpy(str), df["compound"].to_numpy(str),
                    df["tyre_life"].to_numpy(float), df["lap_number"].to_numpy(float))
        y = df["lap_time_s"].to_numpy(float)
        mask = np.random.default_rng(seed).random(len(df)) < 0.85
        params = dict(XGB_PARAMS, random_state=seed)
        if (~mask).sum() >= 10:
            hold = XGBRegressor(**params).fit(X[mask], y[mask])
            self.rmse = float(np.sqrt(np.mean((hold.predict(X[~mask]) - y[~mask]) ** 2)))
        self._xgb = XGBRegressor(**params).fit(X, y)
        self.kind = "xgboost"

    # ------------------------------------------------------------ public
    def predict(self, driver, compound, tyre_life, lap_number) -> np.ndarray:
        driver = np.atleast_1d(np.asarray(driver, dtype=object))
        compound = np.atleast_1d(np.asarray(compound, dtype=object))
        tyre_life = np.atleast_1d(np.asarray(tyre_life, dtype=float))
        lap_number = np.atleast_1d(np.asarray(lap_number, dtype=float))
        if self._xgb is None:
            return self._predict_linear(driver, compound, tyre_life, lap_number)
        pred = self._xgb.predict(self._X(driver, compound, tyre_life, lap_number)).astype(float)
        # trees plateau past the longest stint seen: extend with the linear degradation slope
        for i in range(len(pred)):
            seen = self._max_life.get(str(compound[i]))
            if seen is not None and tyre_life[i] > seen:
                pred[i] += max(0.0, self._coef(str(driver[i]), str(compound[i]))[1]) * (tyre_life[i] - seen)
        return pred

    def describe(self) -> dict:
        return {"kind": self.kind, "rmse_s": round(float(self.rmse), 3), "n_train_laps": self.n_train,
                "rmse_linear_s": round(self.rmse_linear, 3) if self.rmse_linear is not None else None,
                "compounds": self.compounds}
