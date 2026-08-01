from __future__ import annotations

import json
import math
import time
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from app.agents.models import AgentContext, ToolExecutionResult
from app.services.data_service import DataService
from app.services.financial_calculator_service import FinancialCalculatorService
from app.services.rag_service import RAGService


class _QueryTransactionsInput(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    query: str = Field(..., min_length=1, max_length=300)


class _SearchGSTKnowledgeInput(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    query: str = Field(..., min_length=1, max_length=300)
    n_results: int = Field(default=3)

    @field_validator("n_results")
    @classmethod
    def clamp_results(cls, value: int) -> int:
        return max(1, min(int(value), 5))


class _FinancialCalculationInput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    operation: str = Field(..., min_length=1, max_length=50)
    amount: float | None = None
    rate_percent: float | None = None
    revenue: float | None = None
    cost: float | None = None

    @field_validator("amount", "rate_percent", "revenue", "cost")
    @classmethod
    def reject_non_finite_numbers(cls, value: float | None) -> float | None:
        if value is None:
            return value
        if not math.isfinite(value):
            raise ValueError("Values must be finite numbers.")
        return value


class _SummarizeBillInput(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    intent: str | None = Field(default=None, max_length=120)


class AgentToolRegistry:
    def __init__(
        self,
        *,
        data_service: DataService | None = None,
        rag_service: RAGService | None = None,
        financial_calculator_service: FinancialCalculatorService | None = None,
        observation_max_chars: int = 3000,
    ) -> None:
        self.data_service = data_service or DataService()
        self.rag_service = rag_service or RAGService()
        self.financial_calculator_service = financial_calculator_service or FinancialCalculatorService()
        self.observation_max_chars = max(100, min(int(observation_max_chars), 4000))
        self._tool_schemas = {
            "query_transactions": _QueryTransactionsInput,
            "search_gst_knowledge": _SearchGSTKnowledgeInput,
            "calculate_financial_metric": _FinancialCalculationInput,
            "summarize_bill": _SummarizeBillInput,
        }

    def definitions(self, context: AgentContext) -> list[dict[str, Any]]:
        tools = [
            {
                "name": "query_transactions",
                "description": "Answer read-only questions about the authenticated user's transactions.",
                "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
            },
            {
                "name": "search_gst_knowledge",
                "description": "Retrieve GST knowledge from the local knowledge base.",
                "input_schema": {"type": "object", "properties": {"query": {"type": "string"}, "n_results": {"type": "integer"}}},
            },
            {
                "name": "calculate_financial_metric",
                "description": "Perform deterministic GST, profit, loss, and margin calculations.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "operation": {"type": "string"},
                        "amount": {"type": "number"},
                        "rate_percent": {"type": "number"},
                        "revenue": {"type": "number"},
                        "cost": {"type": "number"},
                    },
                    "required": ["operation"],
                },
            },
        ]
        if context.bill_data:
            tools.append(
                {
                    "name": "summarize_bill",
                    "description": "Summarize trusted OCR bill data for the current request.",
                    "input_schema": {"type": "object", "properties": {"intent": {"type": "string"}}},
                }
            )
        return tools

    def normalize_tool_input(self, tool_name: str, tool_input: dict[str, Any]) -> dict[str, Any]:
        schema = self._tool_schemas.get(tool_name)
        if not schema:
            raise ValueError("Unknown tool.")
        parsed = schema.model_validate(tool_input or {})
        return parsed.model_dump(exclude_none=True)

    def duplicate_key(self, tool_name: str, tool_input: dict[str, Any]) -> str:
        normalized = self.normalize_tool_input(tool_name, tool_input)
        return json.dumps({"tool_name": tool_name, "tool_input": normalized}, sort_keys=True, ensure_ascii=True)

    def execute(self, tool_name: str, tool_input: dict[str, Any], context: AgentContext) -> ToolExecutionResult:
        started = time.perf_counter()
        try:
            normalized_input = self.normalize_tool_input(tool_name, tool_input)
        except (ValidationError, ValueError) as exc:
            return ToolExecutionResult(
                tool_name=tool_name,
                status="error",
                result=self._truncate(f"Invalid tool input: {exc}"),
                summary="Invalid tool input.",
            )

        try:
            if tool_name == "query_transactions":
                payload = self._run_query_transactions(normalized_input, context)
            elif tool_name == "search_gst_knowledge":
                payload = self._run_search_gst_knowledge(normalized_input)
            elif tool_name == "calculate_financial_metric":
                payload = self._run_calculate_financial_metric(normalized_input)
            elif tool_name == "summarize_bill":
                payload = self._run_summarize_bill(context)
            else:
                raise ValueError("Unknown tool.")
        except Exception:
            payload = {
                "status": "error",
                "result": "The tool could not complete the request safely.",
                "summary": "Tool execution failed.",
            }

        duration_ms = int((time.perf_counter() - started) * 1000)
        return ToolExecutionResult(
            tool_name=tool_name,
            status=payload["status"],
            result=self._truncate(payload["result"]),
            summary=payload.get("summary", ""),
            duration_ms=duration_ms,
        )

    def _run_query_transactions(self, tool_input: dict[str, Any], context: AgentContext) -> dict[str, str]:
        result = self.data_service.answer_sql_query(
            db=context.db,
            query_text=tool_input["query"],
            user_id=context.user_id,
        )
        if not result:
            return {
                "status": "success",
                "result": "No matching transaction result was found for the authenticated user.",
                "summary": "No transaction result found.",
            }
        return {"status": "success", "result": str(result), "summary": "Transaction data retrieved."}

    def _run_search_gst_knowledge(self, tool_input: dict[str, Any]) -> dict[str, str]:
        docs = self.rag_service.query(tool_input["query"], n_results=tool_input.get("n_results", 3))
        answer = self.rag_service.build_concise_answer(tool_input["query"], docs, max_lines=3)
        return {
            "status": "success",
            "result": answer,
            "summary": "GST knowledge retrieved." if docs else "No GST knowledge result found.",
        }

    def _run_calculate_financial_metric(self, tool_input: dict[str, Any]) -> dict[str, str]:
        result = self.financial_calculator_service.calculate(**tool_input)
        return {"status": "success", "result": result["message"], "summary": "Financial calculation completed."}

    def _run_summarize_bill(self, context: AgentContext) -> dict[str, str]:
        if not context.bill_data:
            return {"status": "error", "result": "No trusted bill data is available for this request.", "summary": "Bill data unavailable."}
        bill_data = context.bill_data
        raw_text = " ".join((bill_data.get("raw_text") or "").split())[:240]
        parts = []
        if bill_data.get("amount") is not None:
            parts.append(f"Amount: Rs. {float(bill_data['amount']):,.2f}")
        if bill_data.get("date"):
            parts.append(f"Date: {bill_data['date']}")
        if bill_data.get("gstin"):
            parts.append(f"GSTIN: {bill_data['gstin']}")
        if bill_data.get("category"):
            parts.append(f"Category: {bill_data['category']}")
        if raw_text:
            parts.append(f"Text summary: {raw_text}")
        if not parts:
            parts.append("Bill data was extracted, but no structured fields were available.")
        return {"status": "success", "result": ". ".join(parts), "summary": "Bill summarized from trusted OCR data."}

    def _truncate(self, text: str) -> str:
        clean = " ".join((text or "").split())
        if len(clean) <= self.observation_max_chars:
            return clean
        return clean[: self.observation_max_chars - 3].rstrip() + "..."
