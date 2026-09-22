import re
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

try:
    import pytesseract
    from PIL import Image
    OCR_IMPORT_ERROR = None
except Exception as exc:
    pytesseract = None
    Image = None
    OCR_IMPORT_ERROR = exc

# Configure Tesseract path for Windows if not in PATH.
if pytesseract and os.name == "nt":
    _tess_cmd = os.getenv("TESSERACT_CMD", r"C:\Program Files\Tesseract-OCR\tesseract.exe")
    if os.path.exists(_tess_cmd):
        pytesseract.pytesseract.tesseract_cmd = _tess_cmd

# Read language config from .env  (e.g. TESSERACT_LANGS=eng+hin)
TESSERACT_LANGS = os.getenv("TESSERACT_LANGS", "eng+hin")

class OCRService:
    def __init__(self):
        self.available = pytesseract is not None and Image is not None
        # Common regex patterns for invoices/bills
        self.patterns = {
            "amount": r"(?:total|amount|net|grand total|sum)[:\s]*[^\d]*([0-9,]+\.[0-9]{2}|[0-9,]+)",
            "date": r"(\d{2}[/-]\d{2}[/-]\d{4}|\d{4}[/-]\d{2}[/-]\d{2})",
            "gstin": r"(\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1})",
            "category_keywords": {
                "Food": ["restaurant", "cafe", "coffee", "food", "hotel", "dinner", "lunch", "tandoori", "paneer"],
                "Fuel": ["petrol", "diesel", "fuel", "gas", "hpcl", "bpcl"],
                "Travel": ["uber", "ola", "train", "flight", "indigo", "travel"],
                "Shopping": ["store", "mart", "mall", "grocery", "amazon", "flipkart"]
            }
        }

    def extract_text(self, image_path: str) -> str:
        """Extract text, retaining the original pass if enhancement is unavailable."""
        if not os.path.exists(image_path):
            return ""
        if not self.available:
            print(f"OCR unavailable: {OCR_IMPORT_ERROR}")
            return ""
        try:
            image = Image.open(image_path)
            # Keep the original OCR pass as the guaranteed fallback.
            original = pytesseract.image_to_string(image, lang=TESSERACT_LANGS)

            # Small/low-contrast receipts benefit substantially from upscaling and
            # autocontrast. This uses Pillow, which OCR already depends on.
            try:
                from PIL import ImageOps

                grayscale = ImageOps.autocontrast(image.convert("L"))
                scale = 3 if max(image.size) < 1600 else 2
                resized = grayscale.resize(
                    (grayscale.width * scale, grayscale.height * scale)
                )
                enhanced = pytesseract.image_to_string(
                    resized, lang=TESSERACT_LANGS, config="--psm 6"
                )
                if self._text_quality(enhanced) > self._text_quality(original):
                    return enhanced
            except Exception:
                pass

            return original
        except Exception as e:
            print(f"OCR Error: {e}")
            return ""

    def parse_data(self, text: str) -> dict:
        """Parses extracted text using regex to find structured data."""
        data = {
            "amount": None,
            "date": None,
            "gstin": None,
            "vendor": None,
            "invoice_number": None,
            "taxable_amount": None,
            "gst_amount": None,
            "category": "General",
            "type": "expense" # Default
        }

        # Find Amount
        data["amount"] = self._labelled_amount(
            text,
            r"(?:grand\s*total|net\s*(?:amount|payable)|total\s*amount|balance\s*due|amount\s*due|total)",
        )
        if data["amount"] is None and re.search(
            r"\b(?:cashier|service\s*charge)\b", text, re.IGNORECASE
        ):
            standalone = re.findall(
                r"(?m)^\s*(?:Rs\.?|INR|₹|%)?\s*([0-9][0-9,]*\.\d{2})\s*$",
                text,
                re.IGNORECASE,
            )
            candidates = [self._to_number(value) for value in standalone]
            candidates = [value for value in candidates if value is not None]
            if candidates:
                data["amount"] = max(candidates)

        # Find Date
        date_match = re.search(self.patterns["date"], text)
        if date_match:
            data["date"] = self._normalize_date(date_match.group(1))

        # Find GSTIN
        gst_match = re.search(self.patterns["gstin"], text)
        if gst_match:
            data["gstin"] = gst_match.group(1)

        invoice_match = re.search(
            r"\b(?:invoice|bill)\s*(?:no|number|#)?\s*[.:#-]*\s*([A-Z0-9][A-Z0-9/-]{1,30})",
            text,
            re.IGNORECASE,
        )
        if invoice_match:
            data["invoice_number"] = invoice_match.group(1).strip()

        data["taxable_amount"] = self._labelled_amount(text, r"taxable\s*amount")
        data["gst_amount"] = self._extract_gst_amount(text)
        data["vendor"] = self._extract_vendor(text)

        # Determine Category
        text_lower = text.lower()
        for cat, keywords in self.patterns["category_keywords"].items():
            if any(k in text_lower for k in keywords):
                data["category"] = cat
                break

        return data

    @staticmethod
    def _text_quality(text: str) -> int:
        clean = text or ""
        keywords = len(
            re.findall(
                r"\b(?:bill|invoice|date|total|amount|gst|tax|cashier|qty|price|service)\b",
                clean,
                re.IGNORECASE,
            )
        )
        numbers = len(re.findall(r"\b\d+[.,]\d{2}\b", clean))
        return len(re.findall(r"[A-Za-z0-9]", clean)) + keywords * 30 + numbers * 8

    @staticmethod
    def _to_number(value: str):
        clean = re.sub(r"[^0-9.,]", "", value or "").replace(",", "")
        try:
            number = round(float(clean), 2)
            return number if number >= 0 else None
        except (TypeError, ValueError):
            return None

    @classmethod
    def _labelled_amount(cls, text: str, label_pattern: str):
        # OCR commonly places the label and value on adjacent lines, so allow a
        # short non-numeric gap while avoiding unrelated table rows.
        pattern = rf"{label_pattern}\s*[:=-]?\s*(?:Rs\.?|INR|₹|%)?\s*([0-9][0-9,]*(?:\.\d{{1,2}})?)"
        matches = re.findall(pattern, text or "", re.IGNORECASE)
        values = [cls._to_number(match) for match in matches]
        values = [value for value in values if value is not None]
        if values:
            return values[-1]

        lines = [line.strip() for line in (text or "").splitlines()]
        for index, line in enumerate(lines):
            if not re.search(label_pattern, line, re.IGNORECASE):
                continue
            for nearby in lines[index : index + 3]:
                candidates = re.findall(r"\b[0-9][0-9,]*\.\d{1,2}\b", nearby)
                if candidates:
                    return cls._to_number(candidates[-1])
        return None

    @classmethod
    def _extract_gst_amount(cls, text: str):
        explicit = cls._labelled_amount(text, r"\b(?:total\s*)?gst\b(?:\s*amount)?")
        if explicit is not None:
            return explicit

        components = []
        for label in (r"cgst(?:\s*@?\s*[0-9.]+%?)?", r"sgst(?:\s*@?\s*[0-9.]+%?)?", r"igst(?:\s*@?\s*[0-9.]+%?)?"):
            value = cls._labelled_amount(text, label)
            if value is not None:
                components.append(value)
        return round(sum(components), 2) if components else None

    @staticmethod
    def _normalize_date(value: str):
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d"):
            try:
                return datetime.strptime(value, fmt).date().isoformat()
            except ValueError:
                continue
        return value

    @staticmethod
    def _extract_vendor(text: str):
        lines = [" ".join(line.split()) for line in (text or "").splitlines() if line.strip()]
        if lines and re.match(r"^cashier\b", lines[0], re.IGNORECASE):
            return None
        skip = re.compile(
            r"^(?:tax invoice|invoice|bill|cashier|date|gstin|phone|mobile|address|qty|quantity|s\.?\s*no|dish\b|items?\b)",
            re.IGNORECASE,
        )
        for line in lines[:8]:
            clean = re.sub(r"^[^A-Za-z]+|[^A-Za-z0-9&.,' -]+$", "", line).strip()
            clean = re.sub(r"\s+(?:bill|invoice)\s*(?:no|number|#).*?$", "", clean, flags=re.IGNORECASE).strip()
            if re.search(r"\b(?:qty|quantity|amnt|amount|price)\b", clean, re.IGNORECASE):
                continue
            if len(clean) >= 3 and re.search(r"[A-Za-z]{3}", clean) and not skip.search(clean):
                return clean[:150]
        return None

    def process_image(self, image_path: str) -> dict:
        """Full pipeline: OCR + Parse."""
        text = self.extract_text(image_path)
        parsed = self.parse_data(text)
        parsed["raw_text"] = text
        if not self.available and OCR_IMPORT_ERROR:
            parsed["error"] = f"OCR dependencies unavailable: {OCR_IMPORT_ERROR}"
        return parsed
