import io
from typing import Optional
import pandas as pd
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.column_detector import detect_columns
from app.kpi import prepare, compute_kpis, timeseries_monthly, breakdown_by, all_breakdowns, combine_dataframes
from app.insights import generate_insights
from app.semantic_roles import classify_columns
from app.domains import detect_domain
from app.planner import plan_analyses
from app.executor import execute_all
from app.understanding import understand_dataset
from app.executor_v2 import execute_all as execute_all_v2
from app.analyzers.registry import get_analyzer
from app.data_quality import analyze_data_quality
from app.correlation_center import analyze_correlations

app = FastAPI(title="DataLens")

STATIC_DIR = Path(__file__).parent / "static"

ALLOWED_EXTENSIONS = {".csv", ".tsv", ".xlsx", ".xls"}


def _serialize_correlation_pair(pair) -> Optional[dict]:
    """Shared serializer for CorrelationPair so the significance fields
    (n, p_value, significant, strength, caveat) stay consistent between the
    full pairs list and the strongest-positive/negative callouts."""
    if pair is None:
        return None
    return {
        "col1": pair.col1,
        "col2": pair.col2,
        "r": round(pair.r, 3),
        "n": pair.n,
        "p_value": round(pair.p_value, 4) if pair.p_value is not None else None,
        "significant": pair.significant,
        "strength": pair.strength,
        "caveat": pair.caveat,
    }


def _run_v2_pipeline(df: pd.DataFrame) -> dict:
    """
    The full new pipeline: Dataset Understanding -> pick the right domain
    Analyzer plugin -> that plugin's dashboard/findings/weak-points. This
    function no longer knows what "healthcare" or "sales" means at all —
    get_analyzer() picks the right plugin, and every domain-specific
    decision (which dimensions matter most, what KPIs this domain cares
    about) lives inside that plugin, not here.
    """
    profile = understand_dataset(df)

    df_exec = df.copy()
    for col, role in profile.semantic_roles.items():
        if role == "DATE":
            df_exec[col] = pd.to_datetime(df_exec[col], errors="coerce")

    analyzer = get_analyzer(profile.domain, df_exec, profile)

    specs = analyzer.choose_visualizations()
    top3 = analyzer.choose_dashboard(n=3)
    top3_ids = {s.id for s in top3}

    all_executed = execute_all_v2(df_exec, specs)
    top_order = {s.id: i for i, s in enumerate(top3)}
    top_executed = sorted(
        (a for a in all_executed if a["id"] in top3_ids),
        key=lambda a: top_order.get(a["id"], 999),
    )

    insights = analyzer.generate_findings()
    weak_points = analyzer.detect_weak_points()
    story = analyzer.generate_story()
    quality_report = analyze_data_quality(df_exec, profile)
    correlation_report = analyze_correlations(df_exec, profile)

    return {
        "profile": {
            "domain": profile.domain,
            "domain_confidence": profile.domain_confidence,
            "primary_entity": profile.primary_entity,
            "row_count": profile.row_count,
            "column_count": profile.column_count,
            "data_completeness_pct": profile.data_completeness_pct,
            "key_kpis": analyzer.key_kpis,
        },
        "top_analyses": top_executed,
        "all_analyses": all_executed,
        "findings": [
            {"text": i.text, "category": i.category, "score": i.score}
            for i in insights
        ],
        "weak_points": [
            {
                "problem": w.problem, "impact": w.impact, "priority": w.priority,
                "suggested_action": w.suggested_action, "category": w.category,
            }
            for w in weak_points
        ],
        "story": [
            {"label": b.label, "text": b.text, "tone": b.tone}
            for b in story
        ],
        "data_quality": {
            "missing_by_column": quality_report.missing_by_column,
            "duplicate_row_count": quality_report.duplicate_row_count,
            "duplicate_row_pct": quality_report.duplicate_row_pct,
            "constant_columns": quality_report.constant_columns,
            "high_cardinality_columns": quality_report.high_cardinality_columns,
            "outlier_summary": quality_report.outlier_summary,
            "dtype_breakdown": quality_report.dtype_breakdown,
            "overall_quality_score": quality_report.overall_quality_score,
        },
        "correlation_center": {
            "pairs": [_serialize_correlation_pair(p) for p in correlation_report["pairs"]],
            "strongest_positive": _serialize_correlation_pair(correlation_report["strongest_positive"]),
            "strongest_negative": _serialize_correlation_pair(correlation_report["strongest_negative"]),
        },
    }


