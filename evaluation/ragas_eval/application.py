from __future__ import annotations

from time import perf_counter

from .models import EvaluationCase, EvaluationRecord


class RAGApplicationAdapter:
    """Runs the same retrieval and answer-building code used by the chat application."""

    def __init__(self, db_folder: str, n_results: int = 5):
        try:
            from app.services.rag_service import RAGService
        except ImportError as exc:
            raise RuntimeError(
                "Application dependencies are missing. Run: pip install -r requirements.txt"
            ) from exc

        self.service = RAGService(db_folder=db_folder)
        self.n_results = n_results

    def run(self, case: EvaluationCase) -> EvaluationRecord:
        started = perf_counter()
        contexts = self.service.query(case.user_input, n_results=self.n_results)
        response = self.service.build_concise_answer(case.user_input, contexts, max_lines=3)
        return EvaluationRecord(
            case=case,
            response=response,
            retrieved_contexts=list(contexts),
            latency_ms=(perf_counter() - started) * 1000,
        )
