from datetime import date
from decimal import Decimal
from types import SimpleNamespace
import unittest

from backend.app.services.budget_service import BudgetService


class BudgetServiceTests(unittest.TestCase):
    def budget(self, amount=1000, threshold=80, category="__overall__"):
        return SimpleNamespace(
            id=1,
            year_month="2026-09",
            category=category,
            amount=Decimal(str(amount)),
            warning_threshold=Decimal(str(threshold)),
        )

    def test_month_range_handles_month_end(self):
        self.assertEqual(
            BudgetService.month_range("2024-02"),
            (date(2024, 2, 1), date(2024, 2, 29)),
        )

    def test_safe_warning_and_exceeded_statuses(self):
        self.assertEqual(BudgetService.serialize(self.budget(), 500)["status"], "safe")
        self.assertEqual(BudgetService.serialize(self.budget(), 800)["status"], "warning")
        exceeded = BudgetService.serialize(self.budget(), 1100)
        self.assertEqual(exceeded["status"], "exceeded")
        self.assertEqual(exceeded["remaining"], -100.0)

    def test_empty_category_means_overall_budget(self):
        self.assertEqual(BudgetService.normalize_category("  "), "__overall__")
        self.assertEqual(BudgetService.normalize_category(" Shop Rent "), "Shop Rent")


if __name__ == "__main__":
    unittest.main()
