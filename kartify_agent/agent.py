"""Context-aware LangGraph support agent with evaluation and session memory."""

from __future__ import annotations

import os
import re
import time
import uuid
from datetime import date, datetime
from typing import Any

from langgraph.graph import END, START, StateGraph
from rapidfuzz import fuzz

from .models import AgentState, Classification, Intent, TraceEvent
from .repository import (
    customer_owns_order,
    get_customer,
    get_order,
    list_customer_orders,
)


POLICY_AS_OF = date.fromisoformat(os.getenv("KARTIFY_POLICY_DATE", "2025-10-31"))

ARCHITECTURE_MERMAID = """flowchart TD
    UI[Streamlit / Notebook] --> SESSION[Demo identity + conversation session]
    SESSION --> G[Input guardrail]
    G -->|safe| U[Intent + entity understanding]
    G -->|blocked| R[Grounded response]
    U --> C[Context resolver]
    C -->|needs one slot| R
    C --> A[Object-level authorization]
    A -->|denied| T[Tool router / safe skip]
    A -->|allowed| T
    T --> O[(Orders tool)]
    T --> P[(Products evidence)]
    T --> Y[Policy engine]
    O --> Y
    P --> Y
    Y --> R
    R --> E[Response critic + quality signals]
    E --> M[Session memory]
    E --> UI
    UI --> F[Customer rating + resolution feedback]
    F --> Q[(Quality analytics)]
"""


def _event(
    node: str,
    decision: str,
    detail: str,
    *,
    started: float | None = None,
    data_used: list[str] | None = None,
) -> TraceEvent:
    return {
        "node": node,
        "decision": decision,
        "detail": detail,
        "duration_ms": round((time.perf_counter() - started) * 1000, 2)
        if started
        else 0.0,
        "data_used": data_used or [],
    }


def _extract_customer_id(query: str) -> int | None:
    match = re.search(r"(?:customer|customer\s*id|cid)\s*[:#-]?\s*(\d+)", query, re.I)
    return int(match.group(1)) if match else None


def _extract_order_id(query: str) -> str | None:
    match = re.search(r"\bORD\s*[-#]?\s*(\d{4})\b", query, re.I)
    return f"ORD{match.group(1)}" if match else None


def _deterministic_intent(query: str, previous_intent: Intent | None) -> Intent:
    text = query.lower().strip()
    if any(term in text for term in ("bye", "goodbye", "end conversation", "that's all", "thats all")):
        return "end_conversation"
    if any(term in text for term in ("cancel", "stop the order", "refund now")):
        return "cancel_request"
    if any(term in text for term in ("return", "replace", "damaged", "broken", "defective")):
        return "return_help"
    if any(term in text for term in ("product", "item", "warranty", "what did i buy", "what is in")):
        return "product_help"
    if any(term in text for term in ("all orders", "my orders", "order history", "list orders")):
        return "order_list"
    if any(
        term in text
        for term in (
            "status",
            "arrive",
            "delivery",
            "track",
            "where is",
            "when will",
            "shipped",
            "shipping",
            "processing",
            "delivered",
        )
    ):
        return "order_status"
    if len(text.split()) <= 4 and any(term in text for term in ("it", "that", "this order")):
        return previous_intent or "order_status"
    return "general_help"


def _llm_classification(query: str) -> Classification | None:
    """Classify variable language only when optional model credentials exist."""
    if not os.getenv("OPENAI_API_KEY"):
        return None
    try:
        from langchain_openai import ChatOpenAI

        model = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"), temperature=0
        ).with_structured_output(Classification)
        return model.invoke(
            "Classify this e-commerce support turn. Extract only explicit identifiers. "
            f"Request: {query}"
        )
    except Exception:
        return None


