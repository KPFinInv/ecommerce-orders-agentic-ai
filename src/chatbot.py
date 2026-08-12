"""LangGraph-based order-query agent with deterministic and optional LLM modes."""

from __future__ import annotations

import json
import operator
import os
import re
from datetime import date, datetime
from typing import Annotated, Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from .data import customer_owns_order, get_order, list_customer_orders


Intent = Literal["order_status", "order_list", "return_help", "product_help", "unsupported"]


class AgentState(TypedDict, total=False):
    query: str
    customer_id: int | None
    order_id: str | None
    intent: Intent
    authorized: bool
    order: dict[str, Any] | None
    orders: list[dict[str, Any]]
    policy: dict[str, Any]
    response: str
    trace: Annotated[list[dict[str, str]], operator.add]
    mode: str
    error: str | None


def _event(node: str, detail: str) -> dict[str, str]:
    return {"node": node, "detail": detail}


def _extract_ids(query: str) -> tuple[int | None, str | None]:
    customer_match = re.search(r"(?:customer|cust(?:omer)?\s*id)\s*[:#-]?\s*(\d+)", query, re.I)
    order_match = re.search(r"\bORD\s*[-#]?\s*(\d{4})\b", query, re.I)
    customer_id = int(customer_match.group(1)) if customer_match else None
    order_id = f"ORD{order_match.group(1)}" if order_match else None
    return customer_id, order_id


def _deterministic_intent(query: str, order_id: str | None) -> Intent:
    text = query.lower()
    if any(word in text for word in ("return", "replace", "damaged", "broken", "defective")):
        return "return_help"
    if any(word in text for word in ("warranty", "spec", "product", "item")):
        return "product_help"
    if any(word in text for word in ("all orders", "my orders", "order list", "orders have")):
        return "order_list"
    if order_id or any(word in text for word in ("status", "arrive", "delivery", "track", "where")):
        return "order_status"
    return "unsupported"


def _llm_classification(query: str) -> dict[str, Any] | None:
    """Use an LLM only when configured; return None on any provider failure."""
    if not os.getenv("OPENAI_API_KEY"):
        return None
    try:
        from langchain_openai import ChatOpenAI

        model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
        llm = ChatOpenAI(model=model, temperature=0).with_structured_output(
            {
                "title": "OrderQueryClassification",
                "description": "Classify an e-commerce order support request.",
                "type": "object",
                "properties": {
                    "intent": {
                        "type": "string",
                        "enum": ["order_status", "order_list", "return_help", "product_help", "unsupported"],
                    },
                    "customer_id": {"type": ["integer", "null"]},
                    "order_id": {"type": ["string", "null"]},
                },
                "required": ["intent", "customer_id", "order_id"],
                "additionalProperties": False,
            }
        )
        return llm.invoke(
            "Extract identifiers and classify this Kartify support request. "
            "Order IDs use ORD followed by four digits. Request: " + query
        )
    except Exception:
        return None


def guardrail_node(state: AgentState) -> AgentState:
    query = (state.get("query") or "").strip()
    blocked = any(token in query.lower() for token in ("drop table", "delete from", "insert into", "update orders"))
    if not query:
        return {"error": "Please enter a question.", "trace": [_event("guardrail", "Rejected an empty request.")]}
    if blocked:
        return {
            "error": "I can answer order questions, but I cannot modify the database.",
            "trace": [_event("guardrail", "Blocked a database-write instruction.")],
        }
    return {"trace": [_event("guardrail", "Input accepted; no write instruction detected.")]}


def classify_node(state: AgentState) -> AgentState:
    llm_result = _llm_classification(state["query"]) if state.get("mode") == "LLM-assisted" else None
    regex_customer, regex_order = _extract_ids(state["query"])
    if llm_result:
        intent = llm_result["intent"]
        customer_id = llm_result.get("customer_id") or regex_customer
        order_id = (llm_result.get("order_id") or regex_order)
        if order_id:
            order_id = re.sub(r"[^A-Z0-9]", "", order_id.upper())
        method = "LLM structured output"
    else:
        intent = _deterministic_intent(state["query"], regex_order)
        customer_id, order_id = regex_customer, regex_order
        method = "deterministic fallback"
    detail = f"Intent={intent}; customer_id={customer_id}; order_id={order_id}; via {method}."
    return {
        "intent": intent,
        "customer_id": customer_id,
        "order_id": order_id,
        "trace": [_event("classify", detail)],
    }


def authorize_node(state: AgentState) -> AgentState:
    customer_id, order_id = state.get("customer_id"), state.get("order_id")
    if state.get("intent") == "order_list":
        allowed = customer_id is not None
        detail = "Customer identifier supplied for scoped order lookup." if allowed else "Customer identifier is missing."
    elif order_id and customer_id is not None:
        allowed = customer_owns_order(customer_id, order_id)
        detail = "Ownership verified." if allowed else "Ownership check failed."
    else:
        allowed = False
        detail = "Both customer ID and order ID are required for this request."
    return {"authorized": allowed, "trace": [_event("authorize", detail)]}


