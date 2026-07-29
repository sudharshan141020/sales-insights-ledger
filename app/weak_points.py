"""
Phase 3b/3c — Weak Point Detector + Recommendation Engine.

The two are combined in one module because every weak point IS an actionable
recommendation target — detecting "billing amount is declining" without also
saying what to do about it isn't useful. The Recommendation Engine's job is
specifically the `suggested_action` text on each WeakPoint; keeping it as a
clearly separate function per detector (not just inlined) is what keeps the
"detect vs recommend" split real rather than cosmetic.
"""
from dataclasses import dataclass
import pandas as pd

from app.understanding import DatasetProfile

HIGH, MEDIUM, LOW = "high", "medium", "low"


@dataclass
class WeakPoint:
    problem: str
    impact: str
    priority: str          # "high" | "medium" | "low"
    suggested_action: str
    category: str          # "trend" | "data_quality" | "concentration" | "outlier" | "underperformance"
    score: float            # for ranking across weak points


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


# ============================================================
# Detectors — each returns list[WeakPoint]
# ============================================================

def declining_trend(df: pd.DataFrame, profile: DatasetProfile) -> list:
    primary = profile.primary_measure
    if not primary or not profile.date_column:
        return []
    tmp = df.dropna(subset=[profile.date_column, primary.column]).copy()
    if tmp.empty:
        return []
    tmp["_year"] = tmp[profile.date_column].dt.year
    agg = tmp.groupby("_year")[primary.column].mean() if primary.aggregation == "avg" else tmp.groupby("_year")[primary.column].sum()
    if len(agg) < 2 or agg.iloc[0] == 0:
        return []
    change = (agg.iloc[-1] - agg.iloc[0]) / abs(agg.iloc[0]) * 100
    if change >= -5:  # not a meaningful decline
        return []

    magnitude = abs(change)
    priority = HIGH if magnitude > 30 else MEDIUM if magnitude > 15 else LOW
    problem_label = f"Declining {primary.column}"

    return [WeakPoint(
        problem=problem_label,
        impact=f"{primary.column} fell {_fmt_pct(magnitude)} from {agg.index[0]} to {agg.index[-1]} "
               f"({_fmt_num(agg.iloc[0])} → {_fmt_num(agg.iloc[-1])}).",
        priority=priority,
        suggested_action=(
            f"Break down {primary.column} by each available dimension to see whether the decline is "
            f"concentrated in one segment (fixable — points to something specific that changed) or spread "
            f"evenly across all of them (points to an external/market-wide cause instead)."
        ),
        category="trend",
        score=magnitude,
    )]


def missing_data(df: pd.DataFrame, profile: DatasetProfile) -> list:
    out = []
    missing_pct = (df.isnull().mean() * 100).sort_values(ascending=False)
    worst = missing_pct[missing_pct > 15]
    for col, pct in worst.head(3).items():
        priority = HIGH if pct > 50 else MEDIUM if pct > 30 else LOW
        out.append(WeakPoint(
            problem=f"Missing data in {col}",
            impact=f"{col} is missing in {_fmt_pct(pct)} of rows, which can bias any average, "
                   f"breakdown, or trend that relies on it.",
            priority=priority,
            suggested_action=(
                f"Confirm whether this is expected (e.g. {col} is an optional field) or a genuine data "
                f"collection gap. If it's expected, exclude {col} from anything requiring completeness; "
                f"if it's a gap, fixing collection going forward matters more than imputing the past."
            ),
            category="data_quality",
            score=pct,
        ))
    return out


