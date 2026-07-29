"""
Plugin architecture for domain-specific analysis.

BaseAnalyzer defines the interface every domain plugin implements. Its
default method bodies are NOT stubs — they call the shared, domain-agnostic
engines (analysis_planner, insight_engine, weak_points) using this class's
own configuration (headline_dimension_roles, key_kpis). That's what makes
this "plugin architecture" rather than just "a class per domain that
reimplements everything": a new domain (e.g. Retail) that behaves just like
the generic fallback but with different headline dimensions only needs to
override two class attributes — no method bodies at all.

Adding a genuinely new domain later means creating one new file in this
folder and registering it in registry.py — nothing in analysis_planner.py,
insight_engine.py, or weak_points.py needs to change.
"""
from app.analysis_planner import plan_analyses, top_n as top_n_analyses
from app.insight_engine import generate_insights
from app.weak_points import generate_weak_points
from app.story_engine import build_story


class BaseAnalyzer:
    domain_name = "generic"

    # Semantic roles that matter MOST for this domain — used to boost an
    # analysis's importance ranking so the dashboard's top-3 reflects what
    # actually matters here, not just whatever has the highest raw score.
    headline_dimension_roles = set()

    # Domain Knowledge Library: the KPI concepts this domain cares about,
    # independent of whether the current dataset happens to have columns
    # for all of them. Used for the Dataset Profile display and as a hook
    # for future phases (chart reasoning, story mode) to reference by name.
    key_kpis = []

    def __init__(self, df, profile):
        self.df = df
        self.profile = profile

    # ---- Plugin interface ----

    def detect_priority_metrics(self):
        """Measures ranked by relevance to this domain. Default: the
        profile's measures as-is (already ordered with primary first)."""
        return self.profile.measures

    def detect_priority_dimensions(self):
        """Dimensions ranked by relevance to this domain — headline roles first."""
        dims = self.profile.dimensions
        return sorted(dims, key=lambda d: d.role not in self.headline_dimension_roles)

    def choose_visualizations(self):
        """Every planned analysis for this dataset, with chart types assigned."""
        return plan_analyses(self.profile, headline_roles=self.headline_dimension_roles)

    def choose_dashboard(self, n=3):
        """The N most important analyses for the Executive Dashboard."""
        return top_n_analyses(self.choose_visualizations(), n=n)

    def generate_findings(self):
        return generate_insights(self.df, self.profile)

    def detect_weak_points(self):
        return generate_weak_points(self.df, self.profile)

    def generate_recommendations(self):
        """Currently, recommendations live as `suggested_action` on each
        WeakPoint rather than as a separate list — this method exposes them
        as their own collection for callers that want recommendations
        without the full weak-point detail (e.g. a future report export)."""
        return [
            {"problem": w.problem, "recommendation": w.suggested_action, "priority": w.priority}
            for w in self.detect_weak_points()
        ]

    def generate_story(self):
        """Chains this dataset's own findings and weak points into a
        narrative arc (Story Mode) — see app/story_engine.py."""
        return build_story(self.generate_findings(), self.detect_weak_points())
