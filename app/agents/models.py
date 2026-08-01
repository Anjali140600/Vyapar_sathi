from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


ALLOWED_TOOL_NAMES = (
    "query_transactions",
    "search_gst_knowledge",
    "calculate_financial_metric",
    "summarize_bill",
)


class AgentAction(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    action: Literal["call_tool", "final_answer"]
    tool_name: Optional[Literal["query_transactions", "search_gst_knowledge", "calculate_financial_metric", "summarize_bill"]] = None
    tool_input: dict[str, Any] = Field(default_factory=dict)
    final_answer: Optional[str] = None
    decision_summary: Optional[str] = Field(default=None, max_length=200)

    @field_validator("tool_input")
    @classmethod
    def limit_tool_input(cls, value: dict[str, Any]) -> dict[str, Any]:
        if len(value) > 12:
            raise ValueError("Too many tool input fields.")
        return value

    @field_validator("final_answer")
    @classmethod
    def normalize_final_answer(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        trimmed = value.strip()
        if len(trimmed) > 4000:
            raise ValueError("Final answer is too long.")
        return trimmed

    @model_validator(mode="after")
    def validate_action(self) -> "AgentAction":
        if self.action == "call_tool":
            if not self.tool_name:
                raise ValueError("call_tool requires tool_name.")
            if self.final_answer:
                raise ValueError("Tool actions cannot include final_answer.")
        if self.action == "final_answer":
            if self.tool_name:
                raise ValueError("Final actions cannot include tool_name.")
            if not self.final_answer:
                raise ValueError("final_answer action requires final_answer text.")
        return self


class AgentObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step: int
    tool_name: str
    status: Literal["success", "error", "skipped"]
    result: str


class AgentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: str
    trace: list[dict[str, Any]] = Field(default_factory=list)


class ToolExecutionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_name: str
    status: Literal["success", "error", "skipped"]
    result: str
    summary: str = ""
    duration_ms: Optional[int] = None


@dataclass
class AgentContext:
    db: Any
    user_id: str
    conversation_history: list[dict[str, str]]
    bill_data: dict[str, Any] | None = None