def outlier_risk(df: pd.DataFrame, profile: DatasetProfile) -> list:
    out = []
    for m in profile.measures:
        series = df[m.column].dropna()
        if len(series) < 20:
            continue
        q1, q3 = series.quantile(0.25), series.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            continue
        upper_fence = q3 + 1.5 * iqr
        outliers = series[series > upper_fence]
        if outliers.empty:
            continue
        row_share = len(outliers) / len(series) * 100
        value_share = outliers.sum() / series.sum() * 100 if series.sum() else 0
        if row_share < 8 and value_share > 20:
            priority = HIGH if value_share > 40 else MEDIUM
            out.append(WeakPoint(
                problem=f"Outliers in {m.column}",
                impact=f"{len(outliers)} unusually high {m.column} values ({_fmt_pct(row_share)} of rows) "
                       f"account for {_fmt_pct(value_share)} of the total — a small number of extreme "
                       f"values are distorting the overall picture.",
                priority=priority,
                suggested_action=(
                    f"Check these {len(outliers)} rows individually — confirm they're legitimate before "
                    f"trusting any average or total that includes {m.column}, since a handful of data entry "
                    f"errors or genuine extreme cases can swing the numbers substantially either way."
                ),
                category="outlier",
                score=value_share,
            ))
            break  # one outlier flag is enough signal; don't repeat per measure
    return out


def concentration_risk(df: pd.DataFrame, profile: DatasetProfile) -> list:
    """Domain-flavored: 'disease hotspot' for healthcare CONDITION, generic
    'concentration risk' otherwise — same detection logic, different framing."""
    out = []
    primary = profile.primary_measure
    if not primary:
        return out

    DOMAIN_FRAME = {
        "CONDITION": "Disease hotspot",
        "CUSTOMER": "Customer concentration risk",
        "HOSPITAL": "Hospital load imbalance",
        "LOCATION": "Regional concentration",
    }

    for d in profile.dimensions:
        if not d.is_chartable or d.column == primary.column:
            continue
        grouped = df.groupby(d.column)[primary.column].sum()
        total = grouped.sum()
        if total == 0 or len(grouped) < 2:
            continue
        top_label, top_val = grouped.idxmax(), grouped.max()
        share = top_val / total * 100
        expected = 100 / len(grouped)
        if share <= expected * 1.5:
            continue

        priority = HIGH if share > 50 else MEDIUM if share > expected * 2 else LOW
        problem_label = DOMAIN_FRAME.get(d.role, f"{d.column} concentration")

        out.append(WeakPoint(
            problem=problem_label,
            impact=f"{top_label} accounts for {_fmt_pct(share)} of total {primary.column} across "
                   f"{d.column} groups — versus an even {_fmt_pct(expected)} split across {len(grouped)} groups.",
            priority=priority,
            suggested_action=(
                f"This isn't automatically bad, but worth deciding deliberately: is {top_label} being "
                f"resourced/protected adequately given how much it carries, and is there a plan if it "
                f"underperforms — since so much currently depends on it."
            ),
            category="concentration",
            score=share - expected,
        ))
    return out


def underperforming_segment(df: pd.DataFrame, profile: DatasetProfile) -> list:
    """The lowest-performing category for a measure where LOW is bad — e.g.
    lowest-average-score subject, lowest attendance group."""
    out = []
    LOW_IS_BAD_ROLES = {"SCORE", "ATTENDANCE"}
    for m in profile.measures:
        if m.role not in LOW_IS_BAD_ROLES:
            continue
        for d in profile.dimensions:
            if not d.is_chartable:
                continue
            grouped = df.groupby(d.column)[m.column].mean()
            if len(grouped) < 2:
                continue
            worst_label, worst_val = grouped.idxmin(), grouped.min()
            overall_avg = df[m.column].mean()
            if overall_avg == 0:
                continue
            gap_pct = (overall_avg - worst_val) / overall_avg * 100
            if gap_pct < 15:  # not meaningfully worse than average
                continue
            priority = HIGH if gap_pct > 35 else MEDIUM
            out.append(WeakPoint(
                problem=f"Low {m.column} in {worst_label}",
                impact=f"{worst_label} averages {_fmt_num(worst_val)} on {m.column}, "
                       f"{_fmt_pct(gap_pct)} below the overall average of {_fmt_num(overall_avg)}.",
                priority=priority,
                suggested_action=(
                    f"Investigate what's different about {worst_label} specifically — resourcing, "
                    f"support, or structural factors — before assuming the same fix applies dataset-wide."
                ),
                category="underperformance",
                score=gap_pct,
            ))
    return out


