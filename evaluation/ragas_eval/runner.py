from __future__ import annotations

import asyncio
import hashlib
import platform
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, Protocol

from .config import EvaluationConfig
from .dataset import load_cases, to_ragas_dataset
from .models import EvaluationCase, EvaluationRecord
from .reporting import build_summary, write_report


class ApplicationAdapter(Protocol):
    def run(self, case: EvaluationCase) -> EvaluationRecord: ...


class MetricSuite(Protocol):
    async def score_records(self, records: list[EvaluationRecord]) -> list[EvaluationRecord]: ...


def collect_outputs(cases: list[EvaluationCase], application: ApplicationAdapter) -> list[EvaluationRecord]:
    return [application.run(case) for case in cases]


def run_evaluation(
    config: EvaluationConfig,
    application: ApplicationAdapter,
    metric_suite: MetricSuite | None,
    limit: int | None = None,
) -> tuple[dict[str, Any], Path]:
    cases = load_cases(config.dataset_path, limit=limit)
    records = collect_outputs(cases, application)

    # Validate that captured fields conform to RAGAS's EvaluationDataset schema.
    if metric_suite is not None:
        to_ragas_dataset(records)
        records = asyncio.run(metric_suite.score_records(records))
        thresholds = config.thresholds
    else:
        thresholds = {}

    summary = build_summary(records, thresholds)
    metadata = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dataset": str(config.dataset_path),
        "dataset_sha256": _sha256(config.dataset_path),
        "db_folder": str(config.db_folder),
        "n_results": config.n_results,
        "provider": config.provider if metric_suite is not None else None,
        "evaluator_model": config.evaluator_model if metric_suite is not None else None,
        "embedding_model": config.embedding_model if metric_suite is not None else None,
        "max_concurrency": config.max_concurrency if metric_suite is not None else None,
        "thresholds": thresholds,
        "python": platform.python_version(),
        "packages": {
            name: _package_version(name)
            for name in ("ragas", "openai", "chromadb")
        },
        "mode": "ragas" if metric_suite is not None else "collect-only",
    }
    run_dir = write_report(records, summary, config.output_dir, metadata)
    return summary, run_dir


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def _package_version(name: str) -> str | None:
    try:
        return version(name)
    except PackageNotFoundError:
        return None
