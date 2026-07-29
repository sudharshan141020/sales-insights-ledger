from app.analyzers.base_analyzer import BaseAnalyzer


class EducationAnalyzer(BaseAnalyzer):
    domain_name = "education"

    headline_dimension_roles = {"SUBJECT"}

    key_kpis = ["Attendance", "Grades", "Subjects", "Performance", "Pass Rate"]