def _semantic_layer(df: pd.DataFrame) -> dict:
    """
    Runs the domain-aware pipeline (Phases 1-4: semantic classification,
    domain detection, analysis planning, execution) and returns domain info
    plus the dynamic analyses list. This is ADDITIVE to the existing
    KPI/insights pipeline below, not a replacement — the existing pipeline
    already works well for sales-shaped data (profit margin, discount risk,
    customer concentration) and there's no reason to risk regressing it
    while this newer, more general layer is still maturing.
    """
    semantic_roles = classify_columns(df)
    domain_result = detect_domain(semantic_roles)
    cardinalities = {c: int(df[c].nunique()) for c in df.columns}
    numeric_cols = set(df.select_dtypes(include="number").columns)

    df_exec = df.copy()
    for col, info in semantic_roles.items():
        if info["role"] == "DATE":
            df_exec[col] = pd.to_datetime(df_exec[col], errors="coerce")

    specs = plan_analyses(semantic_roles, domain_result["domain"], cardinalities, len(df), numeric_cols)
    analyses = execute_all(df_exec, specs)

    return {
        "domain": domain_result["domain"],
        "domain_confidence": domain_result["confidence"],
        "semantic_roles": {c: info["role"] for c, info in semantic_roles.items()},
        "analyses": analyses,
    }


def _load_dataframe(filename: str, raw: bytes) -> pd.DataFrame:
    ext = Path(filename).suffix.lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            400,
            f"Unsupported file type '{ext}'. Upload a .csv, .tsv, .xlsx, or .xls file.",
        )

    if ext in (".xlsx", ".xls"):
        try:
            return pd.read_excel(io.BytesIO(raw))
        except Exception as e:
            raise HTTPException(400, f"Couldn't read the Excel file: {e}")

    sep = "\t" if ext == ".tsv" else ","
    last_error = None
    for encoding in ("utf-8", "utf-8-sig", "latin1", "cp1252"):
        try:
            return pd.read_csv(io.BytesIO(raw), sep=sep, encoding=encoding)
        except Exception as e:
            last_error = e
            continue
    raise HTTPException(400, f"Couldn't parse the file: {last_error}")


def _analyze_df(df: pd.DataFrame, mapping: dict, confidence: dict, unmapped: list, extra_categoricals: list) -> dict:
    df_prepared = prepare(df, mapping)
    response = {
        "detected_columns": mapping,
        "detection_confidence": confidence,
        "unmapped_columns": unmapped,
        "kpis": compute_kpis(df_prepared, mapping),
        "monthly_trend": timeseries_monthly(df_prepared, mapping),
        "breakdowns": all_breakdowns(df_prepared, mapping, extra_categoricals),
        "insights": generate_insights(df_prepared, mapping, extra_categoricals),
    }
    response.update(_semantic_layer(df))
    response["v2"] = _run_v2_pipeline(df)
    return response


