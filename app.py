"""Streamlit experience for the advanced, context-aware Kartify teaching agent."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import streamlit as st

from kartify_agent import (
    DETERMINISTIC_MODE,
    GROQ_MODE,
    OPENAI_MODE,
    SESSION_SCHEMA_VERSION,
    FeedbackStore,
    SupportSession,
    available_understanding_modes,
    benchmark_summary,
    run_benchmark,
)
from kartify_agent.repository import database_summary, list_customers


st.set_page_config(
    page_title="Kartify Agentic Order Assistant",
    page_icon="📦",
    layout="wide",
)


def load_cloud_secrets() -> None:
    """Copy optional provider settings into the environment without logging them."""
    try:
        configured = dict(st.secrets)
    except FileNotFoundError:
        configured = {}
    for key in ("GROQ_API_KEY", "GROQ_MODEL", "OPENAI_API_KEY", "OPENAI_MODEL"):
        if key in configured and not os.getenv(key):
            os.environ[key] = str(configured[key])


@st.cache_resource
def feedback_store() -> FeedbackStore:
    return FeedbackStore()


def new_conversation(customer_id: int, mode: str) -> None:
    st.session_state.agent_session = SupportSession(customer_id, mode=mode)
    st.session_state.messages = []
    st.session_state.last_result = None
    st.session_state.rating_open = False
    st.session_state.feedback_saved = False


load_cloud_secrets()
customers = list_customers()
customer_lookup = {row["customer_id"]: row["name"] for row in customers}

with st.sidebar:
    st.header("Conversation setup")
    selected_customer = st.selectbox(
        "Demo customer session",
        options=list(customer_lookup),
        format_func=lambda value: f"{customer_lookup[value]} · customer {value}",
        help=(
            "This selection simulates identity established before chat. A production "
            "application would use authenticated account context."
        ),
    )
    st.caption("Select identity once; the customer does not repeat it in every message.")
    modes = available_understanding_modes()
    selected_mode = st.radio("Understanding mode", modes)
    if selected_mode == GROQ_MODE:
        st.success(
            "Groq key detected: GPT OSS 20B will be used when provider authentication "
            "succeeds; the governed conversation fallback remains active."
        )
    elif selected_mode == OPENAI_MODE:
        st.success("Configured: OpenAI assisted understanding is available with safe fallback.")
    else:
        st.success("Ready: deterministic mode is active; no API key is required.")
    if st.button("Start a new conversation", width="stretch"):
        new_conversation(selected_customer, selected_mode)

if "agent_session" not in st.session_state:
    new_conversation(selected_customer, selected_mode)
elif (
    st.session_state.agent_session.customer_id != selected_customer
    or st.session_state.agent_session.mode != selected_mode
):
    new_conversation(selected_customer, selected_mode)

session: SupportSession = st.session_state.agent_session
required_session_fields = (
    "schema_version",
    "pending_intent",
    "pending_candidate_order_ids",
    "active_product_name",
)
if (
    not all(hasattr(session, field) for field in required_session_fields)
    or session.schema_version != SESSION_SCHEMA_VERSION
):
    # Streamlit can preserve an object created by an earlier deployed class definition.
    # Rebuild the demo session when its state schema changes so existing browser tabs recover.
    new_conversation(selected_customer, selected_mode)
    session = st.session_state.agent_session

st.title("📦 Kartify Agentic Order Assistant")
st.caption(
    "A multi-turn teaching system: identity context → guardrails → understanding → "
    "context resolution → authorization → tools → policy → response → evaluation"
)

summary = database_summary()
metrics = st.columns(6)
for column, (label, value) in zip(metrics[:4], summary.items()):
    column.metric(label.replace("_", " ").title(), value)
metrics[4].metric("Conversation turns", session.turns)
metrics[5].metric("Active order", session.active_order_id or "Not selected")
if session.pending_intent:
    st.warning(
        "Clarification checkpoint retained: select an order and the agent will continue "
        f"the original **{session.pending_intent.replace('_', ' ')}** request."
    )

chat_tab, architecture_tab, quality_tab = st.tabs(
    ["💬 Conversation", "🧭 Executable architecture", "📊 Quality and feedback"]
)

with chat_tab:
    st.info(
        f"Demo session established for **{session.customer_name}**. Try natural follow-ups; "
        "customer, active-order, product, and clarification context will carry forward."
    )
    prompt_columns = st.columns(4)
    prompt_sets = {
        2: [
            "Where is my latest order?",
            "Could you remind me what came in that parcel?",
            "How long is the 4K monitor covered?",
            "Could I send that one back?",
        ]
    }
    sample_prompts = prompt_sets.get(
        session.customer_id,
        [
            "Where is my latest order?",
            "What exactly came in that parcel?",
            "Is the watch still covered?",
            "Could I send it back if I changed my mind?",
        ],
    )
    for column, sample in zip(prompt_columns, sample_prompts):
        if column.button(sample, width="stretch"):
            st.session_state.queued_prompt = sample

    if session.customer_id == 2:
        with st.expander("Bob Smith · eight-turn webinar script"):
            st.markdown(
                """
1. `Where is my latest order?`
2. `Could you remind me what came in that parcel?`
3. `How long is the 4K monitor covered?`
4. `And how long is the blender covered?`
5. `Could I send that one back?`
6. `And when should the parcel get here?`
7. `Actually, can you stop this order before it ships?`
8. `That's all, thanks.`

