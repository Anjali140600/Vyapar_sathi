from __future__ import annotations

import json
import os
import re
from typing import Any

from app.agents.models import ALLOWED_TOOL_NAMES, AgentAction, AgentContext, AgentObservation, AgentResponse
from app.agents.tool_registry import AgentToolRegistry
from app.services.classifier_service import ClassifierService
from app.services.financial_calculator_service import FinancialCalculatorService


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _clamp_int(value: str | None, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value) if value is not None else default
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(parsed, maximum))


class VyaparSathiAgent:
    def __init__(
        self,
        *,
        llm_client: Any,
        tool_registry: AgentToolRegistry,
        classifier_service: ClassifierService | None = None,
        calculator_service: FinancialCalculatorService | None = None,
        max_steps: int | None = None,
        decision_max_chars: int | None = None,
        debug: bool | None = None,
        enable_agent: bool | None = None,
    ) -> None:
        self.llm_client = llm_client
        self.tool_registry = tool_registry
        self.classifier_service = classifier_service or ClassifierService()
        self.calculator_service = calculator_service or FinancialCalculatorService()
        self.max_steps = max_steps if max_steps is not None else _clamp_int(os.getenv("AGENT_MAX_STEPS"), 4, 1, 6)
        configured_decision_max = decision_max_chars if decision_max_chars is not None else _clamp_int(
            os.getenv("AGENT_DECISION_MAX_CHARS"), 4000, 500, 6000
        )
        self.decision_max_chars = configured_decision_max
        self.debug = debug if debug is not None else _parse_bool(os.getenv("AGENT_DEBUG"), False)
        self.enable_agent = enable_agent if enable_agent is not None else _parse_bool(os.getenv("ENABLE_AGENT"), True)

    def run(self, *, user_query: str, context: AgentContext) -> AgentResponse:
        sanitized_query = (user_query or "").strip()
        if not sanitized_query:
            return AgentResponse(answer="I couldn't understand the input. Please provide text, an image of a bill, or a voice message.")

        observations: list[AgentObservation] = []
        trace: list[dict[str, Any]] = []
        seen_calls: set[str] = set()
        planner_mode = "fallback" if not self.enable_agent else "llm"

        for step in range(1, self.max_steps + 1):
            tool_definitions = self.tool_registry.definitions(context)
            action, current_mode = self._decide_action(
                user_query=sanitized_query,
                context=context,
                observations=observations,
                tool_definitions=tool_definitions,
            )
            planner_mode = planner_mode if planner_mode == "fallback" else current_mode

            if action.action == "final_answer":
                answer = self._clean_answer(action.final_answer) or self._fallback_answer(sanitized_query, observations)
                return AgentResponse(answer=answer, trace=self._build_trace(trace, planner_mode))

            try:
                duplicate_key = self.tool_registry.duplicate_key(action.tool_name or "", action.tool_input)
            except Exception:
                duplicate_key = ""
            if duplicate_key and duplicate_key in seen_calls:
                observation = AgentObservation(
                    step=step,
                    tool_name=action.tool_name or "unknown",
                    status="skipped",
                    result="Repeated equivalent tool call was blocked.",
                )
                observations.append(observation)
                trace.append(self._trace_row(observation, planner_mode, "Duplicate tool call blocked."))
                break

            if duplicate_key:
                seen_calls.add(duplicate_key)

            execution = self.tool_registry.execute(action.tool_name or "", action.tool_input, context)
            observation = AgentObservation(
                step=step,
                tool_name=execution.tool_name,
                status=execution.status,
                result=execution.result,
            )
            observations.append(observation)
            trace.append(self._trace_row(observation, planner_mode, execution.summary, execution.duration_ms))

        answer = self._synthesize_answer(sanitized_query, observations, context.conversation_history)
        return AgentResponse(answer=answer, trace=self._build_trace(trace, planner_mode))

    def _decide_action(
        self,
        *,
        user_query: str,
        context: AgentContext,
        observations: list[AgentObservation],
        tool_definitions: list[dict[str, Any]],
    ) -> tuple[AgentAction, str]:
        if self.enable_agent:
            action = self._llm_action(
                user_query=user_query,
                conversation_history=context.conversation_history,
                observations=observations,
                tool_definitions=tool_definitions,
            )
            if action is not None:
                return action, "llm"
        return self._fallback_action(user_query=user_query, observations=observations, has_bill_data=bool(context.bill_data)), "fallback"

    def _llm_action(
        self,
        *,
        user_query: str,
        conversation_history: list[dict[str, str]],
        observations: list[AgentObservation],
        tool_definitions: list[dict[str, Any]],
    ) -> AgentAction | None:
        try:
            return self.llm_client.decide_agent_action(
                user_query=user_query,
                conversation_history=conversation_history,
                tool_definitions=tool_definitions,
                observations=observations,
            )
        except Exception:
            return None

    def _fallback_action(self, *, user_query: str, observations: list[AgentObservation], has_bill_data: bool) -> AgentAction:
        lower = user_query.lower()
        called_tools = [obs.tool_name for obs in observations if obs.status != "skipped"]
        classification = self.classifier_service.classify(user_query)

        if not observations and self._is_casual(lower):
            return AgentAction(action="final_answer", final_answer="Hello! How can I help with your transactions, GST, calculations, or bills?")

        if has_bill_data and not observations and re.search(r"\b(bill|invoice|receipt|summary|summarize)\b", lower):
            return AgentAction(action="call_tool", tool_name="summarize_bill", tool_input={"intent": "Summarize this bill"})

        calc_input = self.calculator_service.parse_query_text(user_query)
        if calc_input and "calculate_financial_metric" not in called_tools:
            return AgentAction(action="call_tool", tool_name="calculate_financial_metric", tool_input=calc_input)

        wants_transactions = classification["query_type"] in {"sql", "mixed"} or bool(
            re.search(r"\b(transaction|transactions|expense|expenses|sales|purchase|profit|loss|amount|total|spent|income)\b", lower)
        )
        wants_gst = classification["query_type"] in {"general", "mixed"} and bool(
            re.search(r"\b(gst|cgst|sgst|igst|tax|input tax credit|itc|slab|rule|rate)\b", lower)
        ) or bool(re.search(r"\b(gst|cgst|sgst|igst|tax|input tax credit|itc|slab|rule|rate)\b", lower))

        if wants_transactions and "query_transactions" not in called_tools:
            return AgentAction(action="call_tool", tool_name="query_transactions", tool_input={"query": user_query[:300]})
        if wants_gst and "search_gst_knowledge" not in called_tools:
            gst_query = user_query[:300]
            return AgentAction(action="call_tool", tool_name="search_gst_knowledge", tool_input={"query": gst_query, "n_results": 3})

        return AgentAction(action="final_answer", final_answer=self._fallback_answer(user_query, observations))

    def _synthesize_answer(
        self,
        user_query: str,
        observations: list[AgentObservation],
        conversation_history: list[dict[str, str]],
    ) -> str:
        try:
            answer = self.llm_client.synthesize_agent_answer(
                user_query=user_query,
                observations=observations,
                conversation_history=conversation_history,
            )
            clean = self._clean_answer(answer)
            if clean:
                return clean
        except Exception:
            pass
        return self._fallback_answer(user_query, observations)

    def _fallback_answer(self, user_query: str, observations: list[AgentObservation]) -> str:
        successful = [obs for obs in observations if obs.status == "success" and obs.result]
        if successful:
            if len(successful) == 1:
                return successful[0].result
            return " ".join(obs.result for obs in successful)
        if self._is_casual(user_query.lower()):
            return "Hello! How can I help with your transactions, GST, calculations, or bills?"
        return "I could not complete that request right now. Please try again with a more specific question."

    @staticmethod
    def parse_action_json(raw_text: str) -> AgentAction:
        candidate = VyaparSathiAgent._extract_json_object(raw_text)
        if not candidate:
            raise ValueError("No JSON object found.")
        data = json.loads(candidate)
        action = AgentAction.model_validate(data)
        if action.tool_name and action.tool_name not in ALLOWED_TOOL_NAMES:
            raise ValueError("Unknown tool.")
        return action

    @staticmethod
    def _extract_json_object(raw_text: str) -> str | None:
        text = (raw_text or "").strip()
        if not text:
            return None
        fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
        if fence_match:
            return fence_match.group(1).strip()
        if text.startswith("{") and text.endswith("}"):
            return text
        start = text.find("{")
        if start == -1:
            return None
        depth = 0
        in_string = False
        escape = False
        for index in range(start, len(text)):
            char = text[index]
            if escape:
                escape = False
                continue
            if char == "\\":
                escape = True
                continue
            if char == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return text[start : index + 1]
        return None

    def _clean_answer(self, answer: str | None) -> str:
        clean = " ".join((answer or "").split())
        if not clean:
            return ""
        return clean[: self.decision_max_chars].strip()

    def _trace_row(self, observation: AgentObservation, planner_mode: str, summary: str, duration_ms: int | None = None) -> dict[str, Any]:
        row: dict[str, Any] = {
            "step": observation.step,
            "tool": observation.tool_name,
            "status": observation.status,
            "summary": summary[:160] if summary else "",
            "planner_mode": planner_mode,
        }
        if duration_ms is not None:
            row["duration_ms"] = duration_ms
        return row

    def _build_trace(self, rows: list[dict[str, Any]], planner_mode: str) -> list[dict[str, Any]]:
        if self.debug:
            return [{"planner_mode": planner_mode, "steps": rows}]
        return rows

    @staticmethod
    def _is_casual(lower: str) -> bool:
        stripped = lower.strip()
        return stripped in {"hello", "hi", "hey", "ok", "okay"} or bool(re.fullmatch(r"(hello|hi|hey)[!. ]*", stripped))
