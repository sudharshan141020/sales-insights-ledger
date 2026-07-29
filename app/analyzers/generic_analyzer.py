from app.analyzers.base_analyzer import BaseAnalyzer


class GenericAnalyzer(BaseAnalyzer):
    """
    The universal fallback (spec item #23: "the application should NEVER
    fail because it encounters an unfamiliar dataset"). No headline
    dimensions to boost — every chartable dimension is treated equally,
    and analysis still runs entirely off the generic statistical engines
    (trend, distribution, correlation, outlier, missing data).
    """
    domain_name = "generic"
    headline_dimension_roles = set()
    key_kpis = []
