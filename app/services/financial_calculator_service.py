from __future__ import annotations

import math
import re
from typing import Any


class FinancialCalculatorService:
    SUPPORTED_OPERATIONS = {
        "gst_amount",
        "total_with_gst",
        "base_from_gross",
        "profit",
        "loss",
        "margin_percent",
    }

    @staticmethod
    def _to_number(value: Any, field_name: str) -> float:
        if value is None:
            raise ValueError(f"{field_name} is required.")
        number = float(value)
        if not math.isfinite(number):
            raise ValueError(f"{field_name} must be a finite number.")
        return number

    @staticmethod
    def _round(value: float) -> float:
        return round(value + 1e-9, 2)

    def calculate(
        self,
        *,
        operation: str,
        amount: Any = None,
        rate_percent: Any = None,
        revenue: Any = None,
        cost: Any = None,
    ) -> dict[str, Any]:
        if operation not in self.SUPPORTED_OPERATIONS:
            raise ValueError("Unsupported financial operation.")

        if operation in {"gst_amount", "total_with_gst", "base_from_gross"}:
            amount_value = self._to_number(amount, "amount")
            rate_value = self._to_number(rate_percent, "rate_percent")
            if rate_value < 0 or rate_value > 100:
                raise ValueError("GST rate must be between 0 and 100.")

            gst_amount = amount_value * rate_value / 100
            if operation == "gst_amount":
                value = self._round(gst_amount)
                return {"operation": operation, "value": value, "message": f"GST on Rs. {amount_value:,.2f} at {rate_value:.2f}% is Rs. {value:,.2f}."}
            if operation == "total_with_gst":
                value = self._round(amount_value + gst_amount)
                gst_value = self._round(gst_amount)
                return {
                    "operation": operation,
                    "value": value,
                    "gst_amount": gst_value,
                    "message": f"GST: Rs. {gst_value:,.2f}. Total including GST: Rs. {value:,.2f}.",
                }
            divisor = 1 + rate_value / 100
            if divisor == 0:
                raise ValueError("Cannot divide by zero.")
            value = self._round(amount_value / divisor)
            return {"operation": operation, "value": value, "message": f"Base amount from gross Rs. {amount_value:,.2f} at {rate_value:.2f}% GST is Rs. {value:,.2f}."}

        revenue_value = self._to_number(revenue, "revenue")
        cost_value = self._to_number(cost, "cost")
        if operation == "profit":
            value = self._round(revenue_value - cost_value)
            return {"operation": operation, "value": value, "message": f"Profit is Rs. {value:,.2f}."}
        if operation == "loss":
            value = self._round(max(cost_value - revenue_value, 0))
            return {"operation": operation, "value": value, "message": f"Loss is Rs. {value:,.2f}."}
        if revenue_value == 0:
            raise ValueError("Revenue must be non-zero for margin_percent.")
        value = self._round(((revenue_value - cost_value) / revenue_value) * 100)
        return {"operation": operation, "value": value, "message": f"Margin is {value:,.2f}%."}

    def parse_query_text(self, query_text: str) -> dict[str, Any] | None:
        lower = (query_text or "").lower()
        if not lower:
            return None

        amount_match = re.search(r"(?:rs\.?|inr)?\s*([0-9]+(?:\.[0-9]+)?)", lower)
        rate_match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*%", lower)
        if "gst" in lower and amount_match and rate_match:
            operation = "gst_amount"
            if any(term in lower for term in ("total", "including", "with gst")):
                operation = "total_with_gst"
            return {
                "operation": operation,
                "amount": float(amount_match.group(1)),
                "rate_percent": float(rate_match.group(1)),
            }

        revenue_match = re.search(r"revenue\s*(?:is|=)?\s*([0-9]+(?:\.[0-9]+)?)", lower)
        cost_match = re.search(r"cost\s*(?:is|=)?\s*([0-9]+(?:\.[0-9]+)?)", lower)
        if revenue_match and cost_match:
            revenue = float(revenue_match.group(1))
            cost = float(cost_match.group(1))
            if "margin" in lower:
                operation = "margin_percent"
            elif "loss" in lower:
                operation = "loss"
            else:
                operation = "profit"
            return {"operation": operation, "revenue": revenue, "cost": cost}

        return None
