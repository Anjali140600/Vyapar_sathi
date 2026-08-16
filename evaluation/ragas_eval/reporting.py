from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from statistics import fmean
from typing import Any

from .models import EvaluationRecord


def build_summary(
    records: list[EvaluationRecord], thresholds: dict[str, float]
) -> dict[str, Any]:
    metric_names = sorted({name for record in records for name in record.scores})
    aggregates: dict[str, float | None] = {}
    coverage: dict[str, dict[str, int]] = {}
    gates: dict[str, dict[str, Any]] = {}

    for name in metric_names:
        values = [
            value
            for record in records
            if (value := record.scores.get(name)) is not None and math.isfinite(value)
        ]
        aggregates[name] = fmean(values) if values else None
        coverage[name] = {"scored": len(values), "total": len(records)}

    for name, threshold in thresholds.items():
        value = aggregates.get(name)
        gates[name] = {
            "score": value,
            "threshold": threshold,
            "passed": value is not None and coverage.get(name, {}).get("scored") == len(records) and value >= threshold,
        }

    return {
        "sample_count": len(records),
        "aggregates": aggregates,
        "coverage": coverage,
        "gates": gates,
        "passed": bool(gates) and all(gate["passed"] for gate in gates.values()),
        "metric_error_count": sum(len(record.errors) for record in records),
    }


def write_report(
    records: list[EvaluationRecord],
    summary: dict[str, Any],
    output_dir: Path,
    metadata: dict[str, Any],
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = output_dir / stamp
    suffix = 1
    while run_dir.exists():
        run_dir = output_dir / f"{stamp}-{suffix}"
        suffix += 1
    run_dir.mkdir()

    payload = {
        "metadata": metadata,
        "summary": summary,
        "records": [record.to_dict() for record in records],
    }
    _write_json(run_dir / "report.json", payload)
    _write_json(output_dir / "latest_attempt.json", payload)
    if metadata.get("mode") == "collect-only":
        _write_json(output_dir / "latest_collection.json", payload)
    elif _has_complete_coverage(summary):
        _write_json(output_dir / "latest.json", payload)
    _write_csv(run_dir / "scores.csv", records)
    return run_dir


def _has_complete_coverage(summary: dict[str, Any]) -> bool:
    coverage = summary.get("coverage", {})
    return bool(coverage) and summary.get("metric_error_count", 0) == 0 and all(
        item.get("scored") == item.get("total") for item in coverage.values()
    )


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_csv(path: Path, records: list[EvaluationRecord]) -> None:
    metric_names = sorted({name for record in records for name in record.scores})
    fieldnames = ["case_id", "category", "user_input", "response", "latency_ms", *metric_names]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow(
                {
                    "case_id": record.case.case_id,
                    "category": record.case.category,
                    "user_input": record.case.user_input,
                    "response": record.response,
                    "latency_ms": round(record.latency_ms, 2),
                    **record.scores,
                }
            )
