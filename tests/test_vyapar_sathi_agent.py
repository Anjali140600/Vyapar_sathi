from app.agents.models import AgentAction, AgentContext
from app.agents.tool_registry import AgentToolRegistry
from app.agents.vyapar_sathi_agent import VyaparSathiAgent
from app.services.chat_orchestrator import ChatOrchestrator


class FakeDataService:
    def answer_sql_query(self, db, query_text, user_id):
        return "Your total expenses this month are Rs. 5,000.00."


class FakeRAGService:
    def query(self, query_text, n_results=3):
        return ["Input tax credit allows eligible GST set-off."]

    def build_concise_answer(self, query_text, docs, max_lines=3):
        return "Input tax credit allows eligible GST set-off."


class FakeCalculatorService:
    def calculate(self, **kwargs):
        return {"message": "GST: Rs. 180.00. Total including GST: Rs. 1,180.00."}

    def parse_query_text(self, query_text):
        if "1000" in query_text and "18" in query_text:
            return {"operation": "total_with_gst", "amount": 1000, "rate_percent": 18}
        return None


class FakeLLM:
    def __init__(self, actions=None, fail_decision=False, synthesize_text="Synthesized answer"):
        self.actions = list(actions or [])
        self.fail_decision = fail_decision
        self.synthesize_text = synthesize_text
        self.repair_attempts = 0

    def decide_agent_action(self, **kwargs):
        if self.fail_decision:
            self.repair_attempts += 1
            raise ValueError("invalid json")
        if not self.actions:
            return AgentAction(action="final_answer", final_answer="General response")
        return self.actions.pop(0)

    def synthesize_agent_answer(self, **kwargs):
        return self.synthesize_text


def make_agent(llm):
    registry = AgentToolRegistry(
        data_service=FakeDataService(),
        rag_service=FakeRAGService(),
        financial_calculator_service=FakeCalculatorService(),
    )
    return VyaparSathiAgent(
        llm_client=llm,
        tool_registry=registry,
        calculator_service=FakeCalculatorService(),
        enable_agent=True,
        max_steps=4,
    )


def make_context(bill_data=None):
    return AgentContext(db=object(), user_id="user-1", conversation_history=[], bill_data=bill_data)


def test_transaction_query_uses_query_transactions():
    llm = FakeLLM(
        actions=[
            AgentAction(action="call_tool", tool_name="query_transactions", tool_input={"query": "What are my total expenses this month?"}),
            AgentAction(action="final_answer", final_answer="Your total expenses this month are Rs. 5,000.00."),
        ]
    )
    response = make_agent(llm).run(user_query="What are my total expenses this month?", context=make_context())
    assert response.answer.startswith("Your total expenses")
    assert response.trace[0]["tool"] == "query_transactions"


def test_gst_query_uses_search_gst_knowledge():
    llm = FakeLLM(
        actions=[
            AgentAction(action="call_tool", tool_name="search_gst_knowledge", tool_input={"query": "What is input tax credit?", "n_results": 3}),
            AgentAction(action="final_answer", final_answer="Input tax credit allows eligible GST set-off."),
        ]
    )
    response = make_agent(llm).run(user_query="What is input tax credit?", context=make_context())
    assert response.trace[0]["tool"] == "search_gst_knowledge"


def test_mixed_query_sequences_two_tools_then_final():
    llm = FakeLLM(
        actions=[
            AgentAction(action="call_tool", tool_name="query_transactions", tool_input={"query": "What were my expenses this month?"}),
            AgentAction(action="call_tool", tool_name="search_gst_knowledge", tool_input={"query": "what GST rule applies?", "n_results": 3}),
            AgentAction(action="final_answer", final_answer="Here is the combined answer."),
        ]
    )
    response = make_agent(llm).run(
        user_query="What were my expenses this month and what GST rule applies?",
        context=make_context(),
    )
    assert [step["tool"] for step in response.trace] == ["query_transactions", "search_gst_knowledge"]


def test_calculation_query_uses_calculator():
    agent = make_agent(FakeLLM(fail_decision=True))
    response = agent.run(user_query="Calculate GST on Rs. 1000 at 18%.", context=make_context())
    assert response.trace[0]["tool"] == "calculate_financial_metric"


def test_bill_summary_uses_bill_tool():
    agent = make_agent(FakeLLM(fail_decision=True))
    response = agent.run(
        user_query="Summarize this bill.",
        context=make_context(bill_data={"amount": 1200, "date": "2026-07-31", "category": "Food", "raw_text": "Sample bill"}),
    )
    assert response.trace[0]["tool"] == "summarize_bill"


def test_casual_query_can_finalize_without_tool():
    response = make_agent(FakeLLM(actions=[AgentAction(action="final_answer", final_answer="Hello!")] )).run(
        user_query="Hello",
        context=make_context(),
    )
    assert response.answer == "Hello!"


def test_invalid_llm_json_uses_fallback_after_one_attempt():
    agent = make_agent(FakeLLM(fail_decision=True))
    response = agent.run(user_query="What is input tax credit?", context=make_context())
    assert response.trace[0]["planner_mode"] == "fallback"


def test_duplicate_tool_call_is_blocked():
    llm = FakeLLM(
        actions=[
            AgentAction(action="call_tool", tool_name="query_transactions", tool_input={"query": "expenses"}),
            AgentAction(action="call_tool", tool_name="query_transactions", tool_input={"query": "expenses"}),
        ],
        synthesize_text="Finalized after duplicate block",
    )
    response = make_agent(llm).run(user_query="expenses", context=make_context())
    assert response.trace[-1]["status"] == "skipped"


def test_maximum_steps_returns_final_answer():
    llm = FakeLLM(
        actions=[
            AgentAction(action="call_tool", tool_name="query_transactions", tool_input={"query": "expenses"}),
            AgentAction(action="call_tool", tool_name="search_gst_knowledge", tool_input={"query": "gst", "n_results": 3}),
            AgentAction(action="call_tool", tool_name="calculate_financial_metric", tool_input={"operation": "total_with_gst", "amount": 1000, "rate_percent": 18}),
            AgentAction(action="call_tool", tool_name="query_transactions", tool_input={"query": "expenses again"}),
        ],
        synthesize_text="Synthesized after max steps",
    )
    agent = make_agent(llm)
    response = agent.run(user_query="complex question", context=make_context())
    assert response.answer == "Synthesized after max steps"


def test_llm_unavailable_fallback_still_answers_supported_query():
    agent = make_agent(FakeLLM(fail_decision=True))
    response = agent.run(user_query="What are my total expenses this month?", context=make_context())
    assert "expenses" in response.answer.lower()


def test_no_successful_observations_returns_safe_failure():
    llm = FakeLLM(actions=[AgentAction(action="call_tool", tool_name="summarize_bill", tool_input={})], synthesize_text="")
    response = make_agent(llm).run(user_query="Summarize this bill.", context=make_context())
    assert response.answer


def test_chat_orchestrator_process_input_returns_string():
    orchestrator = ChatOrchestrator.__new__(ChatOrchestrator)
    orchestrator.process_input_with_trace = lambda **kwargs: type("Response", (), {"answer": "string answer"})()
    assert isinstance(orchestrator.process_input(text="Hello"), str)
