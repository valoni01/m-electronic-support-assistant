from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response


CHAT_REQUESTS_TOTAL = Counter(
    "chat_requests_total",
    "Total number of chat requests",
)

CHAT_ERRORS_TOTAL = Counter(
    "chat_errors_total",
    "Total number of failed chat requests",
)

LLM_CALLS_TOTAL = Counter(
    "llm_calls_total",
    "Total number of LLM calls",
)

LLM_CALL_DURATION_SECONDS = Histogram(
    "llm_call_duration_seconds",
    "LLM call duration in seconds",
)

MCP_TOOL_CALLS_TOTAL = Counter(
    "mcp_tool_calls_total",
    "Total number of MCP tool calls",
    ["tool_name"],
)

MCP_TOOL_ERRORS_TOTAL = Counter(
    "mcp_tool_errors_total",
    "Total number of failed MCP tool calls",
    ["tool_name"],
)

MCP_TOOL_DURATION_SECONDS = Histogram(
    "mcp_tool_duration_seconds",
    "MCP tool call duration in seconds",
    ["tool_name"],
)


def metrics_response():
    return Response(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )