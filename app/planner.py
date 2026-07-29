"""
Phase 3 — Analysis planner.

Given the semantic roles (Phase 1) and detected domain (Phase 2), decides
WHICH analyses actually make sense to offer — replacing the old behavior of
always plotting the primary metric against every category regardless of
whether that's the meaningful question for this data.

Domain only affects TITLES/labels here. The selection logic itself (which
roles produce which analysis types) is domain-agnostic, which is what keeps
this extensible — adding a new domain means adding keywords (Phase 1) and
signal weights (Phase 2), not new planner code.
"""

# Semantic roles that make sense as a "slice by this" dimension, with a
# domain-aware title template. "default" is always required; other keys are
# domain-specific overrides.
DIMENSION_ROLE_TITLES = {
    "CONDITION":      {"default": "Patient Distribution by {col}"},
    "HOSPITAL":       {"default": "Patient Count by {col}"},
    "INSURANCE":      {"default": "Insurance Distribution by {col}"},
    "ADMISSION_TYPE": {"default": "Admission Type Distribution"},
    "MEDICATION":     {"default": "Medication Frequency"},
    "TEST_RESULT":    {"default": "Test Result Distribution"},
    "GENDER":         {"default": "Gender Distribution"},
    "DEMOGRAPHIC":    {"default": "{col} Distribution"},
    "DEPARTMENT":     {"default": "Department Distribution"},
    "JOB_TITLE":      {"default": "Job Title Distribution"},
    "VEHICLE":        {"default": "Vehicle Type Distribution"},
    "ROOM":           {"default": "Room Distribution"},
    "SUBJECT":        {"default": "{col} Distribution"},
    "CATEGORY":       {"sales": "{col} Breakdown", "default": "{col} Distribution"},
    "LOCATION":       {"sales": "{col} Breakdown", "default": "{col} Distribution"},
}

# Standalone numeric roles worth their own histogram/summary, domain-aware title.
NUMERIC_SUMMARY_ROLE_TITLES = {
    "AGE":            {"default": "Age Distribution"},
    "SCORE":          {"default": "{col} Distribution"},
    "ATTENDANCE":     {"default": "Attendance Distribution"},
    "LENGTH_OF_STAY": {"default": "Length of Stay Distribution"},
    "TENURE":         {"default": "Tenure Distribution"},
    "CONGESTION":     {"default": "{col} Distribution"},
    "ACCIDENT":       {"default": "{col} Distribution"},
    "SPEED":          {"default": "{col} Distribution"},
}

# Candidate "headline metric" roles, in priority order. FINANCIAL_METRIC wins
# whenever present (money is almost always the most decision-relevant number
# in a dataset that has it) — but domains without money still need a
# meaningful trend/histogram target, so the next-best numeric role present
# takes over instead of leaving the dataset with no headline metric at all.
CANDIDATE_METRIC_ROLES = ["FINANCIAL_METRIC", "SCORE", "CONGESTION", "ACCIDENT", "SPEED"]

# How a metric should be aggregated when grouped by a dimension. Summing
# only makes sense for money/counts — summing test scores or congestion
# levels across a group produces a meaningless number; those need averages.
AGGREGATION_BY_ROLE = {
    "FINANCIAL_METRIC": "sum",
    "ACCIDENT": "sum",
    "SCORE": "avg",
    "CONGESTION": "avg",
    "SPEED": "avg",
}


def _title_for(role: str, col: str, domain: str, table: dict) -> str:
    templates = table.get(role, {})
    template = templates.get(domain, templates.get("default", "{col} Distribution"))
    return template.format(col=col)


def _slug(text: str) -> str:
    return text.lower().replace(" ", "_")


