"""
Correlation Center.

Distinct from the "Correlations" section's heatmap in the Explorer, which
shows the raw matrix — this is the summary layer: which relationships
actually matter, ranked, with the strongest positive and negative called
out explicitly rather than left for the user to spot in a grid of numbers.
"""
from dataclasses import dataclass
import pandas as pd

from app.understanding import DatasetProfile

MIN_INTEREST_R = 0.3


@dataclass
class CorrelationPair:
    col1: str
    col2: str
    r: float


def analyze_correlations(df: pd.DataFrame, profile: DatasetProfile, min_r: float = MIN_INTEREST_R) -> dict:
    cols = [m.column for m in profile.measures]
    if len(cols) < 2:
        return {"pairs": [], "strongest_positive": None, "strongest_negative": None}

    try:
        corr = df[cols].corr(numeric_only=True)
    except Exception:
        return {"pairs": [], "strongest_positive": None, "strongest_negative": None}

    pairs = []
    for i, c1 in enumerate(cols):
        for c2 in cols[i + 1:]:
            r = corr.loc[c1, c2]
            if pd.notna(r) and abs(r) >= min_r:
                pairs.append(CorrelationPair(col1=c1, col2=c2, r=float(r)))

    pairs.sort(key=lambda p: abs(p.r), reverse=True)
    positive = [p for p in pairs if p.r > 0]
    negative = [p for p in pairs if p.r < 0]

    return {
        "pairs": pairs,
        "strongest_positive": max(positive, key=lambda p: p.r) if positive else None,
        "strongest_negative": min(negative, key=lambda p: p.r) if negative else None,
    }
