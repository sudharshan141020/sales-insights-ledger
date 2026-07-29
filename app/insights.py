"""
Rule-based insight engine. No external API calls — every insight is a
templated sentence filled in with real numbers, ranked by "surprise" so the
top few shown to the user are the most decision-relevant, not random.

Each detector returns a list of dicts:
    {"text": str, "score": float, "type": str}
score is roughly "how far from a neutral/expected baseline", used for ranking.
"""
import pandas as pd


def _fmt_pct(x):
    return f"{x:.1f}%"


def _fmt_money(x):
    if abs(x) >= 1_000_000:
        return f"${x/1_000_000:.2f}M"
    if abs(x) >= 1_000:
        return f"${x/1_000:.1f}K"
    return f"${x:.2f}"


def trend_insights(df, mapping, extra_categoricals=None):
    out = []
    date_col, rev_col = mapping.get("date"), mapping.get("revenue")
    if not date_col or not rev_col:
        return out

    tmp = df.dropna(subset=[date_col]).copy()
    if tmp.empty:
        return out
    tmp["_year"] = tmp[date_col].dt.year
    yearly = tmp.groupby("_year")[rev_col].sum().sort_index()
    if len(yearly) >= 2:
        first, last = yearly.iloc[0], yearly.iloc[-1]
        if first > 0:
            growth = (last - first) / first * 100
            direction = "grew" if growth >= 0 else "declined"
            if growth >= 0:
                recommendation = (
                    f"Identify which segments or time periods drove this growth in "
                    f"{rev_col} and double down there — check the breakdown charts for "
                    f"what's outperforming before assuming it's even across the board."
                )
            else:
                recommendation = (
                    f"Investigate whether the decline in {rev_col} is concentrated in a "
                    f"specific segment or spread evenly — a broad drop points to external "
                    f"conditions, while a concentrated one points to something fixable."
                )
            out.append({
                "text": f"{rev_col} {direction} {_fmt_pct(abs(growth))} from "
                        f"{yearly.index[0]} ({_fmt_money(first)}) to "
                        f"{yearly.index[-1]} ({_fmt_money(last)}).",
                "recommendation": recommendation,
                "score": min(abs(growth), 200),
                "type": "trend",
            })
    return out


def _categorical_columns_to_scan(df, mapping, extra_categoricals, max_cols=8):
    """Shared helper: every meaningful categorical column, labeled by its own
    name — not just whatever got mapped to the 'category'/'region' roles."""
    cols = []
    for role in ("category", "region"):
        c = mapping.get(role)
        if c and c not in cols:
            cols.append(c)
    for c in (extra_categoricals or []):
        if c not in cols:
            cols.append(c)

    row_count = len(df)
    useful = [
        c for c in cols
        if c in df.columns and 2 <= df[c].nunique() <= min(30, max(row_count * 0.5, 2))
    ]
    return useful[:max_cols]


def segment_concentration_insights(df, mapping, extra_categoricals=None):
    """Which single value in ANY categorical column contributes a
    disproportionate share of the primary metric — scans every meaningful
    categorical column in the file, not just category/region."""
    out = []
    rev_col = mapping.get("revenue")
    if not rev_col:
        return out

    for col in _categorical_columns_to_scan(df, mapping, extra_categoricals):
        grouped = df.groupby(col)[rev_col].sum().sort_values(ascending=False)
        total = grouped.sum()
        if total == 0 or len(grouped) < 2:
            continue
        top_label, top_val = grouped.index[0], grouped.iloc[0]
        share = top_val / total * 100
        expected_share = 100 / len(grouped)
        if share > expected_share * 1.5:  # meaningfully concentrated
            others = grouped.iloc[1:]
            weakest_label = others.idxmin() if len(others) else None
            recommendation = (
                f"This isn't automatically bad, but it's worth asking two questions: "
                f"is {top_label} being protected/invested in enough given how much it "
                f"carries, and is there upside in growing "
                f"{f'{weakest_label}' if weakest_label else 'the smaller groups'} "
                f"instead of relying on one {col} value for growth."
            )
            out.append({
                "text": f"{top_label} accounts for {_fmt_pct(share)} of total {rev_col} "
                        f"({_fmt_money(top_val)}) across {col} values — "
                        f"disproportionate versus an even {_fmt_pct(expected_share)} split "
                        f"across {len(grouped)} {col} groups.",
                "recommendation": recommendation,
                "score": share - expected_share,
                "type": "concentration",
            })
    return out


