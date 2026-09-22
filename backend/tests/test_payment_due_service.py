from datetime import date
from decimal import Decimal
from types import SimpleNamespace
import unittest

from backend.app.services.payment_due_service import (
    PaymentDueService,
    calculate_payment_fields,
    due_direction,
)


class PaymentDueServiceTests(unittest.TestCase):
    def test_omitted_payment_defaults_to_fully_paid(self) -> None:
        paid, due, due_date = calculate_payment_fields(1000, None, None)
        self.assertEqual(paid, Decimal("1000.00"))
        self.assertEqual(due, Decimal("0.00"))
        self.assertIsNone(due_date)

    def test_partial_payment_calculates_due(self) -> None:
        deadline = date(2026, 9, 30)
        paid, due, due_date = calculate_payment_fields(1000, 400, deadline)
        self.assertEqual(paid, Decimal("400.00"))
        self.assertEqual(due, Decimal("600.00"))
        self.assertEqual(due_date, deadline)

    def test_outstanding_amount_requires_due_date(self) -> None:
        with self.assertRaisesRegex(ValueError, "due date"):
            calculate_payment_fields(1000, 400, None)

    def test_overpayment_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "cannot exceed"):
            calculate_payment_fields(1000, 1200, date(2026, 9, 30))

    def test_due_direction(self) -> None:
        self.assertEqual(due_direction("sales"), "receivable")
        self.assertEqual(due_direction("purchase"), "payable")

    def test_record_payment_can_settle_due(self) -> None:
        transaction = SimpleNamespace(
            amount=Decimal("1000.00"),
            amount_paid=Decimal("400.00"),
            amount_due=Decimal("600.00"),
            due_date=date(2026, 9, 30),
        )
        PaymentDueService.record_payment(transaction, 600)
        self.assertEqual(transaction.amount_paid, Decimal("1000.00"))
        self.assertEqual(transaction.amount_due, Decimal("0.00"))
        self.assertIsNone(transaction.due_date)


if __name__ == "__main__":
    unittest.main()
