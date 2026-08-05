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
from typing import Optional
import math
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