def margin_risk_insights(df, mapping, extra_categoricals=None):
    """Flags any categorical column's values (not just category/region) with
    negative or unusually low margin, plus discount-band risk."""
    out = []
    rev_col, profit_col = mapping.get("revenue"), mapping.get("profit")
    if not rev_col or not profit_col:
        return out

    for col in _categorical_columns_to_scan(df, mapping, extra_categoricals):
        grouped = df.groupby(col).agg({rev_col: "sum", profit_col: "sum"})
        grouped["margin"] = grouped[profit_col] / grouped[rev_col].replace(0, pd.NA) * 100
        losers = grouped[grouped["margin"] < 0].sort_values("margin")
        for label, row in losers.iterrows():
            out.append({
                "text": f"{label} ({col}) is unprofitable overall: "
                        f"{_fmt_pct(row['margin'])} margin on {_fmt_money(row[rev_col])} "
                        f"in {rev_col}, losing {_fmt_money(abs(row[profit_col]))}.",
                "recommendation": (
                    f"Before cutting {label}, check whether the loss comes from "
                    f"pricing/discounting or from cost — if it's discount-driven, a "
                    f"floor on discount depth for this {col} may fix it without losing "
                    f"the revenue; if it's cost-driven, it may need a price increase "
                    f"or supplier renegotiation."
                ),
                "score": abs(row["margin"]) + 20,  # negative margin is always high-signal
                "type": "margin_risk",
            })

    if mapping.get("discount"):
        disc_col = mapping["discount"]
        tmp = df.dropna(subset=[disc_col]).copy()
        tmp["_band"] = pd.cut(
            tmp[disc_col],
            bins=[-0.01, 0, 0.2, 0.4, 0.6, 1.01],
            labels=["0%", "1-20%", "21-40%", "41-60%", "60%+"],
        )
        band_margin = tmp.groupby("_band").apply(
            lambda g: (g[profit_col].sum() / g[rev_col].sum() * 100) if g[rev_col].sum() else None,
            include_groups=False,
        )
        neg_bands = band_margin[band_margin < 0]
        if not neg_bands.empty:
            worst_band = neg_bands.idxmin()
            worst_val = neg_bands.min()
            safe_bands = band_margin[band_margin >= 0]
            safe_ceiling = safe_bands.index[-1] if len(safe_bands) else None
            out.append({
                "text": f"Orders discounted {worst_band} run a {_fmt_pct(worst_val)} average "
                        f"margin — discounting past this point is actively losing money, "
                        f"not just cutting profit.",
                "recommendation": (
                    f"Consider capping discretionary discounts at the "
                    f"{safe_ceiling if safe_ceiling else 'lowest'} band, where margin was "
                    f"still positive — treat anything beyond that as needing manager "
                    f"approval rather than a default option at checkout."
                ),
                "score": abs(worst_val) + 30,
                "type": "discount_risk",
            })
    return out


def customer_concentration_insights(df, mapping, extra_categoricals=None):
    out = []
    rev_col, cust_col = mapping.get("revenue"), mapping.get("customer")
    if not rev_col or not cust_col:
        return out
    grouped = df.groupby(cust_col)[rev_col].sum().sort_values(ascending=False)
    total = grouped.sum()
    if total == 0 or len(grouped) < 10:
        return out
    top_n = max(1, int(len(grouped) * 0.1))
    top_share = grouped.iloc[:top_n].sum() / total * 100
    if top_share > 20:
        out.append({
            "text": f"The top 10% of customers ({top_n} of {len(grouped)}) drive "
                    f"{_fmt_pct(top_share)} of total {rev_col}.",
            "recommendation": (
                "Put a retention plan around this group specifically — losing even "
                "one or two of them would be a much bigger hit than an average "
                "customer churning. Also worth checking whether the rest of the "
                "base has room to grow toward that level, or whether the gap is "
                "structural (e.g. B2B vs. individual buyers)."
            ),
            "score": top_share,
            "type": "customer_concentration",
        })
    return out


