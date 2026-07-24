import re
from sqlalchemy.orm import Session

from app.services.classifier_service import ClassifierService
from app.services.data_service import DataService
from app.services.ocr_service import OCRService
from app.services.rag_service import RAGService
from app.services.stt_service import STTService
from llm.tinyllama_client import TinyLlamaClient

_SHARED_CLASSIFIER = None
_SHARED_OCR = None
_SHARED_STT = None
_SHARED_DATA_SERVICE = None
_SHARED_RAG_SERVICE = None
_SHARED_LLM = None


def _get_shared_classifier():
    global _SHARED_CLASSIFIER
    if _SHARED_CLASSIFIER is None:
        _SHARED_CLASSIFIER = ClassifierService()
    return _SHARED_CLASSIFIER


def _get_shared_ocr():
    global _SHARED_OCR
    if _SHARED_OCR is None:
        _SHARED_OCR = OCRService()
    return _SHARED_OCR


def _get_shared_stt():
    global _SHARED_STT
    if _SHARED_STT is None:
        _SHARED_STT = STTService()
    return _SHARED_STT


def _get_shared_data_service():
    global _SHARED_DATA_SERVICE
    if _SHARED_DATA_SERVICE is None:
        _SHARED_DATA_SERVICE = DataService()
    return _SHARED_DATA_SERVICE


def _get_shared_rag_service():
    global _SHARED_RAG_SERVICE
    if _SHARED_RAG_SERVICE is None:
        _SHARED_RAG_SERVICE = RAGService()
    return _SHARED_RAG_SERVICE


def _get_shared_llm():
    global _SHARED_LLM
    if _SHARED_LLM is None:
        _SHARED_LLM = TinyLlamaClient()
    return _SHARED_LLM


