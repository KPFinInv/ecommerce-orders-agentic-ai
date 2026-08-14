# Release 2.2: Free LLM Understanding with Governed Fallback

## Free assisted understanding

The application can now use OpenAI GPT OSS 20B through the GroqCloud free plan. The model receives the current request plus bounded conversational references and returns a typed intent with explicit identifiers. It does not receive a SQL tool, authorization authority, policy ownership, or permission to modify an order.

## Provider governance

The Streamlit application exposes provider modes only when their corresponding secret exists:

* deterministic demo;
* free LLM assisted using `openai/gpt-oss-20b` on GroqCloud;
* optional OpenAI assisted understanding.

Provider exceptions are mapped to non-sensitive operational categories. The request automatically falls back to deterministic classification, preserving the conversation and preventing credential or provider messages from appearing in the interface.

## Teaching evidence

The notebook now contains a provider architecture explanation, a secure readiness check, a flexible-language comparison experiment, a prompt pack, and detailed interpretation guidance. The presentation explains where the LLM adds value and which controls remain outside the model.

## Release verification

* Eleven automated tests pass.
* Fourteen of fourteen deterministic benchmark turns pass.
* The six-turn clarification workflow remains intact.
* A mocked structured LLM classification passes through the same authorization and grounding controls.
* Missing provider credentials trigger a successful deterministic fallback.
* No real secret is stored in source files, notebook outputs, presentation files, or the release archive.
