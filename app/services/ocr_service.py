import re
import os
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
# Uncomment if tesseract.exe is not on PATH:
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

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
                "Food": ["restaurant", "cafe", "food", "hotel", "dinner", "lunch"],
                "Fuel": ["petrol", "diesel", "fuel", "gas", "hpcl", "bpcl"],
                "Travel": ["uber", "ola", "train", "flight", "indigo", "travel"],
                "Shopping": ["store", "mart", "mall", "grocery", "amazon", "flipkart"]
            }
        }

    def extract_text(self, image_path: str) -> str:
        """Extracts raw text from image using Tesseract (lang from TESSERACT_LANGS env var)."""
        if not os.path.exists(image_path):
            return ""
        if not self.available:
            print(f"OCR unavailable: {OCR_IMPORT_ERROR}")
            return ""
        try:
            image = Image.open(image_path)
            # Language is configurable via TESSERACT_LANGS in .env (e.g. eng+hin)
            text = pytesseract.image_to_string(image, lang=TESSERACT_LANGS)
            return text
        except Exception as e:
            print(f"OCR Error: {e}")
            return ""

    def parse_data(self, text: str) -> dict:
        """Parses extracted text using regex to find structured data."""
        data = {
            "amount": None,
            "date": None,
            "gstin": None,
            "category": "General",
            "type": "expense" # Default
        }

        # Find Amount
        amount_match = re.search(self.patterns["amount"], text, re.IGNORECASE)
        if amount_match:
            raw_amount = amount_match.group(1).replace(",", "")
            try:
                data["amount"] = float(raw_amount)
            except:
                pass

        # Find Date
        date_match = re.search(self.patterns["date"], text)
        if date_match:
            data["date"] = date_match.group(1)

        # Find GSTIN
        gst_match = re.search(self.patterns["gstin"], text)
        if gst_match:
            data["gstin"] = gst_match.group(1)

        # Determine Category
        text_lower = text.lower()
        for cat, keywords in self.patterns["category_keywords"].items():
            if any(k in text_lower for k in keywords):
                data["category"] = cat
                break

        return data

    def process_image(self, image_path: str) -> dict:
        """Full pipeline: OCR + Parse."""
        text = self.extract_text(image_path)
        parsed = self.parse_data(text)
        parsed["raw_text"] = text
        if not self.available and OCR_IMPORT_ERROR:
            parsed["error"] = f"OCR dependencies unavailable: {OCR_IMPORT_ERROR}"
        return parsed
