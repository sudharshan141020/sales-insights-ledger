"""
Executes analysis specs produced by planner.plan_analyses() against the
actual dataframe, producing chart-ready data.

Every analysis type returns a list of {"label": str, "value": number} so the
frontend can use ONE generic bar/line chart component regardless of whether
it's a trend, histogram, count distribution, or sum/avg distribution —
that's what makes the dynamic dropdown in Phase 4 tractable without a
different renderer per analysis type.
"""
import numpy as np
import pandas as pd

TOP_N = 15
HIST_BINS = 10


def _compute_trend(df: pd.DataFrame, metric_col: str, date_col: str, aggregation: str) -> list:
    tmp = df.dropna(subset=[date_col, metric_col]).copy()
    if tmp.empty:
        return []
    tmp["_month"] = tmp[date_col].dt.to_period("M").astype(str)
    grouped = tmp.groupby("_month")[metric_col].mean() if aggregation == "avg" else tmp.groupby("_month")[metric_col].sum()
    grouped = grouped.sort_index()
    return [{"label": m, "value": float(v)} for m, v in grouped.items()]


def _compute_histogram(df: pd.DataFrame, col: str, bins: int = HIST_BINS) -> list:
    series = df[col].dropna()
    if series.empty:
        return []
    n_bins = min(bins, max(series.nunique(), 1))
    try:
        counts, edges = np.histogram(series, bins=n_bins)
    except Exception:
        return []
    result = []
    for i in range(len(counts)):
        lo, hi = edges[i], edges[i + 1]
        label = f"{lo:.0f}-{hi:.0f}" if max(abs(lo), abs(hi)) >= 10 else f"{lo:.1f}-{hi:.1f}"
        result.append({"label": label, "value": int(counts[i])})
    return result


def _compute_distribution_count(df: pd.DataFrame, col: str, top_n: int = TOP_N) -> list:
    vc = df[col].value_counts().head(top_n)
    return [{"label": str(k), "value": int(v)} for k, v in vc.items()]


def _compute_distribution_sum(df: pd.DataFrame, col: str, metric_col: str, aggregation: str, top_n: int = TOP_N) -> list:
    grouped = df.groupby(col)[metric_col].mean() if aggregation == "avg" else df.groupby(col)[metric_col].sum()
    grouped = grouped.sort_values(ascending=False).head(top_n)
    return [{"label": str(k), "value": float(v)} for k, v in grouped.items()]


def execute_analysis(df: pd.DataFrame, spec: dict) -> dict:
    """Returns spec merged with a 'data' key. Never raises — a single bad
    analysis spec returns empty data rather than breaking the whole response."""
    try:
        t = spec["type"]
        if t == "trend":
            data = _compute_trend(df, spec["metric_column"], spec["date_column"], spec.get("aggregation", "sum"))
        elif t == "histogram":
            data = _compute_histogram(df, spec["column"])
        elif t == "distribution_count":
            data = _compute_distribution_count(df, spec["column"])
        elif t == "distribution_sum":
            data = _compute_distribution_sum(df, spec["column"], spec["metric_column"], spec.get("aggregation", "sum"))
        else:
            data = []
    except Exception:
        data = []

    return {**spec, "data": data}


def execute_all(df: pd.DataFrame, specs: list) -> list:
    executed = [execute_analysis(df, spec) for spec in specs]
    return [a for a in executed if a["data"]]  # drop any that produced nothing
