from app.analyzers.base_analyzer import BaseAnalyzer


class HealthcareAnalyzer(BaseAnalyzer):
    domain_name = "healthcare"

    headline_dimension_roles = {"CONDITION", "ADMISSION_TYPE"}

    key_kpis = [
        "Disease Frequency", "Age Distribution", "Length of Stay",
        "Admission Types", "Medication Usage", "Insurance Distribution",
        "Hospital Comparison", "Doctor Workload", "Blood Type", "Test Results",
    ]
