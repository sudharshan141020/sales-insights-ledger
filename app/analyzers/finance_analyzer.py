from app.analyzers.base_analyzer import BaseAnalyzer


class FinanceAnalyzer(BaseAnalyzer):
    domain_name = "finance"

    headline_dimension_roles = set()  # no dimension role clearly dominates finance data generically

    key_kpis = ["Cashflow", "Expenses", "Income", "Profit", "Loss", "Investments"]