def _categorical_only_analysis(df: pd.DataFrame, detection: dict) -> dict:
    """
    Fallback for files with no usable numeric metric at all (e.g. a roster of
    names/categories, plain text data). Rather than failing outright, still
    return row/column counts and frequency breakdowns of the categorical
    columns — genuinely useful, just without revenue-style KPIs or charts
    that don't apply to this kind of data.
    """
    row_count = int(len(df))
    col_count = int(len(df.columns))
    missing_frac = df.isnull().mean().mean() if col_count else 0
    completeness = float(round((1 - missing_frac) * 100, 1))

    insight_text = (
        f"This file has {row_count} rows and {col_count} columns but no clear "
        f"numeric metric (like a sales amount, price, or score column) to "
        f"analyze trends or KPIs against."
    )

    response = {
        "detected_columns": detection["mapping"],
        "detection_confidence": detection["confidence"],
        "unmapped_columns": detection["unmapped"],
        "kpis": {
            "row_count": row_count,
            "column_count": col_count,
            "data_completeness_pct": completeness,
        },
        "monthly_trend": [],
        "breakdowns": [],
        "insights": [{
            "text": insight_text,
            "recommendation": (
                "If there is a numeric column meant to be the main metric, try "
                "renaming it to something like 'Amount', 'Value', or 'Score' so "
                "it gets picked up automatically."
            ),
            "score": 1,
            "type": "data_quality",
        }],
        "no_numeric_metric": True,
    }
    response.update(_semantic_layer(df))
    response["v2"] = _run_v2_pipeline(df)
    return response


def _load_and_detect(filename: str, raw: bytes):
    """Returns (df_prepared, mapping) or raises HTTPException."""
    df = _load_dataframe(filename, raw)
    if df.empty:
        raise HTTPException(400, f"{filename} has no rows.")

    detection = detect_columns(df)
    mapping = detection["mapping"]
    if "revenue" not in mapping:
        raise HTTPException(
            422,
            f"{filename}: has no numeric column to use as the primary metric, "
            "so it can't be combined with other files. Try analyzing it on its own instead.",
        )
    df_prepared = prepare(df, mapping)
    return df_prepared, mapping


@app.post("/api/analyze")
async def analyze(file: UploadFile = File(...)):
    raw = await file.read()
    df = _load_dataframe(file.filename, raw)

    if df.empty:
        raise HTTPException(400, "The uploaded file has no rows.")

    detection = detect_columns(df)
    mapping = detection["mapping"]

    if "revenue" not in mapping:
        # No usable numeric metric anywhere in the file — don't fail, fall
        # back to a categorical/overview-only analysis instead.
        return _categorical_only_analysis(df, detection)

    return _analyze_df(df, mapping, detection["confidence"], detection["unmapped"], detection["extra_categoricals"])


@app.post("/api/analyze-combined")
async def analyze_combined(files: list[UploadFile] = File(...)):
    if len(files) < 2:
        raise HTTPException(400, "Select at least two files to combine.")

    prepared_with_mappings = []
    source_names = []
    for f in files:
        raw = await f.read()
        df_prepared, mapping = _load_and_detect(f.filename, raw)
        prepared_with_mappings.append((df_prepared, mapping))
        source_names.append(f.filename)

    combined_df, combined_mapping = combine_dataframes(prepared_with_mappings, source_names)

    # combined_mapping is role->role (already canonical), so every role in it
    # is "combined" confidence, not name-matched or inferred from a single file
    confidence = {role: "combined" for role in combined_mapping}

    result = {
        "detected_columns": combined_mapping,
        "detection_confidence": confidence,
        "unmapped_columns": [],
        "kpis": compute_kpis(combined_df, combined_mapping),
        "monthly_trend": timeseries_monthly(combined_df, combined_mapping),
        "breakdowns": all_breakdowns(combined_df, combined_mapping, []),
        "insights": generate_insights(combined_df, combined_mapping),
        "source_files": source_names,
    }
    result.update(_semantic_layer(combined_df))
    result["v2"] = _run_v2_pipeline(combined_df)
    return result


@app.get("/api/health")
def health():
    return {"status": "ok"}


# ---- Serve the built frontend (if present) ----
if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # Any non-API path returns the SPA's index.html; the React app handles the rest.
        candidate = STATIC_DIR / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(STATIC_DIR / "index.html")
