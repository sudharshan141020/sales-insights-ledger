"""
Phase 1 — Semantic column classifier.

Assigns each column a fine-grained SEMANTIC role based on name keyword
matching, with a dtype/cardinality-based fallback for columns whose names
don't match anything known. This module is intentionally domain-agnostic —
it has no concept of "sales" or "healthcare." That inference happens one
layer up, in the domain detector (Phase 2), which consumes these roles as
its only input.

Extending to a new domain later should only ever mean adding new keyword
entries to ROLE_KEYWORDS below — never touching the classification logic
in classify_columns().
"""
import re
import pandas as pd

# Each semantic role maps to a list of name keywords, most-specific first.
# Order matters for tie-breaking, and duplicate keywords across roles are
# fine — the exact-match pass always wins over substring matches, and roles
# are tried in the order they're declared here.
ROLE_KEYWORDS = {
    # --- Financial / transactional ---
    "FINANCIAL_METRIC": [
        "sales", "revenue", "total_amount", "amount", "price", "cost", "fare",
        "income", "salary", "budget", "expense", "billing_amount", "billing",
        "payment", "fee", "gross_sales", "net_amount", "order_value", "balance",
        "transaction_amount",
    ],
    "PROFIT": ["profit", "margin", "net_income", "net_profit"],
    "DISCOUNT": ["discount", "coupon", "promo_code", "promo"],
    "QUANTITY": ["quantity", "qty", "units", "stock", "item_count"],

    # --- Time ---
    "DATE": [
        "order_date", "admission_date", "discharge_date", "enrolled_date",
        "date_of_admission", "date_of_birth", "dob", "date", "time",
        "timestamp", "created_at", "created", "day", "month", "year",
    ],

    # --- People / entities (checked before generic NAME/CATEGORY) ---
    "PATIENT": ["patient_id", "patient_name", "patient"],
    "STUDENT": ["student_id", "student_name", "student"],
    "EMPLOYEE": ["employee_id", "employee_name", "employee", "staff_id", "staff"],
    "CUSTOMER": ["customer_id", "customer_name", "customer", "client", "buyer", "account_name"],
    "DOCTOR": ["doctor", "physician", "attending"],
    "TEACHER": ["teacher", "instructor", "professor"],
    "NURSE": ["nurse"],
    "DRIVER": ["driver_id", "driver_name", "driver"],

    # --- Products / items ---
    "PRODUCT": ["product_name", "product_id", "product", "item_name", "item", "sku"],

    # --- Location ---
    "LOCATION": [
        "region", "state", "city", "country", "territory", "zone", "address",
        "route", "road", "postal_code", "zip_code", "location",
    ],

    # --- Demographics ---
    "AGE": ["age"],
    "GENDER": ["gender", "sex"],
    "DEMOGRAPHIC": ["blood_type", "race", "ethnicity", "marital_status"],

    # --- Healthcare-specific ---
    "CONDITION": ["medical_condition", "condition", "disease", "diagnosis", "illness", "symptom"],
    "HOSPITAL": ["hospital", "clinic", "facility"],
    "INSURANCE": ["insurance_provider", "insurance", "provider", "policy", "health_plan"],
    "MEDICATION": ["medication", "drug", "prescription", "dosage"],
    "TEST_RESULT": ["test_result", "test_results", "lab_result", "outcome"],
    "ADMISSION_TYPE": ["admission_type", "admit_type"],
    "ROOM": ["room_number", "room", "ward", "bed_number", "bed"],
    "LENGTH_OF_STAY": ["length_of_stay", "stay_duration", "los"],

    # --- Education-specific ---
    "SUBJECT": ["subject", "course_name", "course"],
    "SCORE": ["score", "marks", "grade", "gpa", "percentage"],
    "ATTENDANCE": ["attendance_rate", "attendance"],

    # --- HR-specific ---
    "DEPARTMENT": ["department", "division", "team"],
    "JOB_TITLE": ["job_title", "position", "designation", "role_title"],
    "TENURE": ["tenure", "years_of_service", "years_employed"],

    # --- Finance-specific ---
    "ACCOUNT": ["account_number", "account_id", "account"],
    "INTEREST_RATE": ["interest_rate", "apr"],
    "LOAN": ["loan_amount", "loan_id", "loan"],

    # --- Traffic-specific ---
    "VEHICLE": ["vehicle_type", "vehicle_id", "vehicle", "car_type"],
    "ACCIDENT": ["accident", "collision", "crash"],
    "CONGESTION": ["congestion", "traffic_flow", "delay_minutes", "delay"],
    "SPEED": ["speed", "velocity"],

    # --- Generic categorical (checked late — very common words) ---
    "CATEGORY": ["category", "segment", "product_type", "sub_category", "type", "class", "status"],

    # --- Identifiers (checked late, name-based only) ---
    "IDENTIFIER": ["id", "code", "ticket_number", "ticket", "key", "index", "row_id"],
    "NAME": ["name", "full_name"],

    "TEXT": ["description", "comment", "notes", "remarks", "review"],
}


