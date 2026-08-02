"""
Phase 3b/3c — Weak Point Detector + Recommendation Engine.

The two are combined in one module because every weak point IS an actionable
recommendation target — detecting "billing amount is declining" without also
saying what to do about it isn't useful. The Recommendation Engine's job is
specifically the `suggested_action` text on each WeakPoint; keeping it as a
clearly separate function per detector (not just inlined) is what keeps the
"detect vs recommend" split real rather than cosmetic.

Language rule for every string below: write it so someone with zero data
analysis background can read it and understand what's wrong and why it
matters. No "margin", "concentration", "IQR", "quartile", "variance" — say
what those things actually mean in plain terms instead.
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

    return [WeakPoint(
        problem=f"{primary.column} is trending down",
        impact=f"{primary.column} dropped from {_fmt_num(agg.iloc[0])} to {_fmt_num(agg.iloc[-1])} "
               f"between {agg.index[0]} and {agg.index[-1]} — a {_fmt_pct(magnitude)} decrease.",
        priority=priority,
        suggested_action=(
            f"Check whether this drop is happening across the board or mainly in one specific group. "
            f"If it's just one group, something specific likely changed there and can probably be fixed. "
            f"If it's happening everywhere at once, the cause is more likely something external."
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
        roughly_out_of_100 = round(pct)
        out.append(WeakPoint(
            problem=f"Missing information: {col}",
            impact=f"About {roughly_out_of_100} out of every 100 records don't have a value for {col}. "
                   f"Any chart, average, or comparison that uses {col} is only seeing part of the picture.",
            priority=priority,
            suggested_action=(
                f"Figure out why {col} is missing so often — is it an optional field that's fine to leave "
                f"blank, or something that should have been filled in but wasn't? If it should be there, "
                f"fixing how it's collected going forward matters more than trying to fill in old records."
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
                problem=f"A few unusually high {m.column} values",
                impact=f"Just {len(outliers)} records ({_fmt_pct(row_share)} of all rows) have {m.column} "
                       f"values far above everything else — but together they make up {_fmt_pct(value_share)} "
                       f"of the total. That's enough for a handful of records to make an average or total "
                       f"look bigger than it really is for most of the data.",
                priority=priority,
                suggested_action=(
                    f"Take a look at these {len(outliers)} records specifically. If they're real (a genuinely "
                    f"huge order, an unusually long stay, etc.), that's fine — just know they're skewing the "
                    f"numbers. If they look like typos or data entry mistakes, fixing them will make averages "
                    f"and totals more trustworthy."
                ),
                category="outlier",
                score=value_share,
            ))
            break  # one outlier flag is enough signal; don't repeat per measure
    return out


def concentration_risk(df: pd.DataFrame, profile: DatasetProfile) -> list:
    """Domain-flavored: 'disease hotspot' for healthcare CONDITION, generic
    framing otherwise — same detection logic, different wording."""
    out = []
    primary = profile.primary_measure
    if not primary:
        return out

    DOMAIN_FRAME = {
        "CONDITION": "One condition shows up far more than others",
        "CUSTOMER": "A small number of customers make up most of the business",
        "HOSPITAL": "One hospital is handling a lot more than the others",
        "LOCATION": "One region stands out from the rest",
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
        problem_label = DOMAIN_FRAME.get(d.role, f"One {d.column} stands out from the rest")

        out.append(WeakPoint(
            problem=problem_label,
            impact=f"{top_label} alone makes up {_fmt_pct(share)} of all {primary.column} — much more than "
                   f"you'd expect if it were spread evenly across the {len(grouped)} different "
                   f"{d.column} groups (which would be about {_fmt_pct(expected)} each).",
            priority=priority,
            suggested_action=(
                f"This isn't necessarily a problem, but it's worth a deliberate look: is {top_label} getting "
                f"the attention and resources it deserves given how much depends on it? And is there a "
                f"backup plan if something changes there, since so much currently relies on just this one?"
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
                problem=f"{worst_label} is falling behind on {m.column}",
                impact=f"{worst_label} averages {_fmt_num(worst_val)} for {m.column}, which is "
                       f"{_fmt_pct(gap_pct)} lower than the overall average of {_fmt_num(overall_avg)}.",
                priority=priority,
                suggested_action=(
                    f"Look into what makes {worst_label} different — is it a resourcing issue, a support "
                    f"gap, or something structural? Understand the specific cause there before assuming "
                    f"a one-size-fits-all fix will help."
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
                problem=f"{label} is actually losing money",
                impact=f"{label} brought in {_fmt_num(row[revenue.column])} in {revenue.column}, but after "
                       f"costs it lost {_fmt_num(abs(row[profit.column]))} overall — every sale here is "
                       f"currently costing more than it earns.",
                priority=priority,
                suggested_action=(
                    f"Find out whether the losses come from discounting too heavily or from the underlying "
                    f"cost being too high. If it's discounting, capping how much gets discounted here should "
                    f"fix it without losing the sales. If it's cost, that likely needs a price increase or "
                    f"a cheaper way to deliver it."
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
        problem="Big discounts are losing money, not just cutting profit",
        impact=f"Once a discount goes above {worst_band}, those sales stop making money entirely and "
               f"start losing it instead — on average, losing about {_fmt_pct(abs(worst_val))} of the "
               f"sale price for every order discounted that much.",
        priority=priority,
        suggested_action=(
            f"Consider capping discounts at around {safe_ceiling}, which is the highest level where sales "
            f"were still profitable. Anything beyond that could require manager approval instead of being "
            f"offered automatically at checkout."
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