def retrieve_node(state: AgentState) -> AgentState:
    if not state.get("authorized"):
        return {"trace": [_event("retrieve", "Skipped because authorization did not pass.")]}
    if state.get("intent") == "order_list":
        orders = list_customer_orders(state["customer_id"])
        return {"orders": orders, "trace": [_event("retrieve", f"Retrieved {len(orders)} scoped order(s).")]}
    order = get_order(state["order_id"])
    return {"order": order, "trace": [_event("retrieve", "Retrieved one joined order record." if order else "No matching order found.")]}


def policy_node(state: AgentState) -> AgentState:
    order = state.get("order")
    if state.get("intent") != "return_help" or not order:
        return {"policy": {}, "trace": [_event("policy", "No return-policy calculation required.")]}
    order_day = datetime.strptime(order["order_date"], "%Y-%m-%d").date()
    max_days = max(int(re.search(r"\d+", item["return_policy"]).group()) for item in order["items"])
    age_days = (date.today() - order_day).days
    eligible = order["status"] not in {"Cancelled", "Returned"} and age_days <= max_days
    policy = {"age_days": age_days, "window_days": max_days, "eligible": eligible}
    detail = f"Order age={age_days} days; maximum item window={max_days} days; eligible={eligible}."
    return {"policy": policy, "trace": [_event("policy", detail)]}


def respond_node(state: AgentState) -> AgentState:
    if state.get("error"):
        return {"response": state["error"], "trace": [_event("respond", "Returned a safe refusal or clarification.")]}
    if not state.get("authorized"):
        if state.get("intent") == "order_list":
            text = "Please include your customer ID, for example: ‘Show orders for customer 3’."
        else:
            text = "Please include both your customer ID and order ID so I can verify access, for example: ‘Customer 3, status of ORD1004’."
        return {"response": text, "trace": [_event("respond", "Requested the minimum identifiers needed for authorization.")]}
    if state.get("intent") == "order_list":
        orders = state.get("orders", [])
        if not orders:
            text = f"I could not find orders for customer {state['customer_id']}."
        else:
            lines = [f"• {o['order_id']}: {o['status']} — ${o['total_amount']:,.2f}" for o in orders]
            text = f"I found {len(orders)} order(s) for customer {state['customer_id']}:\n" + "\n".join(lines)
        return {"response": text, "trace": [_event("respond", "Formatted a customer-scoped order list.")]}
    order = state.get("order")
    if not order:
        return {"response": "I could not find that order.", "trace": [_event("respond", "Reported a not-found result.")]}
    if state.get("intent") == "return_help":
        policy = state.get("policy", {})
        decision = "appears eligible" if policy.get("eligible") else "does not appear eligible"
        text = (
            f"Order {order['order_id']} {decision} for a return under the sample policy. "
            f"The order is {policy.get('age_days')} days old and the widest item return window is "
            f"{policy.get('window_days')} days. A human agent should confirm condition and exceptions."
        )
    elif state.get("intent") == "product_help":
        products = ", ".join(f"{i['name']} ({i['warranty_period']} warranty)" for i in order["items"])
        text = f"Order {order['order_id']} contains: {products}."
    else:
        delivery = order["delivery_date"] or "not yet assigned"
        text = (
            f"Order {order['order_id']} is currently {order['status']}. "
            f"Delivery date: {delivery}. Total: ${order['total_amount']:,.2f}."
        )
    return {"response": text, "trace": [_event("respond", "Generated a grounded response from retrieved fields.")]}


def route_after_guardrail(state: AgentState) -> str:
    return "respond" if state.get("error") else "classify"


def build_graph():
    """Compile the teaching workflow into an executable LangGraph graph."""
    builder = StateGraph(AgentState)
    builder.add_node("guardrail", guardrail_node)
    builder.add_node("classify", classify_node)
    builder.add_node("authorize", authorize_node)
    builder.add_node("retrieve", retrieve_node)
    builder.add_node("policy", policy_node)
    builder.add_node("respond", respond_node)
    builder.add_edge(START, "guardrail")
    builder.add_conditional_edges("guardrail", route_after_guardrail, {"classify": "classify", "respond": "respond"})
    builder.add_edge("classify", "authorize")
    builder.add_edge("authorize", "retrieve")
    builder.add_edge("retrieve", "policy")
    builder.add_edge("policy", "respond")
    builder.add_edge("respond", END)
    return builder.compile()


GRAPH = build_graph()


def ask(query: str, mode: str = "Deterministic demo") -> AgentState:
    """Invoke the graph with a clean initial state."""
    return GRAPH.invoke({"query": query, "mode": mode, "trace": []})


def trace_as_json(result: AgentState) -> str:
    return json.dumps(result.get("trace", []), indent=2)
