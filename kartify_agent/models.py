"""Typed contracts shared by the graph, tools, evaluation, and UI."""

from __future__ import annotations

import operator
from typing import Annotated, Any, Literal, TypedDict

from pydantic import BaseModel, Field


Intent = Literal[
    "order_status",
    "order_list",
    "product_help",
    "return_help",
    "cancel_request",
    "end_conversation",
    "general_help",
]

Outcome = Literal[
    "resolved",
    "clarification",
    "denied",
    "blocked",
    "human_handoff",
    "ended",
]


class TraceEvent(TypedDict, total=False):
    node: str
    decision: str
    detail: str
    duration_ms: float
    data_used: list[str]


class AgentState(TypedDict, total=False):
    """State contract for one turn; session context is injected before invocation."""

    query: str
    mode: str
    authenticated: bool
    identity_source: str
    customer_id: int | None
    customer_name: str | None
    claimed_customer_id: int | None
    active_order_id: str | None
    active_product_name: str | None
    previous_intent: Intent | None
    pending_intent: Intent | None
    pending_candidate_order_ids: list[str]
    intent: Intent
    order_id: str | None
    order_reference_source: str | None
    candidate_orders: list[dict[str, Any]]
    candidate_order_ids: list[str]
    needs_clarification: bool
    direct_response: bool
    authorized: bool
    order: dict[str, Any] | None
    orders: list[dict[str, Any]]
    matched_product: dict[str, Any] | None
    policy: dict[str, Any]
    handoff: bool
    blocked: bool
    write_executed: bool
    error: str | None
    error_code: str | None
    response: str
    outcome: Outcome
    quality: dict[str, Any]
    trace: Annotated[list[TraceEvent], operator.add]


class Classification(BaseModel):
    """Structured model output used only when optional LLM mode is enabled."""

    intent: Intent
    order_id: str | None = None
    customer_id: int | None = None


class FeedbackRecord(BaseModel):
    """Conversation-level customer feedback and operational context."""

    conversation_id: str
    customer_id: int
    rating: int = Field(ge=1, le=5)
    resolved: bool
    comment: str = Field(default="", max_length=500)
    turns: int = Field(ge=1)
    duration_seconds: float = Field(ge=0)
    intents: list[str] = Field(default_factory=list)