def guardrail_node(state: AgentState) -> AgentState:
    started = time.perf_counter()
    query = (state.get("query") or "").strip()
    blocked_patterns = (
        "drop table",
        "delete from",
        "insert into",
        "update orders",
        "bypass authorization",
        "ignore previous instructions",
        "reveal system prompt",
    )
    if not query:
        return {
            "blocked": False,
            "error": "Please enter a question.",
            "error_code": "empty_input",
            "outcome": "clarification",
            "trace": [_event("guardrail", "reject", "Rejected an empty request.", started=started)],
        }
    matched = next((pattern for pattern in blocked_patterns if pattern in query.lower()), None)
    if matched:
        return {
            "blocked": True,
            "error": "I can help with order information, but I cannot execute or bypass protected operations.",
            "error_code": "unsafe_instruction",
            "outcome": "blocked",
            "trace": [
                _event(
                    "guardrail",
                    "block",
                    f"Blocked unsafe instruction pattern: {matched!r}.",
                    started=started,
                )
            ],
        }
    return {
        "blocked": False,
        "error": None,
        "trace": [_event("guardrail", "allow", "Input accepted.", started=started)],
    }


def understand_node(state: AgentState) -> AgentState:
    started = time.perf_counter()
    query = state["query"]
    explicit_order = _extract_order_id(query)
    claimed_customer = _extract_customer_id(query)
    bare_order_selection = bool(
        explicit_order
        and re.fullmatch(
            r"\s*(?:order\s*)?ORD\s*[-#]?\s*\d{4}\s*[.!]?\s*",
            query,
            re.I,
        )
    )
    pending_intent = state.get("pending_intent")
    llm_result = (
        _llm_classification(query)
        if state.get("mode") == "LLM-assisted" and not (bare_order_selection and pending_intent)
        else None
    )
    if bare_order_selection and pending_intent:
        intent = pending_intent
        method = "pending-clarification continuation"
    elif llm_result:
        intent = llm_result.intent
        explicit_order = llm_result.order_id or explicit_order
        claimed_customer = llm_result.customer_id or claimed_customer
        method = "optional structured LLM"
    else:
        intent = _deterministic_intent(query, state.get("previous_intent"))
        method = "deterministic domain classifier"
    if explicit_order:
        explicit_order = re.sub(r"[^A-Z0-9]", "", explicit_order.upper())
        if intent == "general_help":
            intent = "order_status"
            method += " + explicit-order fallback"
    return {
        "intent": intent,
        "order_id": explicit_order,
        "claimed_customer_id": claimed_customer,
        "trace": [
            _event(
                "understand",
                intent,
                f"Intent={intent}; explicit_order={explicit_order}; method={method}.",
                started=started,
                data_used=["query", "previous_intent", "pending_intent"],
            )
        ],
    }


