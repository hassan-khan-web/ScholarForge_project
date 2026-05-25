# ScholarForge: Interactive Chat Engine

In this chapter, we look at the interactive chat assistant in `backend/chat_engine.py`. This component handles real-time conversational queries, context injection from uploaded documents, model fallbacks, and response formatting.

---

## Model Registry & Router Settings

The assistant supports multiple models via OpenRouter and Groq:

| Model ID | OpenRouter/Groq API Endpoint ID | Role / Specialized Target |
|---|---|---|
| **default** | `nvidia/nemotron-nano-12b-v2-vl:free` | Lightweight, efficient baseline model |
| **llama-70b** | `llama-3.3-70b-versatile` | Highly capable reasoning engine (Groq) |
| **gpt-oss** | `openai/gpt-oss-120b` | Dense, comprehensive answer generator |
| **gemma** | `google/gemma-3-27b-it:free` | Efficient, fast instruction-following model |
| **llama-8b** | `llama-3.1-8b-instant` | Quick, lower-latency fallback model |

The engine routes requests dynamically:
* If the selected model ID starts with `llama-`, it uses the **Groq API** endpoint (`https://api.groq.com/openai/v1/chat/completions`) using the `GROQ_API_KEY`.
* Otherwise, it queries **OpenRouter** (`https://openrouter.ai/api/v1/chat/completions`) using the `OPENROUTER_API_KEY`.

---

## Response Modes

The assistant operates in two distinct modes, controlled by system prompt instructions:

### 1. Standard Mode (`STANDARD_SYSTEM_PROMPT`)
* Emulates general assistants (like ChatGPT or Gemini).
* Focuses on clear explanations, markdown styling (using `##` for section headers), and code examples.
* Keeps a conversational, helpful tone.

### 2. Deep Dive Mode (`DEEP_DIVE_PROMPT`)
* Adopts the persona of a Senior Post-Doctoral Research Analyst.
* Enforces a structured, academic layout:
  1. **Executive Summary**: A concise summary of the core concepts.
  2. **Theoretical Framework / Core Mechanics**: Technical explanations using `###` sub-headers.
  3. **Comparative Analysis**: A markdown table comparing alternatives.
  4. **Real-World Implications**: Specific use cases and impacts.
  5. **Critical Limitations & Future Outlook**: Bottlenecks and outlook.
* **Reasoning Trace**: Requires the model to enclose its reasoning process inside `<think>...</think>` HTML tags before outputting the final response.

---

## Document Context Injection

If the user uploads documents in the chat interface, the assistant extracts their text contents and appends them to the system instructions:

```text
CONTEXT FROM ATTACHED FILES:
--- FILE: notes.txt ---
[Content here...]
------------------------

Use the above context to answer the user's question if relevant.
```

This context injection makes the assistant aware of the uploaded files without requiring a separate vector database (RAG) system for moderate-sized files.

---

## Fallback Routing & Rate Limiting

Network requests to AI APIs can fail due to rate limits or timeouts. The chat engine implements a fallback mechanism to handle these errors:

```python
# Fallback order for models
FALLBACK_ORDER = ["llama-70b", "llama-8b", "gpt-oss", "gemma", "default"]
```

1. **Model Fallback**:
   If the user's selected model fails (e.g., due to an API outage), the engine automatically tries alternative models in the order defined by `FALLBACK_ORDER`.
2. **Exponential Backoff**:
   If the API returns an HTTP `429 Rate Limit Exceeded` code, the engine catches it, calculates an exponential backoff delay with a random jitter (`(2 ** attempt) + random.uniform(0.5, 1.5)`), pauses execution, and retries.
3. **Server-Side Failover**:
   For HTTP errors like `502 Bad Gateway` or `503 Service Unavailable`, the engine immediately switches to the next fallback model to minimize wait times.

This setup ensures the chat interface remains responsive even during API outages. Let's move on to **Chapter 6: The Council Multi-Agent System** to examine the collaborative writing agent loop.
