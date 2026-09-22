import unittest

from backend.app.services.structured_ocr_service import StructuredOCRService


class FakeModel:
    def __init__(self, response):
        self.response = response

    def generate_json(self, _prompt):
        return self.response


class StructuredOCRServiceTests(unittest.TestCase):
    def setUp(self):
        self.regex_result = {
            "raw_text": "ACME Traders Invoice 19 Total Rs 1180",
            "amount": 1180.0,
            "date": "2026-09-08",
            "category": "General",
            "type": "expense",
        }

    def test_model_initialization_failure_preserves_regex_result(self):
        def unavailable_model():
            raise RuntimeError("provider unavailable")

        result = StructuredOCRService(unavailable_model).enhance(self.regex_result)

        for key, value in self.regex_result.items():
            self.assertEqual(result[key], value)
        self.assertFalse(result["llm_enhanced"])
        self.assertTrue(result["fallback_used"])
        self.assertEqual(result["extraction_source"], "regex")

    def test_invalid_or_empty_model_response_uses_fallback(self):
        result = StructuredOCRService(lambda: FakeModel(None)).enhance(
            self.regex_result
        )

        self.assertEqual(result["amount"], 1180.0)
        self.assertEqual(result["category"], "General")
        self.assertTrue(result["fallback_used"])

    def test_unusable_model_fields_use_fallback(self):
        response = {
            "amount": -10,
            "gst_amount": -2,
            "date": "not-a-date",
            "type": "unknown",
        }
        result = StructuredOCRService(lambda: FakeModel(response)).enhance(
            self.regex_result
        )

        self.assertEqual(result["amount"], 1180.0)
        self.assertEqual(result["date"], "2026-09-08")
        self.assertEqual(result["type"], "expense")
        self.assertFalse(result["llm_enhanced"])
        self.assertTrue(result["fallback_used"])

    def test_valid_model_fields_are_merged_over_regex_result(self):
        response = {
            "vendor": "ACME Traders",
            "invoice_number": "INV-19",
            "date": "08/09/2026",
            "amount": "1,180.00",
            "taxable_amount": 1000,
            "gst_amount": 180,
            "gstin": "27ABCDE1234F1Z5",
            "category": "Raw materials",
            "type": "expense",
        }
        result = StructuredOCRService(lambda: FakeModel(response)).enhance(
            self.regex_result
        )

        self.assertEqual(result["vendor"], "ACME Traders")
        self.assertEqual(result["date"], "2026-09-08")
        self.assertEqual(result["taxable_amount"], 1000.0)
        self.assertEqual(result["gst_amount"], 180.0)
        self.assertTrue(result["llm_enhanced"])
        self.assertFalse(result["fallback_used"])
        self.assertEqual(result["extraction_source"], "ocr+llm")


if __name__ == "__main__":
    unittest.main()
