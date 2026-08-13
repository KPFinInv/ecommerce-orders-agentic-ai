"""Streamlit front end for the Kartify order-query agent."""

from __future__ import annotations

import os

import pandas as pd
import streamlit as st

from src.chatbot import ask
from src.data import database_summary


st.set_page_config(
    page_title="Kartify Agentic Order Assistant",
    page_icon="📦",
    layout="wide",
)


def load_cloud_secrets() -> None:
    """Copy Streamlit secrets into environment variables without logging them."""
    for key in ("OPENAI_API_KEY", "OPENAI_MODEL"):
        if key in st.secrets and not os.getenv(key):
            os.environ[key] = str(st.secrets[key])


def guardrail_blocked(result: dict) -> bool:
    """Return True when the workflow safely stopped a write request."""
    return any(
        event.get("node") == "guardrail"
        and "blocked" in str(event.get("detail", "")).lower()
        for event in result.get("trace", [])
    )


load_cloud_secrets()

st.title("📦 Kartify Agentic Order Assistant")
st.caption(
    "A transparent teaching demo: guardrails → classification → authorization "
    "→ retrieval → policy → response"
)

with st.sidebar:
    st.header("Demo controls")
    llm_available = bool(os.getenv("OPENAI_API_KEY"))
    options = ["Deterministic demo"] + (["LLM-assisted"] if llm_available else [])
    mode = st.radio(
        "Execution mode",
        options,
        help="Deterministic mode is API-free and ideal for a reliable classroom demo.",
    )
    if llm_available:
        st.success("Ready: LLM-assisted mode is available.")
    else:
        st.success(
            "Ready: deterministic mode is active. No API key is required for "
            "this webinar demo."
        )

    st.markdown("**Try these prompts**")
    samples = [
        ("Customer 5, where is ORD1001?", "Customer 5, where is ORD1001?"),
        ("Show all orders for customer 3", "Show all orders for customer 3"),
        ("Customer 3 wants to return ORD1004", "Customer 3 wants to return ORD1004"),
        (
            "Customer 2, what products are in ORD1003?",
            "Customer 2, what products are in ORD1003?",
        ),
        ("Customer 1, show ORD1001", "Customer 1, show ORD1001"),
        ("🛡️ Safety test: block a database write", "Drop table orders"),
    ]
    for label, sample_prompt in samples:
        if st.button(label, use_container_width=True):
            st.session_state["prompt"] = sample_prompt

summary = database_summary()
metrics = st.columns(4)
for column, (label, value) in zip(metrics, summary.items()):
    column.metric(label.replace("_", " ").title(), value)

prompt = st.chat_input(
    "Ask about an order and include customer ID + order ID where relevant"
)
if prompt:
    st.session_state["prompt"] = prompt

if "prompt" not in st.session_state:
    st.session_state["prompt"] = "Customer 5, where is ORD1001?"

selected_prompt = st.session_state["prompt"]
is_safety_test = selected_prompt.strip().lower() == "drop table orders"

if is_safety_test:
    st.info(
        "Safety demonstration: the expected outcome is a controlled refusal. "
        "The request will be stopped before any database access."
    )

st.chat_message("user", avatar="🧪" if is_safety_test else None).write(selected_prompt)
with st.spinner("Running the agent graph..."):
    result = ask(selected_prompt, mode=mode)

blocked_as_expected = guardrail_blocked(result)
if blocked_as_expected:
    st.success(
        "🛡️ Safety check passed: the destructive write request was blocked. "
        "No database change was attempted."
    )
    st.chat_message("assistant", avatar="🛡️").write(result["response"])
else:
    st.chat_message("assistant").write(result["response"])

left, right = st.columns([1.3, 1])
with left:
    st.subheader("Agent execution trace")
    for number, event in enumerate(result.get("trace", []), 1):
        with st.expander(f"{number}. {event['node'].title()}", expanded=True):
            st.write(event["detail"])

with right:
    st.subheader("Structured state")
    safe_state = {
        key: value
        for key, value in result.items()
        if key not in {"trace", "query"}
    }
    st.json(safe_state, expanded=False)

if result.get("order"):
    st.subheader("Grounding record")
    order = result["order"]
    st.dataframe(
        pd.DataFrame(order["items"]),
        use_container_width=True,
        hide_index=True,
    )

st.divider()
st.caption(
    "Teaching sample only. A production service would use authenticated identity, "
    "audited APIs, observability, and human approval for consequential actions."
)