def resolve_context_node(state: AgentState) -> AgentState:
    started = time.perf_counter()
    intent = state["intent"]
    customer_id = state.get("customer_id") or state.get("claimed_customer_id")
    customer = get_customer(customer_id) if customer_id else None

    if not customer:
        return {
            "customer_id": customer_id,
            "needs_clarification": True,
            "candidate_orders": [],
            "candidate_order_ids": [],
            "trace": [
                _event(
                    "context",
                    "need_identity",
                    "No valid session identity is available.",
                    started=started,
                )
            ],
        }

    identity_source = state.get("identity_source") or "query_demo"
    if state.get("authenticated") and state.get("claimed_customer_id") not in (None, customer_id):
        return {
            "customer_id": customer_id,
            "customer_name": customer["name"],
            "needs_clarification": True,
            "error": "The customer identifier in the message does not match the active session.",
            "error_code": "identity_mismatch",
            "candidate_orders": [],
            "candidate_order_ids": [],
            "trace": [
                _event(
                    "context",
                    "identity_mismatch",
                    "Ignored an identifier that conflicted with the active session.",
                    started=started,
                    data_used=["session_customer_id"],
                )
            ],
        }

    base: AgentState = {
        "customer_id": customer_id,
        "customer_name": customer["name"],
        "identity_source": identity_source,
        "needs_clarification": False,
        "candidate_orders": [],
        "candidate_order_ids": [],
        "direct_response": intent in {"general_help", "end_conversation"},
    }
    if intent in {"general_help", "end_conversation", "order_list"}:
        base["trace"] = [
            _event(
                "context",
                "identity_ready",
                f"Using {identity_source}; no order reference is required for {intent}.",
                started=started,
                data_used=["customer_id"],
            )
        ]
        return base

    order_id = state.get("order_id")
    source = "explicit" if order_id else None
    query = state["query"].lower()
    owned_orders = list_customer_orders(customer_id)

    if not order_id and any(term in query for term in ("latest", "most recent", "newest")):
        order_id = owned_orders[0]["order_id"] if owned_orders else None
        source = "latest_order_rule"
    elif not order_id and state.get("active_order_id"):
        order_id = state["active_order_id"]
        source = "conversation_memory"
    elif not order_id and intent == "order_status" and owned_orders:
        order_id = owned_orders[0]["order_id"]
        source = "helpful_latest_default"
    elif not order_id and len(owned_orders) == 1:
        order_id = owned_orders[0]["order_id"]
        source = "single_owned_order"

    if not order_id:
        return {
            **base,
            "candidate_orders": owned_orders[:4],
            "candidate_order_ids": [row["order_id"] for row in owned_orders[:4]],
            "pending_intent": intent,
            "pending_candidate_order_ids": [
                row["order_id"] for row in owned_orders[:4]
            ],
            "needs_clarification": True,
            "trace": [
                _event(
                    "context",
                    "clarify_order",
                    f"{len(owned_orders)} candidate orders exist; the agent will not guess.",
                    started=started,
                    data_used=["scoped_order_index"],
                )
            ],
        }

    return {
        **base,
        "order_id": order_id,
        "active_order_id": order_id,
        "pending_intent": None,
        "pending_candidate_order_ids": [],
        "order_reference_source": source,
        "trace": [
            _event(
                "context",
                "order_resolved",
                f"Resolved {order_id} via {source}.",
                started=started,
                data_used=["active_order_id", "scoped_order_index"],
            )
        ],
    }


def authorize_node(state: AgentState) -> AgentState:
    started = time.perf_counter()
    customer_id, order_id = state.get("customer_id"), state.get("order_id")
    if state["intent"] == "order_list":
        allowed = customer_id is not None
        detail = "Authorized a customer-scoped order list."
    elif customer_id is not None and order_id:
        allowed = customer_owns_order(customer_id, order_id)
        detail = "Ownership verified." if allowed else "Ownership check failed."
    else:
        allowed = False
        detail = "Required identity or order context is missing."
    return {
        "authorized": allowed,
        "trace": [
            _event(
                "authorize",
                "allow" if allowed else "deny",
                detail,
                started=started,
                data_used=["customer_id", "order_id"],
            )
        ],
    }


def retrieve_node(state: AgentState) -> AgentState:
    started = time.perf_counter()
    if not state.get("authorized"):
        return {
            "order": None,
            "orders": [],
            "trace": [
                _event(
                    "tools",
                    "safe_skip",
                    "No customer record entered state because authorization failed.",
                    started=started,
                )
            ],
        }
    if state["intent"] == "order_list":
        orders = list_customer_orders(state["customer_id"])
        return {
            "orders": orders,
            "trace": [
                _event(
                    "tools",
                    "list_customer_orders",
                    f"Returned {len(orders)} scoped order summaries.",
                    started=started,
                    data_used=["orders.order_id", "status", "order_date", "total_amount"],
                )
            ],
        }
    order = get_order(state["order_id"])
    return {
        "order": order,
        "orders": [],
        "trace": [
            _event(
                "tools",
                "get_order",
                "Loaded one governed order aggregate." if order else "No matching order exists.",
                started=started,
                data_used=["order", "order_items", "products"] if order else [],
            )
        ],
    }


