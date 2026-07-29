from app.analyzers.base_analyzer import BaseAnalyzer


class TrafficAnalyzer(BaseAnalyzer):
    domain_name = "traffic"

    headline_dimension_roles = {"VEHICLE", "LOCATION"}

    key_kpis = ["Congestion", "Vehicle Types", "Accidents", "Peak Hours", "Speed"]
