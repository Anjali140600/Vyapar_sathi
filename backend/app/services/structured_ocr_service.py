"""Optional LLM enhancement layered safely over the existing OCR parser."""

import logging
import re
from datetime import datetime
from typing import Callable

from python_services.llm.model_client import ModelClient


logger = logging.getLogger(__name__)


class StructuredOCRService:
    """Enhance regex OCR data while always preserving a usable fallback."""

    def __init__(self, model_factory: Callable[[], ModelClient] = ModelClient):
        self.model_factory = model_factory
        self._model: ModelClient | None = None

    def enhance(self, regex_result: dict) -> dict:
        fallback = dict(regex_result or {})
        fallback.update(
            {
                "llm_enhanced": False,
                "extraction_source": "regex",
                "fallback_used": True,
            }
        )

        raw_text = str(fallback.get("raw_text") or "").strip()
        if not raw_text:
            fallback["fallback_reason"] = "No OCR text was available for enhancement."
            return fallback

        try:
            model = self._get_model()
            extracted = model.generate_json(self._build_prompt(raw_text))
            if not extracted:
                fallback["fallback_reason"] = "The model did not return valid JSON."
                return fallback

            validated = self._validate(extracted)
            if not any(value is not None for value in validated.values()):
                fallback["fallback_reason"] = "The model returned no usable invoice fields."
                return fallback

            merged = dict(fallback)
            for key, value in validated.items():
                if value is not None:
                    merged[key] = value

            merged.update(
                {
                    "llm_enhanced": True,
                    "extraction_source": "ocr+llm",
                    "fallback_used": False,
                }
            )
            merged.pop("fallback_reason", None)
            return merged
        except Exception as exc:
            logger.warning("Structured OCR enhancement unavailable; using regex fallback: %s", exc)
            fallback["fallback_reason"] = "LLM enhancement was unavailable."
            return fallback

    def _get_model(self) -> ModelClient:
        if self._model is None:
            self._model = self.model_factory()
        return self._model

    @staticmethod
    def _build_prompt(raw_text: str) -> str:
        return f"""
You extract accounting data from Indian bills and invoices.

Return ONLY one valid JSON object with exactly these keys:
vendor, invoice_number, date, amount, taxable_amount, gst_amount,
gstin, category, type.

Rules:
- Use null when a value is not present; never guess.
- amount is the final payable grand total, including tax.
- gst_amount is total GST; add CGST and SGST when both are shown.
- date must use YYYY-MM-DD when it can be determined.
- type must be either "expense" for a purchase/bill or "income" for a sale.
- Keep vendor and category short.
- Do not include markdown or explanation.

OCR text:
{raw_text[:12000]}
"""

    @classmethod
    def _validate(cls, payload: dict) -> dict:
        amount = cls._number(payload.get("amount"))
        taxable_amount = cls._number(payload.get("taxable_amount"))
        gst_amount = cls._number(payload.get("gst_amount"))

        if amount is not None and amount <= 0:
            amount = None
        if taxable_amount is not None and taxable_amount < 0:
            taxable_amount = None
        if gst_amount is not None and gst_amount < 0:
            gst_amount = None
        if amount is not None and gst_amount is not None and gst_amount > amount:
            gst_amount = None

        transaction_type = str(payload.get("type") or "").strip().lower()
        if transaction_type not in {"income", "expense"}:
            transaction_type = None

        return {
            "vendor": cls._short_text(payload.get("vendor"), 150),
            "invoice_number": cls._short_text(payload.get("invoice_number"), 80),
            "date": cls._date(payload.get("date")),
            "amount": amount,
            "taxable_amount": taxable_amount,
            "gst_amount": gst_amount,
            "gstin": cls._gstin(payload.get("gstin")),
            "category": cls._short_text(payload.get("category"), 80),
            "type": transaction_type,
        }

    @staticmethod
    def _number(value) -> float | None:
        if value in (None, "") or isinstance(value, bool):
            return None
        try:
            clean = re.sub(r"[^0-9.\-]", "", str(value).replace(",", ""))
            return round(float(clean), 2) if clean else None
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _short_text(value, max_length: int) -> str | None:
        clean = " ".join(str(value or "").split()).strip()
        return clean[:max_length] if clean else None

    @staticmethod
    def _date(value) -> str | None:
        clean = str(value or "").strip()
        if not clean:
            return None
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(clean, fmt).date().isoformat()
            except ValueError:
                continue
        return None

    @staticmethod
    def _gstin(value) -> str | None:
        clean = str(value or "").strip().upper()
        if re.fullmatch(r"\d{2}[A-Z]{5}\d{4}[A-Z][A-Z\d]Z[A-Z\d]", clean):
            return clean
        return None
