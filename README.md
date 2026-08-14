# E-commerce Orders Query Chatbot using Agentic AI

This is a teaching-grade, GitHub-ready case study for a 90-minute data science webinar. It demonstrates a multi-turn LangGraph support agent over a small SQLite database, an inspectable quality framework, and deployment on Streamlit Community Cloud.

## What is materially different in version 2.2

The customer selects a simulated identity once, then asks natural follow-up questions without repeating customer ID or order ID. The agent retains an active-order reference, resolves phrases such as “it,” asks for missing context when several orders are plausible, and verifies ownership before private data enters graph state.

Version 2.1 also retains the **unfinished task behind a clarification**. If a customer asks which products are in an unspecified order, the agent lists safe candidate orders. A reply containing only `ORD1009` resumes the original product request instead of incorrectly switching to order status. The selected order and product context then remain relevant across later warranty, tracking, delivery, return, and cancellation questions.

The case study also includes:

* typed session and turn state;
* input guardrails and early exits;
* read-only, allowlisted domain tools;
* object-level authorization;
* product matching with RapidFuzz;
* reproducible return and cancellation policy;
* human approval boundaries for consequential actions;
* node-level execution traces and automated quality signals;
* a labelled multi-turn benchmark;
* 1-to-5 customer rating, resolution feedback, and SQLite analytics;
* an executable architecture view in Jupyter and Streamlit;
* deterministic mode for reliable, API-free teaching;
* free structured LLM classification using OpenAI GPT OSS 20B on GroqCloud;
* optional OpenAI API classification through Streamlit secrets;
* automatic deterministic fallback when an LLM provider is unavailable or rate limited.

## Project structure

```text
.
├── app.py
├── E-commerce_Orders_Agentic_AI_Webinar.ipynb
├── assets/
│   ├── agent_architecture.svg
│   └── agent_architecture.png
├── data/orders.db
├── kartify_agent/
│   ├── agent.py
│   ├── evaluation.py
│   ├── feedback.py
│   ├── models.py
│   ├── notebook_support.py
│   └── repository.py
├── tests/test_chatbot.py
├── pyproject.toml
├── requirements.txt
└── .streamlit/
    ├── config.toml
    └── secrets.toml.example
```

The notebook imports the package instead of duplicating implementation code. This keeps the learning flow readable while the production logic remains reusable and testable.

## Run locally

Use Python 3.11 or 3.12.

```bash
python -m venv .venv
```

Activate the environment, then run:

```bash
python -m pip install -r requirements.txt
python -m pip install -e .
pytest
streamlit run app.py
```

The complete deterministic experience works without an API key.

## Recommended conversation demo

Select **Bob Smith, customer 2** once in the sidebar, then ask:

1. `Where is my latest order?`
2. `What products are in it?`
3. `Can I return the blender?`

This demonstrates latest-order resolution, conversation memory, product grounding, and policy handoff without repeating identifiers.

### Six-turn clarification-continuation demo

Select Alice Johnson, customer 1 once, then ask:

1. `Can you check and tell me which products are there in my order?`
2. `ORD1009`
3. `What warranty does it have?`
4. `Where is it now?`
5. `When will it arrive?`
6. `Can I return it?`

Turn 2 continues the pending product request. Turns 3 through 6 reuse the governed active-order and product context. The customer does not need to repeat either identifier.

Additional controls:

* Select customer 3 and ask `Can I return an order?` to show ambiguity handling.
* Select customer 1 and ask `Show ORD1001` to show cross-customer denial.
* Select customer 4, ask `Track ORD1002`, then `Cancel it` to show a human approval boundary.
* Ask `Drop table orders` to show a structural guardrail and confirm the database is unchanged.

## Customer feedback and quality

Use **End conversation and rate it** to record:

* overall rating from 1 to 5;
* whether the issue was resolved;
* an optional comment;
* conversation turns, duration, and intents.

The Quality tab keeps customer feedback separate from automated controls such as authorization, groundedness, policy checks, and trace completeness. Local feedback storage on Streamlit Community Cloud is demonstration-only and can reset when the application container restarts.

## Free GroqCloud LLM mode

1. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`.
2. Add a GroqCloud key as `GROQ_API_KEY`.
3. Keep `GROQ_MODEL = "openai/gpt-oss-20b"`.
4. Keep `.streamlit/secrets.toml` untracked.

For Streamlit Community Cloud, add the same two values in the app's Secrets settings. Never commit keys to GitHub. The sidebar will expose **Free LLM assisted: GPT OSS 20B** only when the key is configured.

GroqCloud's free plan is quota limited. If a request times out, fails authentication, or reaches a rate limit, the same turn automatically uses the deterministic classifier. The trace records the provider, model, fallback status, and a non-sensitive failure category.

## Optional OpenAI API mode

1. Add `OPENAI_API_KEY` through local or Streamlit secrets.
2. Set `OPENAI_MODEL` to the approved model for the account.
3. Keep `.streamlit/secrets.toml` untracked.

Both model modes affect intent and explicit-entity classification only. Authorization, tools, policy, memory, and response grounding remain controlled.

## Deploy from GitHub

1. Keep `app.py`, `requirements.txt`, `pyproject.toml`, `kartify_agent`, `assets`, and `data` at repository root.
2. Commit the complete folder structure to the `main` branch.
3. In Streamlit Community Cloud, create or edit the application.
4. Select the repository, branch `main`, and entry point `app.py`.
5. Select Python 3.11 or 3.12.
6. Add `GROQ_API_KEY` and `GROQ_MODEL` in Secrets for the free LLM demonstration.
7. Deploy and inspect the build log.
8. Run the four control scenarios above and submit one feedback record.

Every later GitHub commit triggers a Streamlit refresh.

## Release checks

```bash
pytest
python -m compileall app.py kartify_agent tests
```

The current suite contains eleven tests covering multi-turn memory, clarification continuation, natural status requests, cross-customer privacy, unsafe writes, ambiguity, cancellation handoff, feedback analytics, the labelled benchmark, structured LLM routing, and deterministic provider fallback.

## Production boundary

This remains a teaching system. Production requires real authentication, governed services, least-privilege credentials, durable session and feedback storage, PII redaction, policy ownership, approval queues, idempotent writes, larger evaluation datasets, monitoring, canary releases, rollback criteria, and incident response.