class ChatOrchestrator:
    def __init__(self, db: Session):
        self.db = db
        # Reuse heavyweight services across requests so each chat message
        # does not pay the initialization cost again.
        self.classifier = _get_shared_classifier()
        self.ocr = _get_shared_ocr()
        self.stt = _get_shared_stt()
        self.data_service = _get_shared_data_service()
        self.rag_service = _get_shared_rag_service()
        self.llm = _get_shared_llm()

    def process_input(self, text: str = None, image_path: str = None, audio_path: str = None, user_id: str = "default_user") -> str:
        """
        Coordinates the entire flow: Input -> Process -> Classify -> Fetch -> Answer.
        """
        final_query = text or ""
        extracted_data = None

        if image_path:
            ocr_result = self.ocr.process_image(image_path)
            final_query = ocr_result.get("raw_text", "")
            extracted_data = ocr_result
        elif audio_path:
            final_query = self.stt.transcribe(audio_path)

        if not final_query.strip():
            return "I couldn't understand the input. Please provide text, an image of a bill, or a voice message."

        classification = self.classifier.classify(final_query)
        q_type = classification["query_type"]
        likely_db_query = q_type in {"sql", "mixed"} or self._contains_db_terms(final_query)
        sql_answer = self.data_service.answer_sql_query(self.db, final_query, user_id) if likely_db_query else ""

        category_summary = self._answer_category_amount_query(final_query, user_id)
        if category_summary and self._prefer_sql_answer(final_query, q_type):
            return self._format_response(category_summary, max_lines=1, max_words=28)

        if sql_answer and self._prefer_sql_answer(final_query, q_type):
            return self._generate_fallback("sql", sql_answer, "", extracted_data, final_query)

        if q_type == "sql":
            return self._generate_fallback("sql", sql_answer or "", "", extracted_data, final_query)

        docs = self.rag_service.query(final_query)
        rag_context = "\n".join(docs)

        if q_type == "general":
            if self._should_use_openai_general(final_query, docs):
                return self.llm.generate_general_response(final_query, max_lines=3, max_words=55)
            rag_answer = self._answer_rag_query(final_query, docs)
            return self._format_response(rag_answer, max_lines=3, max_words=55)

        if q_type == "mixed":
            rag_answer = self._answer_rag_query(final_query, docs, prefer_single_line=True)
            combined = self._combine_mixed_answer(sql_answer, rag_answer)
            return self._generate_fallback("mixed", combined, rag_context, extracted_data, final_query)

        return self._generate_fallback(q_type, "", rag_context, extracted_data, final_query)

    def _answer_category_amount_query(self, query: str, user_id: str):
        lower = (query or "").lower().strip()
        if not lower:
            return None

        if re.search(r"\b(gst|tax|quantity|qty|units|pieces)\b", lower):
            return None

        if not re.search(r"\b(amount|total|how much|what is my)\b", lower):
            return None

        cleaned = re.sub(r"[^\w\s]", " ", lower)
        cleaned = re.sub(r"\b(what|is|my|the|amount|total|how|much|for|of|show|tell|me)\b", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if not cleaned:
            return None

        summary = self.data_service.summarize_category_amount(self.db, cleaned, user_id)
        if not summary:
            return None

        amount = float(summary["amount"])
        category = summary["category"]
        count = summary["count"]
        latest_date = summary["latest_date"] or "your latest entry"

        if count == 1:
            return f"Your {category} amount from MySQL is Rs. {amount:,.2f}, dated {latest_date}."
        return f"Your total {category} amount from MySQL is Rs. {amount:,.2f} across {count} transactions."

    @staticmethod
    def _contains_gst_terms(query: str) -> bool:
        lower = (query or "").lower()
        return bool(re.search(r"\b(gst|cgst|sgst|igst|tax|hsn|sac|law|rules?|slab|percentage|rate)\b", lower))

    @staticmethod
    def _contains_db_terms(query: str) -> bool:
        lower = (query or "").lower()
        return bool(
            re.search(
                r"\b(transaction|transactions|entries|amount|total|sum|quantity|qty|units|pieces|sales|sale|income|expense|expenses|purchase|rent|salary|profit|loss|balance|recent|last|highest|lowest|average|avg|count|how many|item|items|material|materials|shop)\b",
                lower,
            )
        )

    def _prefer_sql_answer(self, query: str, q_type: str) -> bool:
        if q_type == "sql":
            return True
        if self._contains_db_terms(query):
            return True
        return False

    def _should_use_openai_general(self, query: str, docs: list[str]) -> bool:
        if self._contains_gst_terms(query):
            return False
        if self._contains_db_terms(query):
            return False
        if docs:
            return False
        return True

    def _answer_rag_query(self, final_query: str, docs: list[str], prefer_single_line: bool = False) -> str:
        if not docs:
            return "I could not find a matching answer in the GST knowledge base."

        max_lines = 1 if prefer_single_line else 3
        return self.rag_service.build_concise_answer(final_query, docs, max_lines=max_lines)

    def _combine_mixed_answer(self, sql_answer: str | None, rag_answer: str | None) -> str:
        sql_part = self._single_line(sql_answer or "")
        rag_part = self._single_line(rag_answer or "")
        if sql_part and rag_part:
            return f"{sql_part} GST: {rag_part}"
        return sql_part or rag_part

    @staticmethod
    def _single_line(text: str) -> str:
        return " ".join((text or "").replace("\n", " ").split())

    def _format_response(self, text: str, max_lines: int = 1, max_words: int = 30) -> str:
        source = self._single_line(text) if max_lines == 1 else text
        return self.llm._enforce_limits(source, max_lines=max_lines, max_words=max_words)

    def _generate_fallback(self, q_type, data, context, extracted_data=None, final_query: str = ""):
        if extracted_data and extracted_data.get("amount"):
            amount = extracted_data["amount"]
            date = extracted_data.get("date", "recent")
            return f"I processed your bill of Rs. {amount:,.2f} dated {date} and saved the details."

        if q_type == "sql":
            answer = data or "I could not find matching MySQL data for this query."
            return self._format_response(answer, max_lines=1, max_words=28)

        if q_type == "general":
            docs = [doc for doc in context.split("\n") if doc.strip()]
            if self._should_use_openai_general(final_query, docs):
                return self.llm.generate_general_response(final_query, max_lines=3, max_words=55)
            answer = self.rag_service.build_concise_answer(final_query, docs, max_lines=3)
            return self._format_response(answer, max_lines=3, max_words=55)

        if q_type == "mixed":
            answer = data
            if not answer:
                docs = [doc for doc in context.split("\n") if doc.strip()]
                rag_answer = self.rag_service.build_concise_answer(final_query, docs, max_lines=1) if docs else ""
                answer = self._combine_mixed_answer("", rag_answer)
            return self._format_response(answer or "I could not fully answer the mixed query.", max_lines=1, max_words=38)

        return "I could not process this request."
