from __future__ import annotations

import asyncio
import math
import os
from collections.abc import Iterable
from typing import Any

from .models import EvaluationRecord


METRIC_INPUTS = {
    "context_precision": ("user_input", "reference", "retrieved_contexts"),
    "context_recall": ("user_input", "reference", "retrieved_contexts"),
    "faithfulness": ("user_input", "response", "retrieved_contexts"),
    "answer_relevancy": ("user_input", "response"),
    "factual_correctness": ("response", "reference"),
}


class RagasMetricSuite:
    """Scores captured application outputs with the RAGAS v0.4 collections API."""

    def __init__(
        self,
        provider: str,
        evaluator_model: str,
        embedding_model: str,
        max_concurrency: int = 2,
    ) -> None:
        provider = provider.strip().lower()
        if provider not in {"openai", "google"}:
            raise ValueError("RAGAS provider must be either 'openai' or 'google'")

        key_name = "GOOGLE_API_KEY" if provider == "google" else "OPENAI_API_KEY"
        api_key = os.getenv(key_name)
        if not api_key or api_key.startswith("your_"):
            raise RuntimeError(f"{key_name} is required to run the RAGAS judge metrics")

        try:
            from openai import AsyncOpenAI
            from ragas.embeddings.base import embedding_factory
            from ragas.llms import llm_factory
            from ragas.metrics.collections import (
                AnswerRelevancy,
                ContextPrecision,
                ContextRecall,
                Faithfulness,
                FactualCorrectness,
            )
        except ImportError as exc:
            raise RuntimeError(
                "Evaluation dependencies are missing. Run: "
                "pip install -r evaluation/requirements.txt"
            ) from exc

        client_kwargs: dict[str, Any] = {"api_key": api_key}
        if provider == "google":
            client_kwargs["base_url"] = os.getenv(
                "RAGAS_GOOGLE_BASE_URL",
                "https://generativelanguage.googleapis.com/v1beta/openai/",
            )
        elif os.getenv("OPENAI_BASE_URL"):
            client_kwargs["base_url"] = os.environ["OPENAI_BASE_URL"]
        client = AsyncOpenAI(**client_kwargs)
        # Gemini exposes an OpenAI-compatible endpoint. This lets the existing
        # structured-output and embedding adapters operate against Google's API.
        judge = llm_factory(evaluator_model, client=client, temperature=0)
        embeddings = embedding_factory(
            "openai", model=embedding_model, client=client
        )
        self.metrics = {
            "context_precision": ContextPrecision(llm=judge),
            "context_recall": ContextRecall(llm=judge),
            "faithfulness": Faithfulness(llm=judge),
            "answer_relevancy": AnswerRelevancy(llm=judge, embeddings=embeddings),
            "factual_correctness": FactualCorrectness(llm=judge, mode="f1"),
        }
        self.provider = provider
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._fatal_provider_error: str | None = None

    async def score_records(self, records: list[EvaluationRecord]) -> list[EvaluationRecord]:
        await asyncio.gather(
            *(self._score_one(record, name, metric) for record in records for name, metric in self.metrics.items())
        )
        return records

    async def _score_one(self, record: EvaluationRecord, name: str, metric: Any) -> None:
        values = record.ragas_input()
        kwargs = {key: values[key] for key in METRIC_INPUTS[name]}
        try:
            async with self._semaphore:
                if self._fatal_provider_error:
                    raise RuntimeError(self._fatal_provider_error)
                result = await metric.ascore(**kwargs)
            value = float(result.value)
            if not math.isfinite(value):
                raise ValueError(f"metric returned a non-finite value: {value}")
            record.scores[name] = value
            record.reasons[name] = result.reason
        except Exception as exc:  # Preserve partial results and surface the exact failed metric.
            error = f"{type(exc).__name__}: {exc}"
            if any(
                marker in error
                for marker in (
                    "insufficient_quota",
                    "credit_balance_exhausted",
                    "RESOURCE_EXHAUSTED",
                    "quota exceeded",
                )
            ):
                provider_name = "Google Gemini" if self.provider == "google" else "OpenAI"
                key_name = "GOOGLE_API_KEY" if self.provider == "google" else "OPENAI_API_KEY"
                error = (
                    f"{provider_name} quota is exhausted. Wait for quota reset or configure "
                    f"a key with available quota in {key_name}."
                )
                self._fatal_provider_error = error
            record.scores[name] = None
            record.reasons[name] = None
            record.errors[name] = error


def metric_names() -> Iterable[str]:
    return METRIC_INPUTS.keys()
