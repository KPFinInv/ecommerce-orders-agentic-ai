# Facilitator Guide: 90-minute Webinar

## Session outcome

Learners should leave able to explain an agent as a controlled state, routing, tool, policy, and evaluation system. They will observe multi-turn memory, inspect privacy and action boundaries, compare offline and customer-experience metrics, and understand the GitHub to Streamlit deployment path.

## Run of show

| Time | Segment | Instructor move | Learner outcome |
|---:|---|---|---|
| 0 to 6 min | Business hook | Contrast repeated identifiers with a natural multi-turn conversation | Recognize the gap between a parser and a support agent |
| 6 to 16 min | Agentic foundations | Define state, nodes, routing, memory, tools, guardrails, policy, and human approval | Build a precise mental model |
| 16 to 25 min | Data and risk | Audit customers, orders, items, and products; discuss privacy and write risk | Connect technical controls to the business process |
| 25 to 37 min | Executable architecture | Trace safe, ambiguous, denied, and blocked paths through the graph | Read a controlled LangGraph design |
| 37 to 54 min | Multi-turn lab | Run Bob Smith's three-turn conversation and inspect state plus trace | See identity and active-order memory working |
| 54 to 66 min | Boundary experiments | Demonstrate ambiguity, cross-customer denial, cancellation handoff, and write guardrail | Understand safe non-happy paths |
| 66 to 77 min | Data science evaluation | Run the labelled benchmark, confusion matrix, scorecard, and latency measure | Treat agent quality as an evaluation dataset |
| 77 to 83 min | Customer feedback | Submit a rating and discuss sample-size uncertainty | Separate self-evaluation from customer outcomes |
| 83 to 88 min | Streamlit and deployment | Show the live tabs and GitHub to Community Cloud operating model | Understand how the tested package becomes an application |
| 88 to 90 min | Close | Review production gaps and assign the extension | Leave with a practical next step |

## Pre-session checklist

* Use Python 3.11 or 3.12.
* Install `requirements.txt` at least one day before the webinar.
* Run `pytest` and confirm eight passing tests.
* Run every notebook cell from a fresh kernel.
* Run `streamlit run app.py` from repository root.
* Verify that the architecture SVG renders in the notebook and Streamlit.
* Submit one test feedback record, then explain that Community Cloud local storage can reset.
* Keep deterministic mode as the primary live path.
* If using optional LLM mode, store the API key only in secrets and set a usage limit.
* Open the deck, notebook, repository, deployed app, and Streamlit logs in separate tabs.
* Keep screenshots of the architecture, multi-turn trace, and benchmark as contingencies.

## Live demonstration sequence

### 1. Multi-turn memory

Select **Bob Smith, customer 2** once, then ask:

1. `Where is my latest order?`
2. `What products are in it?`
3. `Can I return the blender?`

Expected interpretation: the graph resolves ORD1003 on turn one and retains it as the active order. The later turns change intent but not customer scope or active order. Return policy uses the matched Portable Blender record and ends in human confirmation.

### 2. Ambiguity

Select **Charlie Brown, customer 3**, then ask `Can I return an order?`

Expected interpretation: several owned orders are plausible and no active order exists. The graph asks for one missing slot. Clarification is the correct result, not a failure.

### 3. Cross-customer privacy

Select **Alice Johnson, customer 1**, then ask `Show ORD1001`.

Expected interpretation: authorization fails, retrieval performs a safe skip, and the private order record remains absent from state.

### 4. Consequential action boundary

Select **Diana Prince, customer 4**, ask `Track ORD1002`, then `Cancel it`.

Expected interpretation: the policy node can assess cancellation eligibility, but the system creates a handoff proposal and keeps `write_executed` false.

### 5. Structural guardrail

Ask `Drop table orders`.

Expected interpretation: the trace contains only guardrail, respond, and evaluate. Understanding, authorization, tools, and policy do not run. The database still contains ten orders.

## Evaluation discussion

Use the benchmark table to ask four questions:

1. What exactly is labelled for each turn?
2. Which failure dimension would identify a wrong pronoun resolution?
3. Why can access-control success not be averaged away by high intent accuracy?
4. Why does 100 percent on eight curated turns not imply production accuracy?

Then compare the automated quality score with conversation feedback. Explain that internal controls can verify grounding and trace completeness, while only the customer can report perceived resolution and satisfaction.

## Likely learner questions

**Is deterministic routing really AI?**

It is a reliable control layer inside an agentic system. Optional model classification can expand language flexibility, but the state transitions, tools, authorization, and policy create the governed action system.

**Why not let the model generate SQL?**

Known support intents are better served by narrow, parameterized functions with read-only access. Text-to-SQL can be added later with schema allowlists, query inspection, row limits, protected columns, and a dedicated evaluation set.

**Why store active order separately from history text?**

Typed entity memory is deterministic, inspectable, and testable. A prose summary can omit, alter, or confuse identifiers.

**Why does cancellation require a human?**

The action changes customer and financial state. A proposal plus approval boundary is a safer teaching pattern than granting a conversational model direct write authority.

**Why keep customer rating separate from automated quality?**

The system can inspect its own trace but cannot truthfully infer satisfaction. Conflating the two creates circular evaluation.

## Student extension

Add a `delivery_exception` intent and at least ten labelled turns. Acceptance criteria:

* context memory works across a status question and exception follow-up;
* only the active customer can access the order;
* evidence includes the relevant status and delivery fields;
* the agent does not invent a courier event;
* serious exceptions produce a human handoff;
* benchmark metrics show the failure before and the improvement after the change.

## Production gates

1. Real authentication and object-level authorization.
2. Least-privilege tools and no model-controlled raw writes.
3. Grounded responses with field-level provenance.
4. Versioned policies and human approval for consequential changes.
5. Evaluation across happy paths, ambiguity, abuse, and policy edge cases.
6. Durable telemetry, feedback, monitoring, rollback, and incident response.
