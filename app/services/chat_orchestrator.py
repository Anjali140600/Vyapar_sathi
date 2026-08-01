import os
from sqlalchemy.orm import Session

from app.agents.models import AgentContext, AgentResponse
from app.agents.tool_registry import AgentToolRegistry
from app.agents.vyapar_sathi_agent import VyaparSathiAgent
from app.services.classifier_service import ClassifierService
from app.services.data_service import DataService
from app.services.financial_calculator_service import FinancialCalculatorService
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
_SHARED_CALCULATOR = None


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


def _get_shared_calculator():
    global _SHARED_CALCULATOR
    if _SHARED_CALCULATOR is None:
        _SHARED_CALCULATOR = FinancialCalculatorService()
    return _SHARED_CALCULATOR


def _history_limit() -> int:
    try:
        value = int(os.getenv("AGENT_HISTORY_LIMIT", "8"))
    except ValueError:
        value = 8
    return max(2, min(value, 10))


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
        self.calculator = _get_shared_calculator()
        self.tool_registry = AgentToolRegistry(
            data_service=self.data_service,
            rag_service=self.rag_service,
            financial_calculator_service=self.calculator,
            observation_max_chars=int(os.getenv("AGENT_OBSERVATION_MAX_CHARS", "3000") or "3000"),
        )
        self.agent = VyaparSathiAgent(
            llm_client=self.llm,
            tool_registry=self.tool_registry,
            classifier_service=self.classifier,
            calculator_service=self.calculator,
        )

    def process_input_with_trace(
        self,
        text: str | None = None,
        image_path: str | None = None,
        audio_path: str | None = None,
        user_id: str = "default_user",
        conversation_history: list[dict[str, str]] | None = None,
    ) -> AgentResponse:
        final_query = text or ""
        bill_data = None

        if image_path:
            ocr_result = self.ocr.process_image(image_path)
            bill_data = ocr_result
            final_query = ocr_result.get("raw_text", "").strip()
            if not final_query and any(ocr_result.get(key) for key in ("amount", "date", "gstin", "category")):
                final_query = "Summarize the uploaded bill"
        elif audio_path:
            try:
                final_query = self.stt.transcribe(audio_path)
            except Exception:
                final_query = ""

        if not final_query.strip():
            return AgentResponse(
                answer="I couldn't understand the input. Please provide text, an image of a bill, or a voice message."
            )

        history = self._sanitize_history(conversation_history or [])
        context = AgentContext(
            db=self.db,
            user_id=user_id,
            conversation_history=history,
            bill_data=bill_data,
        )
        return self.agent.run(user_query=final_query, context=context)

    def process_input(
        self,
        text: str | None = None,
        image_path: str | None = None,
        audio_path: str | None = None,
        user_id: str = "default_user",
        conversation_history: list[dict[str, str]] | None = None,
    ) -> str:
        return self.process_input_with_trace(
            text=text,
            image_path=image_path,
            audio_path=audio_path,
            user_id=user_id,
            conversation_history=conversation_history,
        ).answer

    def _sanitize_history(self, conversation_history: list[dict[str, str]]) -> list[dict[str, str]]:
        limit = _history_limit()
        cleaned: list[dict[str, str]] = []
        total_chars = 0
        for item in conversation_history[-limit:]:
            role = (item.get("role") or "").strip().lower()
            content = " ".join((item.get("content") or "").split()).strip()
            if role not in {"user", "assistant"} or not content:
                continue
            content = content[:400]
            total_chars += len(content)
            if total_chars > 2400:
                break
            cleaned.append({"role": role, "content": content})
        return cleaned
