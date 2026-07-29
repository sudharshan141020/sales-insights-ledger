"""
Phase B — Story Mode.

Chains the dataset's OWN findings and weak points into a narrative arc.
This is deliberately NOT a new detection engine — it's a narrator that
orders and connects what the Insight Engine and Weak Point Detector already
computed. Every sentence in a story is a real Insight or WeakPoint's own
text; nothing is invented. Staying rule-based means the "story" is really a
templated narrative STRUCTURE (opening -> development -> complication ->
recommendation) applied to whatever findings exist for THIS dataset, not a
free-text generator — which is what keeps it honest and fast, and keeps it
working for a domain that has never been seen before, same as everything
else in this pipeline.
"""
from dataclasses import dataclass


@dataclass
class StoryBeat:
    label: str    # "The Trend" | "The Breakdown" | "The Driver" | "Recommendation"
    text: str
    tone: str      # "neutral" | "warning" | "action"


def _mentions_same_subject(a_text: str, b_column: str) -> bool:
    """Cheap heuristic: does this finding's text reference the same column
    name as the weak point/finding we're trying to connect it to — used to
    prefer beats that plausibly relate to each other over unrelated ones."""
    if not b_column:
        return False
    return b_column.lower() in a_text.lower()


def build_story(findings: list, weak_points: list) -> list:
    """
    findings: list[Insight] from insight_engine
    weak_points: list[WeakPoint] from weak_points detector
    Returns list[StoryBeat], 2-4 beats depending on what's actually available
    — a sparse/clean dataset gets a short story, not a padded one.
    """
    beats = []
    used_findings = set()
    used_weak_points = set()

    # ---- Beat 1: The Trend (opening) ----
    trend_weak = next((w for i, w in enumerate(weak_points) if w.category == "trend" and i not in used_weak_points), None)
    trend_finding = next((f for i, f in enumerate(findings) if f.category == "trend" and i not in used_findings), None)

    opener_subject_col = None
    if trend_weak:
        idx = weak_points.index(trend_weak)
        used_weak_points.add(idx)
        beats.append(StoryBeat(label="The Trend", text=trend_weak.impact, tone="warning"))
    elif trend_finding:
        idx = findings.index(trend_finding)
        used_findings.add(idx)
        beats.append(StoryBeat(label="The Trend", text=trend_finding.text, tone="neutral"))
    elif findings:
        # No trend at all (no date column, or nothing meaningful) — open
        # with the single strongest finding instead so the story isn't empty.
        beats.append(StoryBeat(label="The Headline", text=findings[0].text, tone="neutral"))
        used_findings.add(0)

    if not beats:
        return beats  # genuinely nothing to say — an empty story is honest, not a bug

    # ---- Beat 2: The Breakdown (composition/concentration) ----
    concentration_weak = next(
        (w for i, w in enumerate(weak_points) if w.category == "concentration" and i not in used_weak_points),
        None,
    )
    top_segment_finding = next(
        (f for i, f in enumerate(findings) if f.category == "top_segment" and i not in used_findings),
        None,
    )
    if concentration_weak:
        idx = weak_points.index(concentration_weak)
        used_weak_points.add(idx)
        beats.append(StoryBeat(label="The Breakdown", text=concentration_weak.impact, tone="neutral"))
    elif top_segment_finding:
        idx = findings.index(top_segment_finding)
        used_findings.add(idx)
        beats.append(StoryBeat(label="The Breakdown", text=top_segment_finding.text, tone="neutral"))

    # ---- Beat 3: The Driver (underlying risk — margin/discount/outlier/data quality) ----
    driver_categories = ("underperformance", "outlier", "data_quality")
    driver = next(
        (w for i, w in enumerate(weak_points) if w.category in driver_categories and i not in used_weak_points),
        None,
    )
    if driver:
        idx = weak_points.index(driver)
        used_weak_points.add(idx)
        beats.append(StoryBeat(label="The Driver", text=driver.impact, tone="warning"))

    # ---- Beat 4: Recommendation ----
    # Prefer the driver's own action; otherwise fall back to the highest
    # remaining weak point's action, or the trend weak point's action if
    # nothing else was used.
    action_source = driver
    if not action_source:
        action_source = next((w for i, w in enumerate(weak_points) if i not in used_weak_points), None) or trend_weak

    if action_source:
        beats.append(StoryBeat(label="Recommendation", text=action_source.suggested_action, tone="action"))

    return beats
