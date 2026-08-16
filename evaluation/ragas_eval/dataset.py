from __future__ import annotations

import json
from pathlib import Path

from .models import EvaluationCase, EvaluationRecord


def load_cases(path: Path, limit: int | None = None) -> list[EvaluationCase]:
    if not path.is_file():
        raise FileNotFoundError(f"evaluation dataset not found: {path}")

    cases: list[EvaluationCase] = []
    seen_ids: set[str] = set()
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSON on line {line_number} of {path}: {exc.msg}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"dataset line {line_number} must contain a JSON object")
            case = EvaluationCase.from_dict(row, line_number)
            if case.case_id in seen_ids:
                raise ValueError(f"duplicate case_id {case.case_id!r} on line {line_number}")
            seen_ids.add(case.case_id)
            cases.append(case)
            if limit is not None and len(cases) >= limit:
                break

    if not cases:
        raise ValueError(f"evaluation dataset is empty: {path}")
    return cases


def to_ragas_dataset(records: list[EvaluationRecord]):
    """Build RAGAS's canonical dataset lazily, keeping RAGAS an optional runtime dependency."""
    try:
        from ragas import EvaluationDataset
    except ImportError as exc:
        raise RuntimeError(
            "RAGAS is not installed. Run: pip install -r evaluation/requirements.txt"
        ) from exc
    return EvaluationDataset.from_list([record.ragas_input() for record in records])
