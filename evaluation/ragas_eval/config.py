from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_THRESHOLDS = {
    "context_precision": 0.65,
    "context_recall": 0.70,
    "faithfulness": 0.70,
    "answer_relevancy": 0.70,
    "factual_correctness": 0.70,
}


@dataclass(frozen=True)
class EvaluationConfig:
    dataset_path: Path = Path("evaluation/datasets/gst_rag_eval.jsonl")
    output_dir: Path = Path("evaluation/results")
    db_folder: Path = Path("modules/module_1_rag/chroma_db")
    provider: str = field(
        default_factory=lambda: os.getenv("RAGAS_PROVIDER", "openai").strip().lower()
    )
    evaluator_model: str = field(
        default_factory=lambda: os.getenv("RAGAS_EVALUATOR_MODEL", "gpt-4o-mini")
    )
    embedding_model: str = field(
        default_factory=lambda: os.getenv("RAGAS_EMBEDDING_MODEL", "text-embedding-3-small")
    )
    max_concurrency: int = field(
        default_factory=lambda: int(os.getenv("RAGAS_MAX_CONCURRENCY", "2"))
    )
    n_results: int = 3
    thresholds: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_THRESHOLDS))

    def __post_init__(self) -> None:
        if self.provider not in {"openai", "google"}:
            raise ValueError("RAGAS_PROVIDER must be either 'openai' or 'google'")
        if self.max_concurrency < 1:
            raise ValueError("max_concurrency must be at least 1")
        if self.n_results < 1:
            raise ValueError("n_results must be at least 1")
        for name, value in self.thresholds.items():
            if not 0 <= value <= 1:
                raise ValueError(f"threshold for {name!r} must be between 0 and 1")
