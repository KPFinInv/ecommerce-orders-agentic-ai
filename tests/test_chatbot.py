from kartify_agent import FeedbackStore, SupportSession, ask, benchmark_summary, run_benchmark


def test_identity_and_order_context_persist_across_turns():
    session = SupportSession(2)
    first = session.ask("Where is my latest order?")
    second = session.ask("What products are in it?")

    assert first["active_order_id"] == "ORD1003"
    assert second["active_order_id"] == "ORD1003"
    assert second["order_reference_source"] == "conversation_memory"
    assert "Portable Blender" in second["response"]


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
