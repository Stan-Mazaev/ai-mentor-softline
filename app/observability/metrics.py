from prometheus_client import Counter, Histogram

LLM_REQUESTS = Counter(
    "llm_requests_total", "LLM requests", ["task", "outcome"]
)
LLM_TOKENS = Counter(
    "llm_tokens_total", "LLM tokens processed", ["direction"]
)
LLM_LATENCY = Histogram(
    "llm_latency_seconds", "LLM request latency", ["task"]
)