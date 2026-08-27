# Release 2.3: Provider-independent Webinar Conversation

## Defect corrected

When Groq authentication, availability, or quota failed, flexible language such as “what came
in that parcel?” and “how long is the monitor covered?” previously fell through to general
help. Order memory remained intact, but the narrow fallback vocabulary prevented retrieval and
product-policy stages from running.

## Improvements

* Expanded the governed classifier for parcel contents, product coverage, changed-mind returns,
  conversational delivery questions, and natural cancellation language.
* Strengthened the LLM instruction with explicit intent definitions and bounded examples.
* Added natural duration formatting such as `3-year warranty` and `30-day return window`.
* Added Bob Smith's complete eight-turn script as a visible, customer-specific Streamlit guide.
* Replaced Bob's irrelevant Smartwatch prompt with his actual 4K monitor workflow.
* Added a session-schema migration so stale browser sessions reset cleanly after deployment.
* Clarified whether fallback was caused by authentication, rate limit, timeout, connectivity,
  missing credentials, or another provider error without exposing secrets.

## Release gate

The twelve-test suite now includes Bob Smith's complete eight-turn journey while Groq returns an
authentication failure. The expected intents, ORD1003 memory, monitor and blender context,
return-policy result, honest delivery response, cancellation handoff, write protection, and
conversation closure must all pass.
