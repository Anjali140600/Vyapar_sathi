from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class EvaluationCase:
    case_id: str
    user_input: str
    reference: str
    category: str = "gst"
    source: str = ""

    @classmethod
    def from_dict(cls, row: dict[str, Any], line_number: int | None = None) -> "EvaluationCase":
        location = f" on line {line_number}" if line_number else ""
        required = ("case_id", "user_input", "reference")
        missing = [name for name in required if not str(row.get(name, "")).strip()]
        if missing:
            raise ValueError(f"missing required field(s){location}: {', '.join(missing)}")
        return cls(
            case_id=str(row["case_id"]).strip(),
            user_input=str(row["user_input"]).strip(),
            reference=str(row["reference"]).strip(),
            category=str(row.get("category", "gst")).strip() or "gst",
            source=str(row.get("source", "")).strip(),
        )


@dataclass
class EvaluationRecord:
    case: EvaluationCase
    response: str
    retrieved_contexts: list[str]
    latency_ms: float
    scores: dict[str, float | None] = field(default_factory=dict)
    reasons: dict[str, str | None] = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)

    def ragas_input(self) -> dict[str, Any]:
        return {
            "user_input": self.case.user_input,
            "response": self.response,
            "retrieved_contexts": self.retrieved_contexts,
            "reference": self.case.reference,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self.case),
            "response": self.response,
            "retrieved_contexts": self.retrieved_contexts,
            "latency_ms": round(self.latency_ms, 2),
            "scores": self.scores,
            "reasons": self.reasons,
            "errors": self.errors,
        }
