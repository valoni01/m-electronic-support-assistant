import time
from typing import Any, Dict, List

from openai import OpenAI

from app.config import settings
from app.observability.logging import get_logger
from app.observability.metrics import (
    LLM_CALLS_TOTAL,
    LLM_CALL_DURATION_SECONDS,
)


logger = get_logger(__name__)


class LLMService:
    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.llm_model

    def convert_mcp_tools_to_openai_tools(
        self,
        mcp_tools: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["input_schema"],
                },
            }
            for tool in mcp_tools
        ]

    def create_response(self, messages, tools=None):
        start = time.perf_counter()

        LLM_CALLS_TOTAL.inc()

        logger.info(
            "llm_call_started",
            model=self.model,
            tool_count=len(tools or []),
            message_count=len(messages),
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools or [],
                tool_choice="auto" if tools else None,
                temperature=0.2,
            )

            duration_seconds = time.perf_counter() - start
            duration_ms = round(duration_seconds * 1000, 2)

            LLM_CALL_DURATION_SECONDS.observe(duration_seconds)

            usage = getattr(response, "usage", None)

            logger.info(
                "llm_call_completed",
                model=self.model,
                duration_ms=duration_ms,
                prompt_tokens=getattr(usage, "prompt_tokens", None),
                completion_tokens=getattr(usage, "completion_tokens", None),
                total_tokens=getattr(usage, "total_tokens", None),
            )

            return response

        except Exception as error:
            duration_seconds = time.perf_counter() - start
            duration_ms = round(duration_seconds * 1000, 2)

            LLM_CALL_DURATION_SECONDS.observe(duration_seconds)

            logger.exception(
                "llm_call_failed",
                model=self.model,
                duration_ms=duration_ms,
                error=str(error),
            )

            raise