def correlation_insights(df, mapping, extra_categoricals=None):
    """Works on ANY dataset with 2+ numeric columns — not sales-specific.
    Finds the strongest linear relationship between any two numeric columns."""
    out = []
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    # drop columns that are just row indices/ids in disguise (near-unique small ints)
    numeric_cols = [c for c in numeric_cols if df[c].nunique() > 3]
    if len(numeric_cols) < 2:
        return out

    try:
        corr = df[numeric_cols].corr(numeric_only=True)
    except Exception:
        return out

    best = None
    for i, c1 in enumerate(numeric_cols):
        for c2 in numeric_cols[i + 1:]:
            r = corr.loc[c1, c2]
            if pd.notna(r) and abs(r) >= 0.5:
                if best is None or abs(r) > abs(best[2]):
                    best = (c1, c2, r)

    if best:
        c1, c2, r = best
        direction = "tends to increase" if r > 0 else "tends to decrease"
        strength = "strong" if abs(r) >= 0.75 else "moderate"
        out.append({
            "text": f"{c1} and {c2} show a {strength} relationship (r={r:.2f}) — "
                    f"as {c1} goes up, {c2} {direction}.",
            "recommendation": (
                f"Correlation isn't causation — worth checking whether {c1} actually "
                f"drives {c2}, or whether both are being pulled by a third factor "
                f"before making decisions based on this relationship."
            ),
            "score": abs(r) * 90,
            "type": "correlation",
        })
    return out


def outlier_insights(df, mapping, extra_categoricals=None):
    """Works on ANY numeric column, not just revenue — flags when a small
    number of extreme values are skewing the total for the primary metric."""
    out = []
    col = mapping.get("revenue")
    if not col:
        return out
    series = df[col].dropna()
    if len(series) < 20:
        return out

    q1, q3 = series.quantile(0.25), series.quantile(0.75)
    iqr = q3 - q1
    if iqr == 0:
        return out
    upper_fence = q3 + 1.5 * iqr
    outliers = series[series > upper_fence]

    if len(outliers) == 0:
        return out
    outlier_share_of_rows = len(outliers) / len(series) * 100
    outlier_share_of_total = outliers.sum() / series.sum() * 100 if series.sum() else 0

    # only surface if it's a SMALL number of rows contributing a DISPROPORTIONATE amount
    if outlier_share_of_rows < 8 and outlier_share_of_total > 20:
        out.append({
            "text": f"{len(outliers)} unusually high {col} values "
                    f"({_fmt_pct(outlier_share_of_rows)} of rows) account for "
                    f"{_fmt_pct(outlier_share_of_total)} of the total {col}.",
            "recommendation": (
                "Check whether these are legitimate high performers/outliers or data "
                "entry errors — a small number of extreme values can distort averages "
                "and make the overall picture look better (or worse) than it really is."
            ),
            "score": outlier_share_of_total,
            "type": "outlier",
        })
    return out


def missing_data_insights(df, mapping, extra_categoricals=None):
    """Works on ANY dataset — flags columns with significant missing data,
    since that's a genuine data-quality concern regardless of domain."""
    out = []
    missing_pct = (df.isnull().mean() * 100).sort_values(ascending=False)
    worst = missing_pct[missing_pct > 20]
    if worst.empty:
        return out
    col = worst.index[0]
    pct = worst.iloc[0]
    out.append({
        "text": f"{col} is missing in {_fmt_pct(pct)} of rows.",
        "recommendation": (
            "Confirm whether this is expected (e.g. an optional field) or a data "
            "collection gap — heavy missingness in a column used elsewhere in this "
            "analysis can bias averages and breakdowns without it being obvious."
        ),
        "score": pct * 0.8,
        "type": "data_quality",
    })
    return out


def generate_insights(df, mapping, extra_categoricals=None, top_k=7):
    detectors = [
        trend_insights,
        segment_concentration_insights,
        margin_risk_insights,
        customer_concentration_insights,
        correlation_insights,
        outlier_insights,
        missing_data_insights,
    ]
    all_insights = []
    for detector in detectors:
        try:
            all_insights.extend(detector(df, mapping, extra_categoricals))
        except Exception:
            continue  # a single detector failing shouldn't break the whole response

    all_insights.sort(key=lambda x: x["score"], reverse=True)
    return all_insights[:top_k]
