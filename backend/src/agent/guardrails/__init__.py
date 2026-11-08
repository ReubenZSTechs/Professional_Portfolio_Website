"""Defense-in-depth guardrails for the chat agent (docs/security.md).

history.py       signed assistant turns: forged history is dropped
normalize.py     Unicode/obfuscation normalisation before any check
patterns.py      weighted prompt-injection rules (English + Indonesian)
input_guard.py   deterministic pre-LLM screening: block / suspicious / clean
spotlight.py     fence untrusted text (visitor message, passages) with nonce delimiters
output_guard.py  streaming check for canary / system-prompt leakage
"""

REFUSAL = (
    "I can only answer questions about Reuben's work: his projects, experience, skills and "
    "research. What would you like to know?"
)
