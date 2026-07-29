"""
Computes standard KPIs from a dataframe + a column role mapping produced by
column_detector.detect_columns(). Every function degrades gracefully if a
role is missing (e.g. no profit column) instead of throwing.
"""
import pandas as pd


def prepare(df: pd.DataFrame, mapping: dict) -> pd.DataFrame:
    """Coerce mapped columns to correct dtypes, derive profit from revenue-cost if needed."""
    out = df.copy()

    if "date" in mapping:
        out[mapping["date"]] = pd.to_datetime(out[mapping["date"]], errors="coerce")

    for role in ("revenue", "profit", "cost", "quantity", "discount"):
        if role in mapping:
            out[mapping[role]] = pd.to_numeric(out[mapping[role]], errors="coerce")

    # normalize discount to 0-1 scale if it looks like it's in 0-100
    if "discount" in mapping:
        col = mapping["discount"]
        if out[col].max(skipna=True) is not None and out[col].max(skipna=True) > 1.5:
            out[col] = out[col] / 100.0

    # derive profit if missing but cost+revenue present
    if "profit" not in mapping and "revenue" in mapping and "cost" in mapping:
        out["_derived_profit"] = out[mapping["revenue"]] - out[mapping["cost"]]
        mapping["profit"] = "_derived_profit"

    return out


def compute_kpis(df: pd.DataFrame, mapping: dict) -> dict:
    kpis = {}
    rev_col = mapping.get("revenue")
    profit_col = mapping.get("profit")
    date_col = mapping.get("date")
    cust_col = mapping.get("customer")
    qty_col = mapping.get("quantity")

    if rev_col:
        kpis["total_revenue"] = float(df[rev_col].sum())
    if profit_col:
        kpis["total_profit"] = float(df[profit_col].sum())
    if rev_col and profit_col:
        total_rev = df[rev_col].sum()
        kpis["overall_profit_margin_pct"] = (
            float(df[profit_col].sum() / total_rev * 100) if total_rev else None
        )
    if rev_col:
        kpis["order_count"] = int(len(df))
        kpis["avg_order_value"] = float(df[rev_col].mean())
    if cust_col:
        kpis["unique_customers"] = int(df[cust_col].nunique())
        if rev_col:
            kpis["avg_revenue_per_customer"] = float(
                df.groupby(cust_col)[rev_col].sum().mean()
            )
    if qty_col:
        kpis["total_units_sold"] = float(df[qty_col].sum())
    if date_col:
        valid_dates = df[date_col].dropna()
        if not valid_dates.empty:
            kpis["date_range"] = [str(valid_dates.min().date()), str(valid_dates.max().date())]

    # Generic stats — computed regardless of whether this looks like sales data,
    # so a dataset with no recognizable metric still gets useful baseline numbers.
    kpis["row_count"] = int(len(df))
    kpis["column_count"] = int(len(df.columns))
    missing_frac = df.isnull().mean().mean() if len(df.columns) else 0
    kpis["data_completeness_pct"] = float(round((1 - missing_frac) * 100, 1))

    return kpis


def timeseries_monthly(df: pd.DataFrame, mapping: dict) -> list:
    """Monthly revenue (and profit if available) for charting."""
    date_col = mapping.get("date")
    rev_col = mapping.get("revenue")
    if not date_col or not rev_col:
        return []

    tmp = df.dropna(subset=[date_col]).copy()
    tmp["_ym"] = tmp[date_col].dt.to_period("M").astype(str)
    agg = {rev_col: "sum"}
    if mapping.get("profit"):
        agg[mapping["profit"]] = "sum"
    grouped = tmp.groupby("_ym").agg(agg).reset_index()

    result = []
    for _, row in grouped.iterrows():
        entry = {"month": row["_ym"], "revenue": float(row[rev_col])}
        if mapping.get("profit"):
            entry["profit"] = float(row[mapping["profit"]])
        result.append(entry)
    return result


def breakdown_by_column(df: pd.DataFrame, col: str, mapping: dict, top_n: int = 15) -> list:
    """Revenue/profit breakdown by any categorical column name (not restricted to a role)."""
    rev_col = mapping.get("revenue")
    if not col or not rev_col or col not in df.columns:
        return []

    agg = {rev_col: "sum"}
    if mapping.get("profit"):
        agg[mapping["profit"]] = "sum"

    grouped = df.groupby(col).agg(agg).reset_index()
    grouped = grouped.sort_values(rev_col, ascending=False).head(top_n)

    result = []
    for _, row in grouped.iterrows():
        entry = {"label": str(row[col]), "revenue": float(row[rev_col])}
        if mapping.get("profit"):
            rev = row[rev_col]
            entry["profit"] = float(row[mapping["profit"]])
            entry["margin_pct"] = float(row[mapping["profit"]] / rev * 100) if rev else None
        result.append(entry)
    return result


def breakdown_by(df: pd.DataFrame, mapping: dict, role: str, top_n: int = 15) -> list:
    """Revenue/profit breakdown by a categorical role (category or region). Kept
    for backward compatibility — prefer breakdown_by_column for arbitrary columns."""
    col = mapping.get(role)
    return breakdown_by_column(df, col, mapping, top_n)


def all_breakdowns(df: pd.DataFrame, mapping: dict, extra_categoricals: list, max_cols: int = 6) -> list:
    """
    Scans EVERY meaningful categorical column — not just the two roles
    (category/region) — and returns a breakdown for each. This is what makes
    the tool actually analyze the whole file instead of ignoring columns that
    didn't happen to get name-matched to 'category' or 'region'.
    """
    rev_col = mapping.get("revenue")
    if not rev_col:
        return []

    cat_cols = []
    for role in ("category", "region"):
        c = mapping.get(role)
        if c and c not in cat_cols:
            cat_cols.append(c)
    for c in extra_categoricals:
        if c not in cat_cols:
            cat_cols.append(c)

    # A useful breakdown column has more than one value but isn't basically a
    # unique identifier — skip columns with too many or too few distinct values.
    row_count = len(df)
    useful_cols = [
        c for c in cat_cols
        if c in df.columns and 2 <= df[c].nunique() <= min(30, max(row_count * 0.5, 2))
    ]
    useful_cols = useful_cols[:max_cols]

    results = []
    for c in useful_cols:
        data = breakdown_by_column(df, c, mapping)
        if data:
            results.append({"column": c, "data": data})
    return results


def combine_dataframes(prepared_with_mappings: list, source_names: list) -> tuple:
    """
    Takes [(df_prepared, mapping), ...] from multiple already-analyzed files
    and merges them into one dataframe with one canonical column per role,
    plus a '_source_file' column for traceability. Returns (combined_df,
    combined_mapping) ready to feed straight into compute_kpis/timeseries_
    monthly/breakdown_by/generate_insights — same functions as a single file,
    so every stat (averages, unique counts, margins) is computed correctly on
    the real merged rows rather than being averaged-of-averages across files.
    """
    all_roles = set()
    for _, mapping in prepared_with_mappings:
        all_roles.update(mapping.keys())

    frames = []
    for (df, mapping), name in zip(prepared_with_mappings, source_names):
        rename = {col: role for role, col in mapping.items()}
        sub = df.rename(columns=rename)
        keep_cols = [r for r in all_roles if r in sub.columns]
        sub = sub[keep_cols].copy()
        sub["_source_file"] = name
        frames.append(sub)

    combined = pd.concat(frames, ignore_index=True, sort=False)
    combined_mapping = {role: role for role in all_roles}
    return combined, combined_mapping