def margin_risk(df: pd.DataFrame, profile: DatasetProfile) -> list:
    """Unprofitable segments — needs both a revenue-like and a profit-like
    measure to exist, which is why this only fires for financial data."""
    out = []
    revenue = next((m for m in profile.measures if m.role == "FINANCIAL_METRIC"), None)
    profit = next((m for m in profile.measures if m.role == "PROFIT"), None)
    if not revenue or not profit:
        return out

    for d in profile.dimensions:
        if not d.is_chartable:
            continue
        grouped = df.groupby(d.column).agg({revenue.column: "sum", profit.column: "sum"})
        grouped["margin"] = grouped[profit.column] / grouped[revenue.column].replace(0, pd.NA) * 100
        losers = grouped[grouped["margin"] < 0].sort_values("margin")
        for label, row in losers.head(2).iterrows():
            priority = HIGH if row["margin"] < -20 else MEDIUM
            out.append(WeakPoint(
                problem=f"{label} is unprofitable",
                impact=f"{label} ({d.column}) runs a {_fmt_pct(row['margin'])} margin on "
                       f"{_fmt_num(row[revenue.column])} in {revenue.column}, "
                       f"losing {_fmt_num(abs(row[profit.column]))}.",
                priority=priority,
                suggested_action=(
                    f"Check whether the loss is discount-driven or cost-driven before cutting {label} — "
                    f"a discount cap fixes the former without losing the revenue, while the latter needs "
                    f"a price increase or cost renegotiation."
                ),
                category="underperformance",
                score=abs(row["margin"]) + 15,
            ))
    return out


def discount_risk(df: pd.DataFrame, profile: DatasetProfile) -> list:
    revenue = next((m for m in profile.measures if m.role == "FINANCIAL_METRIC"), None)
    profit = next((m for m in profile.measures if m.role == "PROFIT"), None)
    discount = next((m for m in profile.measures if m.role == "DISCOUNT"), None)
    if not revenue or not profit or not discount:
        return []

    tmp = df.dropna(subset=[discount.column]).copy()
    if tmp[discount.column].max() > 1.5:
        tmp[discount.column] = tmp[discount.column] / 100.0
    tmp["_band"] = pd.cut(
        tmp[discount.column],
        bins=[-0.01, 0, 0.2, 0.4, 0.6, 1.01],
        labels=["0%", "1-20%", "21-40%", "41-60%", "60%+"],
    )
    band_margin = tmp.groupby("_band", observed=True).apply(
        lambda g: (g[profit.column].sum() / g[revenue.column].sum() * 100) if g[revenue.column].sum() else None,
        include_groups=False,
    )
    neg_bands = band_margin[band_margin < 0]
    if neg_bands.empty:
        return []

    worst_band, worst_val = neg_bands.idxmin(), neg_bands.min()
    safe_bands = band_margin[band_margin >= 0]
    safe_ceiling = safe_bands.index[-1] if len(safe_bands) else "0%"
    priority = HIGH if worst_val < -50 else MEDIUM

    return [WeakPoint(
        problem="Discounting is unprofitable past a threshold",
        impact=f"Orders discounted {worst_band} run a {_fmt_pct(worst_val)} average margin — "
               f"discounting past this point actively loses money, not just cuts profit.",
        priority=priority,
        suggested_action=(
            f"Cap discretionary discounts at the {safe_ceiling} band, where margin was still positive — "
            f"treat anything beyond that as needing approval rather than a default checkout option."
        ),
        category="underperformance",
        score=abs(worst_val) + 20,
    )]


def generate_weak_points(df: pd.DataFrame, profile: DatasetProfile, top_k: int = 6) -> list:
    detectors = [
        declining_trend, missing_data, outlier_risk, concentration_risk,
        underperforming_segment, margin_risk, discount_risk,
    ]
    all_weak_points = []
    for detector in detectors:
        try:
            all_weak_points.extend(detector(df, profile))
        except Exception:
            continue
    all_weak_points.sort(key=lambda w: w.score, reverse=True)
    return all_weak_points[:top_k]
