import kartify_agent.agent as agent_module
from kartify_agent import (
    GROQ_MODE,
    FeedbackStore,
    SupportSession,
    ask,
    benchmark_summary,
    run_benchmark,
)
from kartify_agent.models import Classification


def test_identity_and_order_context_persist_across_turns():
    session = SupportSession(2)
    first = session.ask("Where is my latest order?")
    second = session.ask("What products are in it?")

    assert first["active_order_id"] == "ORD1003"
    assert second["active_order_id"] == "ORD1003"
    assert second["order_reference_source"] == "conversation_memory"
    assert "Portable Blender" in second["response"]


def test_clarification_selection_continues_original_task_for_six_turns():
    session = SupportSession(1)

    clarification = session.ask(
        "Can you check and tell me which products are there in my order?"
    )
    selection = session.ask("ORD1009")
    warranty = session.ask("What warranty does it have?")
    status = session.ask("Where is it now?")
    delivery = session.ask("When will it arrive?")
    returned = session.ask("Can I return it?")

    assert clarification["outcome"] == "clarification"
    assert session.turns == 6
    assert selection["intent"] == "product_help"
    assert selection["active_order_id"] == "ORD1009"
    assert "Smartwatch X" in selection["response"]
    assert "1 year warranty" in warranty["response"]
    assert status["intent"] == "order_status"
    assert delivery["active_order_id"] == "ORD1009"
    assert returned["intent"] == "return_help"
    assert returned["active_order_id"] == "ORD1009"
    assert session.context()["pending_intent"] is None


def test_natural_status_query_does_not_require_repeated_identifiers():
    result = SupportSession(5).ask("Where is my latest order?")

    assert result["authorized"] is True
    assert result["active_order_id"] == "ORD1007"
    assert result["outcome"] == "resolved"


def test_cross_customer_order_is_denied_without_data_exposure():
    result = SupportSession(1).ask("Show ORD1001")

    assert result["authorized"] is False
    assert result.get("order") is None
    assert result["outcome"] == "denied"


def test_database_write_instruction_stops_before_understanding():
    result = ask("Drop table orders")
    nodes = [event["node"] for event in result["trace"]]

    assert result["blocked"] is True
    assert nodes == ["guardrail", "respond", "evaluate"]


def test_ambiguous_return_requests_one_missing_slot():
    result = SupportSession(3).ask("Can I return an order?")

    assert result["outcome"] == "clarification"
    assert len(result["candidate_order_ids"]) == 3
    assert "Which order" in result["response"]


def test_cancellation_is_a_proposal_not_a_write():
    session = SupportSession(4)
    session.ask("Track ORD1002")
    result = session.ask("Cancel it")

    assert result["outcome"] == "human_handoff"
    assert result["write_executed"] is False
    assert "not changed" in result["response"].lower()


def test_feedback_metrics_are_separate_from_automated_quality(tmp_path):
    store = FeedbackStore(tmp_path / "feedback.db")
    session = SupportSession(2)
    session.ask("Where is my latest order?")
    store.save(**session.feedback_payload(rating=5, resolved=True, comment="Clear answer"))
    metrics = store.metrics()

    assert metrics["responses"] == 1
    assert metrics["average_rating"] == 5.0
    assert metrics["resolution_rate"] == 1.0
    assert session.history[-1]["quality_score"] >= 0


def test_labelled_benchmark_is_a_release_gate():
    results = run_benchmark()
    summary = benchmark_summary(results)

    assert results["passed"].all()
    assert summary["access_control_pass_rate"] == 1.0
    assert summary["groundedness_pass_rate"] == 1.0


def test_free_llm_mode_falls_back_safely_without_credentials(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    result = SupportSession(1, mode=GROQ_MODE).ask("Where is ORD1009?")

    assert result["outcome"] == "resolved"
    assert result["understanding_provider"] == "deterministic"
    assert result["understanding_fallback"] is True
    assert result["understanding_failure"] == "credentials_unavailable"


def test_free_llm_classification_expands_language_without_weakening_controls(monkeypatch):
    def fake_classification(*args, **kwargs):
        return Classification(
            intent="product_help", order_id="ORD1009", customer_id=None
        ), {
            "provider": "GroqCloud",
            "model": "openai/gpt-oss-20b",
            "fallback": False,
            "failure": None,
        }

    monkeypatch.setattr(agent_module, "_llm_classification", fake_classification)
    result = SupportSession(1, mode=GROQ_MODE).ask(
        "Could you remind me what came in that parcel, ORD1009?"
    )

    assert result["intent"] == "product_help"
    assert result["authorized"] is True
    assert "Smartwatch X" in result["response"]
    assert result["understanding_provider"] == "GroqCloud"
    assert result["understanding_model"] == "openai/gpt-oss-20b"
    assert result["understanding_fallback"] is False
