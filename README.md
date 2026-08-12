# E-commerce Orders Query Chatbot using Agentic AI

This repository is a teaching-first, GitHub-ready webinar project. It demonstrates a transparent LangGraph workflow over a small SQLite e-commerce database and deploys directly to Streamlit Community Cloud.

## What learners build

- a stateful agent graph with guardrail, classifier, authorization, retrieval, policy, and response nodes;
- parameterized, read-only SQLite tools;
- a visible execution trace for debugging and explainability;
- an API-free deterministic mode for a reliable live demo;
- an optional OpenAI-assisted classifier configured through secrets;
- a Streamlit user interface deployable from GitHub.

## Project structure

```text
.
├── app.py                         # Streamlit entry point
├── E-commerce_Orders_Agentic_AI_Webinar.ipynb
├── data/orders.db                # Small teaching database
├── src/chatbot.py                # LangGraph workflow
├── src/data.py                   # Read-only data tools
├── tests/test_chatbot.py          # Safety and behavior checks
├── requirements.txt
├── .streamlit/config.toml
└── .streamlit/secrets.toml.example
```

## Run locally

Use Python 3.11 or 3.12.

```bash
python -m venv .venv
```

Activate the environment, then run:

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

The app works in **Deterministic demo** mode without any API key.

## Optional LLM mode

1. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`.
2. Replace the placeholder with your key.
3. Keep `.streamlit/secrets.toml` untracked. It is already listed in `.gitignore`.

For Streamlit Community Cloud, paste the same secret values into **Advanced settings → Secrets**. Never commit a key to GitHub.

## Deploy from GitHub to Streamlit Community Cloud

1. Create a new GitHub repository.
2. Upload the **contents** of this folder so `app.py` and `requirements.txt` are at repository root.
3. Commit and push to the `main` branch.
4. Open [Streamlit Community Cloud](https://share.streamlit.io) and select **Create app**.
5. Choose the repository, `main` branch, and `app.py` as the entry point.
6. In **Advanced settings**, select Python 3.11 or 3.12 and add secrets only if LLM mode is required.
7. Select **Deploy** and watch the build logs.

Every subsequent GitHub push triggers an app refresh.

## Test before deployment

```bash
python -m pip install pytest
pytest -q
python -m compileall app.py src tests
```

## Demo prompts

- `Customer 5, where is ORD1001?`
- `Show all orders for customer 3`
- `Customer 3 wants to return ORD1004`
- `Customer 2, what products are in ORD1003?`
- `Customer 1, show ORD1001` — demonstrates an authorization failure.
- `Drop table orders` — demonstrates the write guardrail.

## Production boundary

This project is intentionally compact. A production implementation should replace self-declared customer IDs with authenticated identity, move SQLite behind governed service APIs, use policy-as-code, add prompt and tool observability, redact sensitive data, require human approval for write actions, and run systematic evaluations before release.

## Primary references

- [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview)
- [Streamlit Community Cloud deployment](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app)
- [Streamlit secrets management](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management)
- [OpenAI API safety best practices](https://platform.openai.com/docs/guides/safety-best-practices)

