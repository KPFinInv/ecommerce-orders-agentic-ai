# Release 2.1: Clarification Continuity and Notebook Reliability

## Conversation continuity

The agent now preserves three distinct layers of conversational context:

* `pending_intent`: the unfinished task that caused a clarification;
* `active_order_id`: the governed order selected for later turns;
* `active_product_name`: the product reference reused by warranty and return questions.

If Alice asks which products are in an unspecified order, the agent safely lists recent owned orders. A reply containing only `ORD1009` resumes the original product request. The same session then remains relevant through warranty, tracking, delivery, and return questions.

The clarification state does not bypass authorization. Every retrieval still confirms that the selected order belongs to the active customer.

## Regression coverage

The automated suite now contains nine tests. The labelled evaluation benchmark contains fourteen turns, including the complete six-turn clarification-continuation scenario.

## Notebook reliability

The notebook no longer runs `%pip install` inside the active kernel. Installation instructions now direct learners to a dedicated virtual environment before the webinar. This avoids dependency resolver conflicts with unrelated Anaconda, Azure ML, MLflow, and profiling packages.

All notebook file reads specify UTF-8 explicitly. This resolves the Windows `UnicodeDecodeError` caused by platform-default character encoding.

The delivered notebook has 38 cells, including 24 executed code cells. Its stored outputs were scanned for exceptions, tracebacks, warning streams, and dependency-conflict messages.

## Release verification

* Nine automated tests pass.
* Fourteen of fourteen labelled benchmark turns pass.
* The six-turn Streamlit workflow passes without repeated customer or order identifiers.
* The presentation passes overflow checks.
* The presentation PDF contains 24 visually reviewed pages.
