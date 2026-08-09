from app.analyzers.base_analyzer import BaseAnalyzer


class RetailAnalyzer(BaseAnalyzer):
    domain_name = "retail"

    # Store and product-category breakdowns are the two headline views for
    # a retail dataset -- distinct from "sales" (which headlines CATEGORY +
    # LOCATION, a more general geographic split). Retail is specifically
    # about inventory and store-level performance, not just transactions.
    headline_dimension_roles = {"CATEGORY", "STORE"}

    key_kpis = [
        "Revenue", "Inventory Level", "Reorder Point", "Stock Turnover",
        "Supplier Performance", "Store Performance", "Products", "Categories",
    ]
