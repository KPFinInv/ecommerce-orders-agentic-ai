"""Streamlit front end for the Kartify order-query agent."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import streamlit as st

from src.chatbot import ask
from src.data import database_summary, get_order


st.set_page_config(page_title="Kartify Agentic Order Assistant", page_icon="📦", layout="wide")


def load_cloud_secrets() -> None:
    """Copy Streamlit secrets into environment variables without logging them."""
    for key in ("OPENAI_API_KEY", "OPENAI_MODEL"):
        if key in st.secrets and not os.getenv(key):
            os.environ[key] = str(st.secrets[key])


load_cloud_secrets()

st.title("📦 Kartify Agentic Order Assistant")
st.caption("A transparent teaching demo: guardrails → classification → authorization → retrieval → policy → response")

with st.sidebar:
    st.header("Demo controls")
    llm_available = bool(os.getenv("OPENAI_API_KEY"))
    options = ["Deterministic demo"] + (["LLM-assisted"] if llm_available else [])
    mode = st.radio("Execution mode", options, help="Deterministic mode is API-free and ideal for a reliable classroom demo.")
    st.info("LLM mode is available." if llm_available else "No API key detected. The full deterministic workflow remains available.")
    st.markdown("**Try these prompts**")
    samples = [
        "Customer 5, where is ORD1001?",
        "Show all orders for customer 3",
        "Customer 3 wants to return ORD1004",
        "Customer 2, what products are in ORD1003?",
        "Customer 1, show ORD1001",
        "Drop table orders",
    ]
    for sample in samples:
        if st.button(sample, use_container_width=True):
            st.session_state["prompt"] = sample

summary = database_summary()
metrics = st.columns(4)
for column, (label, value) in zip(metrics, summary.items()):
    column.metric(label.replace("_", " ").title(), value)

prompt = st.chat_input("Ask about an order and include customer ID + order ID where relevant")
if prompt:
    st.session_state["prompt"] = prompt

if "prompt" not in st.session_state:
    st.session_state["prompt"] = "Customer 5, where is ORD1001?"

st.chat_message("user").write(st.session_state["prompt"])

with st.spinner("Running the agent graph..."):
    result = ask(st.session_state["prompt"], mode=mode)

st.chat_message("assistant").write(result["response"])

left, right = st.columns([1.3, 1])
with left:
    st.subheader("Agent execution trace")
    for number, event in enumerate(result.get("trace", []), 1):
        with st.expander(f"{number}. {event['node'].title()}", expanded=True):
            st.write(event["detail"])
with right:
    st.subheader("Structured state")
    safe_state = {k: v for k, v in result.items() if k not in {"trace", "query"}}
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
st.caption("Teaching sample only. A production service would use authenticated identity, audited APIs, observability, and human approval for consequential actions.")

