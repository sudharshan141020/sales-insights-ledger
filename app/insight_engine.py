"""
Phase 3a — Insight Engine.

Generates informative findings about the dataset — "what's true about this
data" — as distinct from the Weak Point Detector's "what's wrong with this
data." Both consume the same DatasetProfile + dataframe; they're split into
two modules because they answer different questions and a caller (like the
Executive Summary) may want one without the other.

Every insight is phrased using the dataset's actual entity name and column
names, so a healthcare file says "patients" and a sales file says
"customers" without either concept being hardcoded per-domain — the
phrasing just substitutes profile.primary_entity into the same template.
"""
from dataclasses import dataclass
import pandas as pd

from app.understanding import DatasetProfile


@dataclass
class Insight:
    text: str
    category: str   # "summary" | "trend" | "correlation" | "top_segment"
    score: float     # for ranking; not a probability, just relative significance


def _fmt_num(x: float) -> str:
    if abs(x) >= 1_000_000:
        return f"{x / 1_000_000:.2f}M"
    if abs(x) >= 1_000:
        return f"{x / 1_000:.1f}K"
    if abs(x) >= 10:
        return f"{x:.1f}"
    return f"{x:.2f}"


def _fmt_pct(x: float) -> str:
    return f"{x:.1f}%"


def mode_insights(df: pd.DataFrame, profile: DatasetProfile) -> list:
    """'X is the most common {dimension}' — for every chartable dimension,
    not just the headline one, since 'most common blood type' is genuinely
    interesting even if it's not THE headline finding."""
    out = []
    entity = profile.primary_entity.lower() + "s"
    for d in profile.dimensions:
        if not d.is_chartable:
            continue
        vc = df[d.column].value_counts()
        if vc.empty:
            continue
        top_value, top_count = vc.index[0], vc.iloc[0]
        share = top_count / len(df) * 100
        out.append(Insight(
            text=f"{top_value} is the most common {d.column.lower()} — "
                 f"{_fmt_pct(share)} of {entity} ({top_count} of {len(df)}).",
            category="summary",
            score=share,
        ))
    return out


def measure_summary_insights(df: pd.DataFrame, profile: DatasetProfile) -> list:
    """'Average {measure} is X' for every measure."""
    out = []
    entity = profile.primary_entity.lower() + "s"
    for m in profile.measures:
        series = df[m.column].dropna()
        if series.empty:
            continue
        avg = series.mean()
        out.append(Insight(
            text=f"Average {m.column.lower()} across {len(series)} {entity} is {_fmt_num(avg)}.",
            category="summary",
            score=20,  # baseline informative, not usually THE headline
        ))
    return out


def trend_insight(df: pd.DataFrame, profile: DatasetProfile) -> list:
    primary = profile.primary_measure
    if not primary or not profile.date_column:
        return []
    tmp = df.dropna(subset=[profile.date_column, primary.column]).copy()
    if tmp.empty:
        return []
    tmp["_year"] = tmp[profile.date_column].dt.year
    agg = tmp.groupby("_year")[primary.column].mean() if primary.aggregation == "avg" else tmp.groupby("_year")[primary.column].sum()
    if len(agg) < 2:
        return []
    first, last = agg.iloc[0], agg.iloc[-1]
    if first == 0:
        return []
    change = (last - first) / abs(first) * 100
    direction = "grew" if change >= 0 else "declined"
    return [Insight(
        text=f"{primary.column} {direction} {_fmt_pct(abs(change))} from "
             f"{agg.index[0]} ({_fmt_num(first)}) to {agg.index[-1]} ({_fmt_num(last)}).",
        category="trend",
        score=min(abs(change), 150),
    )]


def top_segment_insights(df: pd.DataFrame, profile: DatasetProfile) -> list:
    """'{Segment} has the highest {measure}' — the informative version of
    concentration (as opposed to the Weak Point Detector's risk framing)."""
    out = []
    primary = profile.primary_measure
    if not primary:
        return out
    for d in profile.dimensions:
        if not d.is_chartable or d.column == primary.column:
            continue
        grouped = df.groupby(d.column)[primary.column].sum() if primary.aggregation == "sum" else df.groupby(d.column)[primary.column].mean()
        if grouped.empty or len(grouped) < 2:
            continue
        top_label = grouped.idxmax()
        top_val = grouped.max()
        verb = "handles the largest" if profile.primary_entity != "Record" else "has the highest"
        out.append(Insight(
            text=f"{top_label} {verb} {primary.column.lower()} among {d.column.lower()} groups ({_fmt_num(top_val)}).",
            category="top_segment",
            score=25,
        ))
    return out


def correlation_insight(df: pd.DataFrame, profile: DatasetProfile) -> list:
    numeric_cols = [m.column for m in profile.measures]
    if len(numeric_cols) < 2:
        return []
    try:
        corr = df[numeric_cols].corr(numeric_only=True)
    except Exception:
        return []
    best = None
    for i, c1 in enumerate(numeric_cols):
        for c2 in numeric_cols[i + 1:]:
            r = corr.loc[c1, c2]
            if pd.notna(r) and abs(r) >= 0.4:
                if best is None or abs(r) > abs(best[2]):
                    best = (c1, c2, r)
    if not best:
        return []
    c1, c2, r = best
    direction = "increases" if r > 0 else "decreases"
    return [Insight(
        text=f"{c1} and {c2} are correlated (r={r:.2f}) — as {c1} goes up, {c2} typically {direction}.",
        category="correlation",
        score=abs(r) * 80,
    )]


def generate_insights(df: pd.DataFrame, profile: DatasetProfile, top_k: int = 8) -> list:
    detectors = [mode_insights, measure_summary_insights, trend_insight, top_segment_insights, correlation_insight]
    all_insights = []
    for detector in detectors:
        try:
            all_insights.extend(detector(df, profile))
        except Exception:
            continue
    all_insights.sort(key=lambda i: i.score, reverse=True)
    return all_insights[:top_k]
