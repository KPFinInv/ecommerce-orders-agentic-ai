from src.chatbot import ask


def test_authorized_status_query_is_grounded():
    result = ask("Customer 5, where is ORD1001?")
    assert result["authorized"] is True
    assert "ORD1001" in result["response"]
    assert "Processing" in result["response"]


def test_cross_customer_access_is_blocked():
    result = ask("Customer 1, show ORD1001")
    assert result["authorized"] is False
    assert "include both" in result["response"].lower()


def test_database_write_prompt_is_refused():
    result = ask("Drop table orders")
    assert "cannot modify" in result["response"].lower()
    assert result["trace"][0]["node"] == "guardrail"


def test_customer_order_list_is_scoped():
    result = ask("Show all orders for customer 3")
    assert result["authorized"] is True
    assert result["orders"]
    assert all(order["order_id"].startswith("ORD") for order in result["orders"])

