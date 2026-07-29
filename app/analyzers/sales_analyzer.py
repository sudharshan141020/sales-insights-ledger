from app.analyzers.base_analyzer import BaseAnalyzer


class SalesAnalyzer(BaseAnalyzer):
    domain_name = "sales"

    headline_dimension_roles = {"CATEGORY", "LOCATION"}

    key_kpis = [
        "Revenue", "Profit", "Discounts", "Returns", "Customer Lifetime",
        "Products", "Categories", "Regions",
    ]
