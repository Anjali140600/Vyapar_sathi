from app.agents.models import AgentContext
from app.agents.tool_registry import AgentToolRegistry


class FakeDataService:
    def __init__(self):
        self.calls = []

    def answer_sql_query(self, db, query_text, user_id):
        self.calls.append({"db": db, "query_text": query_text, "user_id": user_id})
        return "Transaction answer"


class FakeRAGService:
    def __init__(self):
        self.calls = []

    def query(self, query_text, n_results=3):
        self.calls.append({"query_text": query_text, "n_results": n_results})
        return ["GST doc"]

    def build_concise_answer(self, query_text, docs, max_lines=3):
        return f"GST answer for {query_text}"


class FakeCalculatorService:
    def __init__(self):
        self.calls = []

    def calculate(self, **kwargs):
        self.calls.append(kwargs)
        if kwargs.get("operation") == "bad":
            raise ValueError("bad input")
        return {"message": "Calculated safely"}


def make_context(bill_data=None):
    return AgentContext(
        db=object(),
        user_id="trusted-user",
        conversation_history=[],
        bill_data=bill_data,
    )


def test_reject_unknown_tools():
    registry = AgentToolRegistry(
        data_service=FakeDataService(),
        rag_service=FakeRAGService(),
        financial_calculator_service=FakeCalculatorService(),
    )
    result = registry.execute("unknown_tool", {}, make_context())
    assert result.status == "error"


def test_query_transactions_injects_trusted_user_id():
    data_service = FakeDataService()
    registry = AgentToolRegistry(
        data_service=data_service,
        rag_service=FakeRAGService(),
        financial_calculator_service=FakeCalculatorService(),
    )
    registry.execute(
        "query_transactions",
        {"query": "my expenses", "user_id": "attacker"},
        make_context(),
    )
    assert data_service.calls[0]["user_id"] == "trusted-user"


def test_calls_correct_mocked_service():
    data_service = FakeDataService()
    registry = AgentToolRegistry(
        data_service=data_service,
        rag_service=FakeRAGService(),
        financial_calculator_service=FakeCalculatorService(),
    )
    result = registry.execute("query_transactions", {"query": "my expenses"}, make_context())
    assert result.status == "success"
    assert data_service.calls[0]["query_text"] == "my expenses"


def test_clamps_rag_result_count():
    rag_service = FakeRAGService()
    registry = AgentToolRegistry(
        data_service=FakeDataService(),
        rag_service=rag_service,
        financial_calculator_service=FakeCalculatorService(),
    )
    registry.execute("search_gst_knowledge", {"query": "itc", "n_results": 99}, make_context())
    assert rag_service.calls[0]["n_results"] == 5


def test_rejects_unsafe_calculator_inputs():
    registry = AgentToolRegistry(
        data_service=FakeDataService(),
        rag_service=FakeRAGService(),
        financial_calculator_service=FakeCalculatorService(),
    )
    result = registry.execute(
        "calculate_financial_metric",
        {"operation": "gst_amount", "amount": 1000, "rate_percent": "NaN"},
        make_context(),
    )
    assert result.status == "error"


def test_handles_tool_exceptions_safely():
    registry = AgentToolRegistry(
        data_service=FakeDataService(),
        rag_service=FakeRAGService(),
        financial_calculator_service=FakeCalculatorService(),
    )
    result = registry.execute("calculate_financial_metric", {"operation": "bad"}, make_context())
    assert result.status == "error"
    assert "safely" in result.result.lower()


def test_refuses_bill_summary_without_bill_context():
    registry = AgentToolRegistry(
        data_service=FakeDataService(),
        rag_service=FakeRAGService(),
        financial_calculator_service=FakeCalculatorService(),
    )
    result = registry.execute("summarize_bill", {}, make_context())
    assert result.status == "error"


def test_truncates_oversized_output():
    class LongDataService(FakeDataService):
        def answer_sql_query(self, db, query_text, user_id):
            return "x" * 5000

    registry = AgentToolRegistry(
        data_service=LongDataService(),
        rag_service=FakeRAGService(),
        financial_calculator_service=FakeCalculatorService(),
        observation_max_chars=300,
    )
    result = registry.execute("query_transactions", {"query": "my expenses"}, make_context())
    assert len(result.result) <= 300