def _normalize(col: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", col.strip().lower()).strip("_")


def _keyword_matches(columns: list) -> dict:
    """
    Two-pass matcher across ALL columns at once: exact normalized-name
    matches first (so a column literally called 'Age' always wins), then
    substring matches for anything left unmatched. A column can only be
    claimed by one role.
    """
    norm_cols = {c: _normalize(c) for c in columns}
    assigned = {}
    claimed = set()

    # Pass 1: exact matches
    for role, keywords in ROLE_KEYWORDS.items():
        for kw in keywords:
            kw_norm = _normalize(kw)
            match = next((c for c in columns if c not in claimed and norm_cols[c] == kw_norm), None)
            if match:
                assigned[match] = {"role": role, "confidence": "name", "matched_keyword": kw}
                claimed.add(match)

    # Pass 2: substring matches (longest keyword wins per column)
    for role, keywords in ROLE_KEYWORDS.items():
        for kw in keywords:
            kw_norm = _normalize(kw)
            for c in columns:
                if c in claimed:
                    continue
                if kw_norm in norm_cols[c]:
                    existing = assigned.get(c)
                    if not existing or len(kw_norm) > len(existing.get("matched_keyword", "")):
                        assigned[c] = {"role": role, "confidence": "name", "matched_keyword": kw}

    for c in columns:
        if c in assigned:
            claimed.add(c)

    return assigned, claimed


def _dtype_fallback(series: pd.Series) -> str:
    """Best-effort role for a column no keyword matched, based on its data."""
    non_null = series.dropna()
    if non_null.empty:
        return "TEXT"

    # date-parseable text
    if pd.api.types.is_string_dtype(series) or series.dtype == object or "datetime" in str(series.dtype):
        try:
            parsed = pd.to_datetime(non_null, errors="coerce")
            if parsed.notna().mean() > 0.9:
                return "DATE"
        except Exception:
            pass

    if pd.api.types.is_numeric_dtype(series):
        vals = non_null.astype(float)
        uniq_ratio = non_null.nunique() / max(len(non_null), 1)
        is_all_int = (vals == vals.round()).all()

        if is_all_int and uniq_ratio > 0.9 and len(non_null) > 10:
            sorted_vals = vals.sort_values().reset_index(drop=True)
            looks_sequential = (sorted_vals.diff().dropna() == 1).mean() > 0.9 if len(sorted_vals) > 1 else False
            if looks_sequential or uniq_ratio > 0.98:
                return "IDENTIFIER"

        if non_null.nunique() <= 2:
            return "CATEGORY"  # binary flag, e.g. survived 0/1

        if is_all_int and vals.min() >= 0 and vals.max() <= 1000 and vals.nunique() < 50:
            return "QUANTITY"

        return "GENERIC_NUMERIC"

    if pd.api.types.is_string_dtype(series) or series.dtype == object:
        uniq_ratio = non_null.nunique() / max(len(non_null), 1)
        if uniq_ratio < 0.5:
            return "CATEGORY"
        if uniq_ratio > 0.8:
            return "IDENTIFIER"

    return "TEXT"


def classify_columns(df: pd.DataFrame) -> dict:
    """
    Returns {column_name: {"role": str, "confidence": "name"|"inferred", "matched_keyword": str|None}}
    for every column in df.
    """
    columns = list(df.columns)
    assigned, claimed = _keyword_matches(columns)

    result = dict(assigned)
    for c in columns:
        if c not in result:
            role = _dtype_fallback(df[c])
            result[c] = {"role": role, "confidence": "inferred", "matched_keyword": None}

    return result
