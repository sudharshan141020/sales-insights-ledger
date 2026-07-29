from app.analyzers.base_analyzer import BaseAnalyzer


class HRAnalyzer(BaseAnalyzer):
    domain_name = "hr"

    headline_dimension_roles = {"DEPARTMENT"}

    key_kpis = ["Attrition", "Departments", "Experience", "Salary", "Performance"]
