# GitHub → Streamlit Community Cloud Checklist

## Repository readiness

- [ ] `app.py` is at repository root.
- [ ] `requirements.txt` is at repository root.
- [ ] `pyproject.toml` and the complete `kartify_agent/` package are committed.
- [ ] `assets/agent_architecture.svg` is committed.
- [ ] `data/orders.db` is committed.
- [ ] `.streamlit/config.toml` is committed.
- [ ] `.streamlit/secrets.toml` is not committed.
- [ ] `.gitignore` excludes secrets and local environments.
- [ ] `pytest` reports eleven passing tests locally.
- [ ] `streamlit run app.py` starts from repository root.

## GitHub

- [ ] Repository is created.
- [ ] Files are pushed to the `main` branch.
- [ ] GitHub shows no credential or secret file.
- [ ] The latest commit contains the tested version.

## Streamlit Community Cloud

- [ ] Sign in with the GitHub account that can access the repository.
- [ ] Select **Create app → Deploy a public app from GitHub**.
- [ ] Choose repository and `main` branch.
- [ ] Set the main file path to `app.py`.
- [ ] Select Python 3.11 or 3.12 in Advanced settings.
- [ ] Add `GROQ_API_KEY` and `GROQ_MODEL = "openai/gpt-oss-20b"` only in the Secrets field.
- [ ] Add OpenAI values only if the optional paid OpenAI API path is also required.
- [ ] Deploy and inspect build logs.
- [ ] Run the six-turn clarification-continuation journey, ambiguity, authorization-failure, cancellation-handoff, and guardrail prompts on the public URL.
- [ ] Submit one customer rating and confirm the Quality tab updates.

## Troubleshooting

| Symptom | Most likely cause | Resolution |
|---|---|---|
| Module not found | `kartify_agent/` missing, dependency missing, or wrong file location | Commit the complete package folder and root dependency files; redeploy |
| Database not found | `data/orders.db` not committed or path is relative to the wrong directory | Commit the file; use `Path(__file__)`-based paths |
| LLM mode absent | No cloud secret | Add `OPENAI_API_KEY` in app settings; reboot |
| Free LLM mode absent | Groq secret is missing or misspelled | Add `GROQ_API_KEY` and `GROQ_MODEL` in app settings; reboot |
| LLM turn uses fallback | Provider timeout, authentication failure, or quota limit | Inspect the non-sensitive trace category; verify the key and Groq account limits |
| Build works locally only | Python/dependency mismatch | Match local and cloud Python versions; pin dependencies |
| Secret visible in GitHub | Secret file committed | Revoke/rotate the key, remove from history, and use Streamlit Secrets |
