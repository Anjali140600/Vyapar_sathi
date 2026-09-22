import unittest

from backend.app.services.ocr_service import OCRService


class OCRServiceParserTests(unittest.TestCase):
    def setUp(self):
        self.service = OCRService()

    def test_extracts_common_invoice_fields(self):
        result = self.service.parse_data(
            """Coffee Shop Bill No. 4588
Date: 09/09/2026
GSTIN: 27ABCDE1234F1Z5
Taxable Amount: Rs. 1,000.00
CGST: 90.00
SGST: 90.00
Grand Total: Rs. 1,180.00"""
        )

        self.assertEqual(result["vendor"], "Coffee Shop")
        self.assertEqual(result["invoice_number"], "4588")
        self.assertEqual(result["date"], "2026-09-09")
        self.assertEqual(result["amount"], 1180.0)
        self.assertEqual(result["taxable_amount"], 1000.0)
        self.assertEqual(result["gst_amount"], 180.0)
        self.assertEqual(result["category"], "Food")

    def test_amount_can_follow_total_on_next_line(self):
        result = self.service.parse_data("Invoice\nGrand Total\n₹ 2,450.50")
        self.assertEqual(result["amount"], 2450.5)

    def test_receipt_standalone_total_is_safe_last_resort(self):
        result = self.service.parse_data(
            "Cashier: RAM\nDish Qty Amount\nPaneer 2 300.00\n\n2011.00\nService Charge"
        )
        self.assertEqual(result["amount"], 2011.0)
        self.assertIsNone(result["vendor"])

    def test_no_total_is_not_invented(self):
        result = self.service.parse_data(
            "Coffee Shop Bill No. 4588\nHot coffee 1 12.50\nTotal"
        )
        self.assertIsNone(result["amount"])


if __name__ == "__main__":
    unittest.main()
