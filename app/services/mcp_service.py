import time
from typing import Any, Dict, List

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from app.config import settings
from app.observability.logging import get_logger
from app.observability.metrics import (
    MCP_TOOL_CALLS_TOTAL,
    MCP_TOOL_ERRORS_TOTAL,
    MCP_TOOL_DURATION_SECONDS,
)


logger = get_logger(__name__)


class MCPService:
    def __init__(self):
        self.server_url = settings.mcp_server_url

    async def list_tools(self) -> List[Dict[str, Any]]:
        start = time.perf_counter()

        logger.info("mcp_list_tools_started")

        try:
            async with streamablehttp_client(self.server_url) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools_response = await session.list_tools()

                    tools = [
                        {
                            "name": tool.name,
                            "description": tool.description or "",
                            "input_schema": tool.inputSchema,
                        }
                        for tool in tools_response.tools
                    ]

                    duration_ms = round((time.perf_counter() - start) * 1000, 2)

                    logger.info(
                        "mcp_list_tools_completed",
                        tool_count=len(tools),
                        duration_ms=duration_ms,
                    )

                    return tools

        except Exception as error:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)

            logger.exception(
                "mcp_list_tools_failed",
                duration_ms=duration_ms,
                error=str(error),
            )

            raise

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        start = time.perf_counter()

        MCP_TOOL_CALLS_TOTAL.labels(tool_name=tool_name).inc()

        logger.info(
            "mcp_tool_call_started",
            tool_name=tool_name,
            arguments=self._safe_arguments(arguments),
        )

        try:
            async with streamablehttp_client(self.server_url) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()

                    result = await session.call_tool(
                        tool_name,
                        arguments=arguments,
                    )

                    duration_seconds = time.perf_counter() - start
                    duration_ms = round(duration_seconds * 1000, 2)

                    MCP_TOOL_DURATION_SECONDS.labels(tool_name=tool_name).observe(
                        duration_seconds
                    )

                    logger.info(
                        "mcp_tool_call_completed",
                        tool_name=tool_name,
                        duration_ms=duration_ms,
                    )

                    return result

        except Exception as error:
            duration_seconds = time.perf_counter() - start
            duration_ms = round(duration_seconds * 1000, 2)

            MCP_TOOL_ERRORS_TOTAL.labels(tool_name=tool_name).inc()
            MCP_TOOL_DURATION_SECONDS.labels(tool_name=tool_name).observe(
                duration_seconds
            )

            logger.exception(
                "mcp_tool_call_failed",
                tool_name=tool_name,
                duration_ms=duration_ms,
                error=str(error),
            )

            raise

    def _safe_arguments(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Avoid logging sensitive data such as PINs.
        """

        redacted = dict(arguments)

        sensitive_keys = {"pin", "password", "token", "api_key"}

        for key in sensitive_keys:
            if key in redacted:
                redacted[key] = "***REDACTED***"

        return redacted