def _match_product(query: str, items: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not items:
        return None
    query_tokens = re.findall(r"[a-z0-9]+", query.lower())
    scored: list[tuple[float, dict[str, Any]]] = []
    for item in items:
        name = item["name"]
        name_tokens = re.findall(r"[a-z0-9]+", name.lower())
        token_score = max(
            (fuzz.ratio(query_token, name_token) for query_token in query_tokens for name_token in name_tokens),
            default=0.0,
        )
        phrase_score = fuzz.WRatio(query, name)
        scored.append((max(token_score, phrase_score), item))
    score, matched_item = max(scored, key=lambda pair: pair[0])
    if score < 85:
        return None
    return matched_item


def policy_node(state: AgentState) -> AgentState:
    started = time.perf_counter()
    intent, order = state["intent"], state.get("order")
    if order and intent == "product_help":
        matched = _match_product(state["query"], order["items"])
        if not matched and state.get("active_product_name"):
            matched = next(
                (
                    item
                    for item in order["items"]
                    if item["name"].lower() == state["active_product_name"].lower()
                ),
                None,
            )
        if not matched and len(order["items"]) == 1:
            matched = order["items"][0]
        return {
            "matched_product": matched,
            "active_product_name": matched["name"] if matched else None,
            "policy": {},
            "handoff": False,
            "write_executed": False,
            "trace": [
                _event(
                    "policy",
                    "product_context",
                    (
                        f"Resolved product context to {matched['name']}."
                        if matched
                        else "No single product reference was required."
                    ),
                    started=started,
                    data_used=["query", "active_product_name", "order.items"],
                )
            ],
        }
    if not order or intent not in {"return_help", "cancel_request"}:
        return {
            "policy": {},
            "handoff": False,
            "write_executed": False,
            "trace": [
                _event(
                    "policy",
                    "not_required",
                    "No consequential policy decision is required.",
                    started=started,
                )
            ],
        }

    order_day = datetime.strptime(order["order_date"], "%Y-%m-%d").date()
    age_days = max(0, (POLICY_AS_OF - order_day).days)
    if intent == "return_help":
        matched = _match_product(state["query"], order["items"])
        if not matched and state.get("active_product_name"):
            matched = next(
                (
                    item
                    for item in order["items"]
                    if item["name"].lower() == state["active_product_name"].lower()
                ),
                None,
            )
        if not matched and len(order["items"]) == 1:
            matched = order["items"][0]
        considered = [matched] if matched else order["items"]
        windows = [int(re.search(r"\d+", item["return_policy"]).group()) for item in considered]
        window_days = min(windows)
        eligible = order["status"] not in {"Cancelled", "Returned"} and age_days <= window_days
        product_name = matched["name"] if matched else "all items (conservative window)"
        policy = {
            "policy_date": POLICY_AS_OF.isoformat(),
            "age_days": age_days,
            "window_days": window_days,
            "eligible_to_request": eligible,
            "product_scope": product_name,
            "requires_human_confirmation": True,
        }
        return {
            "matched_product": matched,
            "active_product_name": matched["name"] if matched else state.get("active_product_name"),
            "policy": policy,
            "handoff": True,
            "write_executed": False,
            "trace": [
                _event(
                    "policy",
                    "return_assessment",
                    f"Age={age_days}; window={window_days}; eligible_to_request={eligible}.",
                    started=started,
                    data_used=["order_date", "status", "product.return_policy"],
                )
            ],
        }

    eligible = order["status"] == "Processing"
    policy = {
        "eligible_to_request": eligible,
        "current_status": order["status"],
        "requires_human_approval": True,
        "write_executed": False,
    }
    return {
        "policy": policy,
        "handoff": True,
        "write_executed": False,
        "trace": [
            _event(
                "policy",
                "cancellation_assessment",
                f"Status={order['status']}; eligible_to_request={eligible}; write_executed=False.",
                started=started,
                data_used=["status", "cancellation_policy"],
            )
        ],
    }


def respond_node(state: AgentState) -> AgentState:
    started = time.perf_counter()
    if state.get("error"):
        outcome = "blocked" if state.get("error_code") == "unsafe_instruction" else "clarification"
        return {
            "response": state["error"],
            "outcome": outcome,
            "trace": [_event("respond", outcome, "Returned a controlled response.", started=started)],
        }
    if state.get("needs_clarification"):
        candidates = state.get("candidate_orders", [])
        if candidates:
            choices = "\n".join(
                f"• {row['order_id']} — {row['status']} — ordered {row['order_date']}"
                for row in candidates
            )
            text = "Which order should I use? Choose one of your recent orders:\n" + choices
        else:
            text = "Please start or select a verified demo customer session before requesting order data."
        return {
            "response": text,
            "outcome": "clarification",
            "trace": [_event("respond", "clarify", "Asked for only the missing context.", started=started)],
        }
    if state["intent"] == "end_conversation":
        return {
            "response": "Thanks for contacting Kartify. Please rate the conversation so the quality dashboard can learn from the outcome.",
            "outcome": "ended",
            "trace": [_event("respond", "close", "Closed the conversation and requested feedback.", started=started)],
        }
    if state["intent"] == "general_help":
        return {
            "response": "I can check your latest order, delivery status, purchased products, return eligibility, or prepare a cancellation request for human approval.",
            "outcome": "resolved",
            "trace": [_event("respond", "capabilities", "Explained the governed support scope.", started=started)],
        }
    if not state.get("authorized"):
        return {
            "response": "I cannot access that order from the active customer session. No order record was retrieved.",
            "outcome": "denied",
            "trace": [_event("respond", "deny", "Returned a privacy-preserving denial.", started=started)],
        }
    if state["intent"] == "order_list":
        rows = state.get("orders", [])
        text = "Here are your orders:\n" + "\n".join(
            f"• {row['order_id']}: {row['status']} — ${row['total_amount']:,.2f}"
            for row in rows
        )
        return {
            "response": text,
            "outcome": "resolved",
            "trace": [_event("respond", "grounded_list", "Formatted scoped tool evidence.", started=started)],
        }
    order = state.get("order")
    if not order:
        return {
            "response": "I could not find that order.",
            "outcome": "clarification",
            "trace": [_event("respond", "not_found", "Reported an evidence gap.", started=started)],
        }
    if state["intent"] == "product_help":
        matched = state.get("matched_product")
        if matched and any(
            term in state["query"].lower()
            for term in ("warranty", "guarantee", "return window", "how long")
        ):
            text = (
                f"The {matched['name']} in {order['order_id']} has a "
                f"{matched['warranty_period']} warranty and a {matched['return_policy']} "
                "return window."
            )
        else:
            lines = [
                f"• {item['name']} × {item['quantity']} — warranty {item['warranty_period']}; return window {item['return_policy']}"
                for item in order["items"]
            ]
            text = f"{order['order_id']} contains:\n" + "\n".join(lines)
        outcome = "resolved"
    elif state["intent"] == "return_help":
        policy = state["policy"]
        decision = (
            "appears eligible to request a return"
            if policy["eligible_to_request"]
            else "does not appear eligible for a return"
        )
        text = (
            f"{order['order_id']} {decision} for {policy['product_scope']}. "
            f"At the reproducible policy date it was {policy['age_days']} days old; "
            f"the applicable window is {policy['window_days']} days. A support specialist must confirm condition and exceptions."
        )
        outcome = "human_handoff"
    elif state["intent"] == "cancel_request":
        policy = state["policy"]
        if policy["eligible_to_request"]:
            text = (
                f"{order['order_id']} is Processing, so I can prepare a cancellation request for human approval. "
                "I have not changed the order."
            )
        else:
            text = (
                f"{order['order_id']} is {order['status']}, so an automated cancellation request is not eligible. "
                "I can hand this to a support specialist; no order change has been made."
            )
        outcome = "human_handoff"
    else:
        if order["delivery_date"]:
            delivery = f"The recorded delivery date is {order['delivery_date']}."
        elif order["status"] in {"Cancelled", "Returned"}:
            delivery = f"There is no active delivery date because the order is {order['status']}."
        else:
            delivery = "A delivery date has not yet been assigned; I will not invent one."
        text = f"{order['order_id']} is {order['status']}. {delivery} Total: ${order['total_amount']:,.2f}."
        outcome = "resolved"
    return {
        "response": text,
        "outcome": outcome,
        "trace": [
            _event(
                "respond",
                "grounded_response",
                "Generated the answer from governed fields and policy output.",
                started=started,
                data_used=["order", "policy"] if state.get("policy") else ["order"],
            )
        ],
    }


def evaluate_node(state: AgentState) -> AgentState:
    started = time.perf_counter()
    nodes = {event["node"] for event in state.get("trace", [])}
    access_control = not (state.get("authorized") is False and state.get("order"))
    grounded = bool(
        state.get("order")
        or state.get("orders")
        or state.get("outcome") in {"clarification", "denied", "blocked", "ended"}
        or state.get("intent") == "general_help"
    )
    policy_checked = state.get("intent") not in {"return_help", "cancel_request"} or bool(
        state.get("policy")
    )
    expected = {"guardrail", "respond"}
    if not state.get("error"):
        expected.add("understand")
    if not state.get("error") and state.get("intent") not in {"general_help", "end_conversation"}:
        expected.add("context")
    if not state.get("needs_clarification") and state.get("intent") not in {"general_help", "end_conversation"} and not state.get("error"):
        expected.update({"authorize", "tools", "policy"})
    trace_complete = expected.issubset(nodes)
    signals = [access_control, grounded, policy_checked, trace_complete]
    score = round(sum(signals) / len(signals), 3)
    quality = {
        "access_control": access_control,
        "grounded": grounded,
        "policy_checked": policy_checked,
        "trace_complete": trace_complete,
        "automated_quality_score": score,
        "customer_rating": None,
    }
    return {
        "quality": quality,
        "trace": [
            _event(
                "evaluate",
                "pass" if all(signals) else "review",
                f"Automated quality score={score:.0%}; customer rating remains independent.",
                started=started,
                data_used=["trace", "authorization", "grounding", "policy"],
            )
        ],
    }


def route_after_guardrail(state: AgentState) -> str:
    return "respond" if state.get("error") else "understand"


def route_after_context(state: AgentState) -> str:
    return "respond" if state.get("needs_clarification") or state.get("direct_response") else "authorize"


def build_graph():
    """Compile the executable state graph used by notebook, tests, and app."""
    builder = StateGraph(AgentState)
    builder.add_node("guardrail", guardrail_node)
    builder.add_node("understand", understand_node)
    builder.add_node("context", resolve_context_node)
    builder.add_node("authorize", authorize_node)
    builder.add_node("tools", retrieve_node)
    builder.add_node("policy", policy_node)
    builder.add_node("respond", respond_node)
    builder.add_node("evaluate", evaluate_node)
    builder.add_edge(START, "guardrail")
    builder.add_conditional_edges(
        "guardrail", route_after_guardrail, {"understand": "understand", "respond": "respond"}
    )
    builder.add_edge("understand", "context")
    builder.add_conditional_edges(
        "context", route_after_context, {"authorize": "authorize", "respond": "respond"}
    )
    builder.add_edge("authorize", "tools")
    builder.add_edge("tools", "policy")
    builder.add_edge("policy", "respond")
    builder.add_edge("respond", "evaluate")
    builder.add_edge("evaluate", END)
    return builder.compile()


GRAPH = build_graph()


class SupportSession:
    """Conversation façade that keeps identity and active-order context across turns."""

    def __init__(self, customer_id: int, mode: str = "Deterministic demo"):
        customer = get_customer(customer_id)
        if not customer:
            raise ValueError(f"Unknown demo customer: {customer_id}")
        self.conversation_id = str(uuid.uuid4())
        self.customer_id = customer_id
        self.customer_name = customer["name"]
        self.mode = mode
        self.active_order_id: str | None = None
        self.active_product_name: str | None = None
        self.previous_intent: Intent | None = None
        self.pending_intent: Intent | None = None
        self.pending_candidate_order_ids: list[str] = []
        self.turns = 0
        self.started_at = time.perf_counter()
        self.history: list[dict[str, Any]] = []

    def ask(self, query: str) -> AgentState:
        started = time.perf_counter()
        result = GRAPH.invoke(
            {
                "query": query,
                "mode": self.mode,
                "authenticated": True,
                "identity_source": "demo_session",
                "customer_id": self.customer_id,
                "customer_name": self.customer_name,
                "active_order_id": self.active_order_id,
                "active_product_name": self.active_product_name,
                "previous_intent": self.previous_intent,
                "pending_intent": self.pending_intent,
                "pending_candidate_order_ids": self.pending_candidate_order_ids,
                "trace": [],
            }
        )
        self.turns += 1
        previous_active_order = self.active_order_id
        self.active_order_id = result.get("active_order_id") or self.active_order_id
        if self.active_order_id != previous_active_order:
            self.active_product_name = None
        if result.get("matched_product"):
            self.active_product_name = result["matched_product"]["name"]
        elif result.get("active_product_name"):
            self.active_product_name = result["active_product_name"]
        self.previous_intent = result.get("intent") or self.previous_intent
        if result.get("needs_clarification") and result.get("candidate_order_ids"):
            self.pending_intent = result.get("intent")
            self.pending_candidate_order_ids = list(result["candidate_order_ids"])
        elif result.get("order_id") or result.get("outcome") in {
            "resolved",
            "denied",
            "human_handoff",
            "ended",
        }:
            self.pending_intent = None
            self.pending_candidate_order_ids = []
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        result.setdefault("quality", {})["latency_ms"] = elapsed_ms
        result["conversation_id"] = self.conversation_id
        result["turn_number"] = self.turns
        self.history.append(
            {
                "turn": self.turns,
                "query": query,
                "response": result["response"],
                "intent": result.get("intent"),
                "active_order_id": self.active_order_id,
                "active_product_name": self.active_product_name,
                "pending_intent": self.pending_intent,
                "outcome": result.get("outcome"),
                "quality_score": result.get("quality", {}).get("automated_quality_score"),
                "latency_ms": elapsed_ms,
            }
        )
        return result

    def context(self) -> dict[str, Any]:
        return {
            "conversation_id": self.conversation_id,
            "customer_id": self.customer_id,
            "customer_name": self.customer_name,
            "active_order_id": self.active_order_id,
            "active_product_name": self.active_product_name,
            "previous_intent": self.previous_intent,
            "pending_intent": self.pending_intent,
            "pending_candidate_order_ids": self.pending_candidate_order_ids,
            "turns": self.turns,
        }

    def feedback_payload(
        self, rating: int, resolved: bool, comment: str = ""
    ) -> dict[str, Any]:
        return {
            "conversation_id": self.conversation_id,
            "customer_id": self.customer_id,
            "rating": rating,
            "resolved": resolved,
            "comment": comment,
            "turns": max(1, self.turns),
            "duration_seconds": round(time.perf_counter() - self.started_at, 2),
            "intents": [row["intent"] for row in self.history if row.get("intent")],
        }


def ask(query: str, mode: str = "Deterministic demo") -> AgentState:
    """Backward-compatible one-turn helper; prefer SupportSession for conversation memory."""
    customer_id = _extract_customer_id(query)
    if customer_id and get_customer(customer_id):
        return SupportSession(customer_id, mode=mode).ask(query)
    return GRAPH.invoke(
        {
            "query": query,
            "mode": mode,
            "authenticated": False,
            "identity_source": "query_demo",
            "trace": [],
        }
    )