def plan_analyses(semantic_roles: dict, domain: str, cardinalities: dict, row_count: int, numeric_cols: set) -> list:
    """
    semantic_roles: {col: {"role": str, ...}} from semantic_roles.classify_columns()
    domain: from domains.detect_domain()["domain"]
    cardinalities: {col: nunique} for every column
    row_count: total row count, used for cardinality sanity checks
    numeric_cols: set of column names that are ACTUALLY numeric dtype — used
        to guard against a name-based role match (e.g. a column literally
        called "Grade" holding letter values 'A'/'B'/'C') being planned as a
        histogram when the underlying data isn't numeric at all.

    Returns a list of analysis specs:
      {"id", "title", "type", "column", "metric_column", "date_column"}
    where type is one of: "trend", "histogram", "distribution_count", "distribution_sum"
    """
    analyses = []

    date_col = next((c for c, info in semantic_roles.items() if info["role"] == "DATE"), None)
    primary_metric_col = None
    primary_metric_role = None
    for role in CANDIDATE_METRIC_ROLES:
        match = next(
            (c for c, info in semantic_roles.items() if info["role"] == role and c in numeric_cols),
            None,
        )
        if match:
            primary_metric_col = match
            primary_metric_role = role
            break
    aggregation = AGGREGATION_BY_ROLE.get(primary_metric_role, "sum")

    def is_chartable_dimension(col):
        n = cardinalities.get(col, 0)
        return 2 <= n <= min(30, max(row_count * 0.5, 2))

    # --- Trend: primary metric over time ---
    if primary_metric_col and date_col:
        analyses.append({
            "id": "trend_" + _slug(primary_metric_col),
            "title": f"{primary_metric_col} Trend",
            "type": "trend",
            "column": date_col,
            "metric_column": primary_metric_col,
            "date_column": date_col,
            "aggregation": aggregation,
        })

    # --- Histogram: primary metric's own distribution (spread, not just total) ---
    if primary_metric_col:
        analyses.append({
            "id": "hist_" + _slug(primary_metric_col),
            "title": f"{primary_metric_col} Distribution",
            "type": "histogram",
            "column": primary_metric_col,
            "metric_column": primary_metric_col,
            "date_column": None,
            "aggregation": aggregation,
        })

    # --- Histograms for other standalone numeric roles (Age, Score, Tenure...) ---
    # Only if the column is ACTUALLY numeric — a name match alone (e.g. a
    # "Grade" column holding letter grades) isn't enough, since that would
    # produce a broken histogram on categorical data.
    for col, info in semantic_roles.items():
        role = info["role"]
        if role not in NUMERIC_SUMMARY_ROLE_TITLES or col == primary_metric_col:
            continue
        if col not in numeric_cols:
            continue  # falls through to the dimension-based handling below instead
        title = _title_for(role, col, domain, NUMERIC_SUMMARY_ROLE_TITLES)
        analyses.append({
            "id": "hist_" + _slug(col),
            "title": title,
            "type": "histogram",
            "column": col,
            "metric_column": col,
            "date_column": None,
            "aggregation": AGGREGATION_BY_ROLE.get(role, "avg"),
        })

    # --- Distributions for every meaningful dimension column ---
    # Count-based is the default (answers "how many have X"), and a
    # sum/avg-based version of the SAME dimension is added alongside it when
    # a primary metric exists (answers "which X costs the most" for money,
    # or "which X scores highest on average" for something like test scores)
    # — the user gets both, rather than the tool guessing which one they
    # meant. Also catches numeric-sounding roles (like "Grade") whose actual
    # data turned out non-numeric, so they still get a sensible analysis
    # instead of being silently dropped.
    for col, info in semantic_roles.items():
        role = info["role"]
        is_dimension_role = role in DIMENSION_ROLE_TITLES
        is_misclassified_numeric = role in NUMERIC_SUMMARY_ROLE_TITLES and col not in numeric_cols
        if not (is_dimension_role or is_misclassified_numeric):
            continue
        if not is_chartable_dimension(col):
            continue

        table = DIMENSION_ROLE_TITLES if is_dimension_role else NUMERIC_SUMMARY_ROLE_TITLES
        title = _title_for(role, col, domain, table)
        analyses.append({
            "id": "count_" + _slug(col),
            "title": title,
            "type": "distribution_count",
            "column": col,
            "metric_column": None,
            "date_column": None,
            "aggregation": None,
        })

        if primary_metric_col and col != primary_metric_col:
            verb = "Average" if aggregation == "avg" else "Total"
            analyses.append({
                "id": "sum_" + _slug(col),
                "title": f"{verb} {primary_metric_col} by {col}",
                "type": "distribution_sum",
                "column": col,
                "metric_column": primary_metric_col,
                "date_column": None,
                "aggregation": aggregation,
            })

    return analyses
