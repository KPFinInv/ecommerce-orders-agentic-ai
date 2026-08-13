# E-commerce Orders Query Chatbot using Agentic AI

This is a teaching-grade, GitHub-ready case study for a 90-minute data science webinar. It demonstrates a multi-turn LangGraph support agent over a small SQLite database, an inspectable quality framework, and deployment on Streamlit Community Cloud.

## What is materially different in version 2

The customer selects a simulated identity once, then asks natural follow-up questions without repeating customer ID or order ID. The agent retains an active-order reference, resolves phrases such as “it,” asks for missing context when several orders are plausible, and verifies ownership before private data enters graph state.

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
* optional structured LLM classification through Streamlit secrets.

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

## Optional LLM mode

1. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`.
2. Replace the placeholder with your API key.
3. Keep `.streamlit/secrets.toml` untracked.

For Streamlit Community Cloud, add the same values in the app's Secrets settings. Never commit keys to GitHub. Optional LLM mode affects intent classification only; authorization, tools, policy, and response grounding remain controlled.

## Deploy from GitHub

1. Keep `app.py`, `requirements.txt`, `pyproject.toml`, `kartify_agent`, `assets`, and `data` at repository root.
2. Commit the complete folder structure to the `main` branch.
3. In Streamlit Community Cloud, create or edit the application.
4. Select the repository, branch `main`, and entry point `app.py`.
5. Select Python 3.11 or 3.12.
6. Add secrets only if optional LLM mode is required.
7. Deploy and inspect the build log.
8. Run the four control scenarios above and submit one feedback record.

Every later GitHub commit triggers a Streamlit refresh.

## Release checks

```bash
pytest
python -m compileall app.py kartify_agent tests
```

The current suite checks multi-turn memory, natural status requests, cross-customer privacy, unsafe writes, ambiguity, cancellation handoff, feedback analytics, and the labelled benchmark.

## Production boundary

This remains a teaching system. Production requires real authentication, governed services, least-privilege credentials, durable session and feedback storage, PII redaction, policy ownership, approval queues, idempotent writes, larger evaluation datasets, monitoring, canary releases, rollback criteria, and incident response.