The governed fallback is release-tested to preserve the same intent, order, product,
policy, and response path if the external language-model service is unavailable.
"""
            )

    for message in st.session_state.messages:
        avatar = "🧑" if message["role"] == "user" else "🛡️"
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"])

    typed_prompt = st.chat_input("Ask naturally, for example: When will it arrive?")
    prompt = typed_prompt or st.session_state.pop("queued_prompt", None)
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.spinner("The graph is resolving context and consulting governed tools..."):
            result = session.ask(prompt)
        st.session_state.last_result = result
        st.session_state.messages.append(
            {"role": "assistant", "content": result["response"]}
        )
        if result.get("outcome") == "ended":
            st.session_state.rating_open = True
        st.rerun()

    result = st.session_state.last_result
    if result:
        if result.get("understanding_fallback"):
            failure_labels = {
                "authentication": "provider authentication failed",
                "rate_limit": "the provider rate limit was reached",
                "timeout": "the provider timed out",
                "connection": "the provider could not be reached",
                "credentials_unavailable": "provider credentials were unavailable",
                "provider_error": "the provider rejected the request",
            }
            failure = failure_labels.get(
                result.get("understanding_failure"), "the provider was unavailable"
            )
            st.warning(
                f"The language-model request used fallback because {failure}. The governed "
                "classifier preserved the same customer, order, product, policy, and response path."
            )
        st.subheader("Why the agent answered this way")
        trace_view, state_view, evidence_view = st.tabs(
            ["Execution trace", "Session state", "Grounding evidence"]
        )
        with trace_view:
            st.dataframe(pd.DataFrame(result.get("trace", [])), hide_index=True)
        with state_view:
            context = session.context()
            context["outcome"] = result.get("outcome")
            context["quality"] = result.get("quality")
            st.json(context)
        with evidence_view:
            if result.get("order"):
                st.write(
                    {
                        key: value
                        for key, value in result["order"].items()
                        if key != "items"
                    }
                )
                st.dataframe(pd.DataFrame(result["order"]["items"]), hide_index=True)
            elif result.get("orders"):
                st.dataframe(pd.DataFrame(result["orders"]), hide_index=True)
            else:
                st.caption("No private order record entered state for this turn.")

    end_col, reset_col = st.columns([1, 1])
    if end_col.button("End conversation and rate it", width="stretch"):
        st.session_state.rating_open = True
    if reset_col.button("Clear chat but retain demo identity", width="stretch"):
        new_conversation(selected_customer, selected_mode)
        st.rerun()

    if st.session_state.rating_open and not st.session_state.feedback_saved:
        st.subheader("Customer feedback")
        with st.form("conversation_feedback"):
            rating = st.select_slider(
                "Overall conversation rating",
                options=[1, 2, 3, 4, 5],
                value=4,
                format_func=lambda score: f"{score} star{'s' if score != 1 else ''}",
            )
            resolved = st.radio(
                "Was your issue resolved?",
                [True, False],
                format_func=lambda value: "Yes" if value else "No",
            )
            comment = st.text_area("Optional feedback", max_chars=500)
            submitted = st.form_submit_button("Submit feedback")
        if submitted:
            feedback_store().save(session.feedback_payload(rating, resolved, comment))
            st.session_state.feedback_saved = True
            st.success("Feedback saved. The quality dashboard has been updated.")

with architecture_tab:
    st.subheader("Runtime architecture")
    architecture_path = Path("assets/agent_architecture.svg")
    if architecture_path.exists():
        st.image(str(architecture_path), width="stretch")
    else:
        st.warning("Architecture image is not available in this checkout.")
    st.markdown(
        """
The architecture distinguishes **conversation memory** from database evidence. Memory may
retain a customer scope and active order reference, but it does not bypass authorization.
Every order retrieval still passes the object-level ownership check.

The understanding selector can use deterministic rules, the free GroqCloud-hosted OpenAI
GPT OSS 20B model, or an OpenAI API model. Only intent and explicit-entity classification
are delegated. Provider failure automatically falls back to the deterministic classifier.

The final evaluation node produces automated control signals. Customer satisfaction is
captured separately because a system cannot infer perceived resolution from its own trace.
"""
    )

with quality_tab:
    st.subheader("Customer-experience signals")
    feedback_metrics = feedback_store().metrics()
    feedback_columns = st.columns(5)
    feedback_columns[0].metric("Responses", feedback_metrics["responses"])
    feedback_columns[1].metric("Average rating", feedback_metrics["average_rating"])
    feedback_columns[2].metric(
        "Resolution rate", f"{feedback_metrics['resolution_rate']:.0%}"
    )
    feedback_columns[3].metric(
        "Five-star share", f"{feedback_metrics['five_star_share']:.0%}"
    )
    feedback_columns[4].metric("Quality band", feedback_metrics["quality_band"])
    st.caption(
        "Feedback stored on Streamlit Community Cloud is demonstration data and may reset "
        "when the container restarts. Use a managed database for durable production analytics."
    )
    if st.button("Run the labelled agent benchmark"):
        with st.spinner("Running multi-turn, privacy, policy, and guardrail scenarios..."):
            benchmark = run_benchmark()
        st.session_state.benchmark = benchmark
    if "benchmark" in st.session_state:
        benchmark = st.session_state.benchmark
        st.json(benchmark_summary(benchmark))
        st.dataframe(benchmark, hide_index=True, width="stretch")

st.divider()
st.caption(
    "Teaching system. Production requires real authentication, durable telemetry, managed "
    "data services, policy ownership, human escalation, monitoring, and incident response."
)
