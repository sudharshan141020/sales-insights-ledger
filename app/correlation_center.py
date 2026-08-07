"""
Correlation Center.

Distinct from the "Correlations" section's heatmap in the Explorer, which
shows the raw matrix — this is the summary layer: which relationships
actually matter, ranked, with the strongest positive and negative called
out explicitly rather than left for the user to spot in a grid of numbers.

Every pair is also tested for statistical significance (Pearson's r with a
two-sided t-test p-value) and flagged when the sample size is too small to
trust the coefficient. A strong r on 6 rows is noise, not a finding — this
is what stops the tool from reporting spurious correlations as real ones.
"""
from dataclasses import dataclass
from typing import Optional, Tuple
import math
import numpy as np
import pandas as pd

from app.understanding import DatasetProfile

try:
    from scipy import stats as _scipy_stats
    _HAS_SCIPY = True
except ImportError:  # pragma: no cover - scipy is a listed dependency
    _HAS_SCIPY = False

MIN_INTEREST_R = 0.3
MIN_SAMPLE_SIZE = 5          # below this, a p-value is meaningless -- skip it
SMALL_SAMPLE_THRESHOLD = 30  # below this, still show it but caveat it
SIGNIFICANCE_ALPHA = 0.05


@dataclass
class CorrelationPair:
    col1: str
    col2: str
    r: float
    n: int
    p_value: Optional[float] = None
    significant: Optional[bool] = None
    strength: str = "weak"
    caveat: Optional[str] = None


def _strength_label(r: float) -> str:
    a = abs(r)
    if a >= 0.7:
        return "strong"
    if a >= 0.5:
        return "moderate"
    return "weak"


def _std_normal_cdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def _two_sided_t_pvalue_fallback(t: float, df: int) -> float:
    """Normal-approximation p-value for when scipy isn't importable. scipy
    is a listed dependency so this path shouldn't run in production, but
    it keeps the feature from hard-failing if the environment is missing
    it for any reason."""
    if df <= 0:
        return 1.0
    x = t * (1 - 1 / (4 * df)) / math.sqrt(1 + t ** 2 / (2 * df))
    p = 2 * (1 - _std_normal_cdf(x))
    return max(0.0, min(1.0, p))


def _correlate_pair(df: pd.DataFrame, c1: str, c2: str):
    """Returns (r, n, p_value) for one column pair, or None if there isn't
    enough usable data (too few paired rows, or a constant column making
    correlation undefined)."""
    pair_df = df[[c1, c2]].dropna()
    n = len(pair_df)
    if n < MIN_SAMPLE_SIZE:
        return None

    x, y = pair_df[c1], pair_df[c2]
    if x.std(ddof=0) == 0 or y.std(ddof=0) == 0:
        return None

    if _HAS_SCIPY:
        r, p = _scipy_stats.pearsonr(x, y)
        return float(r), n, float(p)

    r = float(x.corr(y))
    if n <= 2 or abs(r) >= 1:
        return r, n, 0.0
    t_stat = r * math.sqrt((n - 2) / (1 - r ** 2))
    p = _two_sided_t_pvalue_fallback(abs(t_stat), n - 2)
    return r, n, p


def analyze_correlations(df: pd.DataFrame, profile: DatasetProfile, min_r: float = MIN_INTEREST_R) -> dict:
    cols = [m.column for m in profile.measures]
    if len(cols) < 2:
        return {"pairs": [], "strongest_positive": None, "strongest_negative": None}

    pairs = []
    for i, c1 in enumerate(cols):
        for c2 in cols[i + 1:]:
            result = _correlate_pair(df, c1, c2)
            if result is None:
                continue
            r, n, p = result
            if pd.isna(r) or abs(r) < min_r:
                continue

            significant = p < SIGNIFICANCE_ALPHA
            if n < SMALL_SAMPLE_THRESHOLD:
                caveat = f"Only {n} paired data points -- treat this relationship with caution."
            elif not significant:
                caveat = f"Not statistically significant (p={p:.2f}) -- could be due to chance."
            else:
                caveat = None

            pairs.append(CorrelationPair(
                col1=c1, col2=c2, r=r, n=n, p_value=p,
                significant=significant, strength=_strength_label(r),
                caveat=caveat,
            ))

    pairs.sort(key=lambda p: abs(p.r), reverse=True)
    positive = [p for p in pairs if p.r > 0]
    negative = [p for p in pairs if p.r < 0]

    def _pick(candidates, best_fn):
        # Prefer the strongest *significant* relationship as the headline;
        # fall back to strongest overall so the section isn't empty on
        # small datasets -- but the caveat still travels with it either way.
        sig = [c for c in candidates if c.significant]
        pool = sig if sig else candidates
        return best_fn(pool) if pool else None

    return {
        "pairs": pairs,
        "strongest_positive": _pick(positive, lambda lst: max(lst, key=lambda p: p.r)),
        "strongest_negative": _pick(negative, lambda lst: min(lst, key=lambda p: p.r)),
    }


# ---------------------------------------------------------------------------
# Multicollinearity (VIF)
# ---------------------------------------------------------------------------
# Separate from pairwise correlation: two measures can each look fine in
# isolation but still be redundant once you account for every other measure
# predicting them. VIF (Variance Inflation Factor) catches that. Computed
# via plain least-squares (numpy), no sklearn/statsmodels needed.

VIF_MODERATE = 5.0   # conventional analytics thresholds
VIF_SEVERE = 10.0


@dataclass
class VifResult:
    column: str
    vif: float
    severity: str  # "ok" | "moderate" | "severe"
    note: str


def _vif_severity(vif: float) -> Tuple[str, str]:
    if vif >= VIF_SEVERE:
        return "severe", "Highly redundant with the other measures — consider dropping or combining it."
    if vif >= VIF_MODERATE:
        return "moderate", "Meaningfully overlaps with the other measures — worth a second look."
    return "ok", "Contributes independent information."


def analyze_multicollinearity(df: pd.DataFrame, profile: DatasetProfile, min_measures: int = 3) -> dict:
    """For each numeric measure, regress it on all the other measures and
    compute VIF = 1 / (1 - R^2). A high VIF means this measure is largely
    predictable from the others -- i.e. it's not adding independent signal,
    which matters if someone downstream tries to use these as regression
    predictors. Needs at least 3 measures (VIF is meaningless with only 2 --
    that's just the pairwise correlation again) and at least 10 usable rows.
    """
    cols = [m.column for m in profile.measures]
    if len(cols) < min_measures:
        return {"results": [], "note": None}

    usable = df[cols].dropna()
    if len(usable) < 10:
        return {"results": [], "note": "Not enough complete rows across all measures to check for redundancy."}

    # Drop any column that's constant in the usable subset -- undefined R^2.
    usable = usable.loc[:, usable.std(ddof=0) > 0]
    cols = list(usable.columns)
    if len(cols) < min_measures:
        return {"results": [], "note": None}

    results = []
    X_full = usable.to_numpy(dtype=float)
    for i, col in enumerate(cols):
        y = X_full[:, i]
        others = np.delete(X_full, i, axis=1)
        others_with_intercept = np.column_stack([np.ones(len(others)), others])
        try:
            coeffs, _, _, _ = np.linalg.lstsq(others_with_intercept, y, rcond=None)
            y_pred = others_with_intercept @ coeffs
            ss_res = np.sum((y - y_pred) ** 2)
            ss_tot = np.sum((y - y.mean()) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
            r_squared = max(0.0, min(0.999999, r_squared))  # guard divide-by-zero below
            vif = 1 / (1 - r_squared)
        except np.linalg.LinAlgError:
            continue

        severity, note = _vif_severity(vif)
        results.append(VifResult(column=col, vif=float(vif), severity=severity, note=note))

    results.sort(key=lambda r: r.vif, reverse=True)
    return {"results": results, "note": None}
