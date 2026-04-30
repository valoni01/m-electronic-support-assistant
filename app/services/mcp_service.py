from typing import Any, Dict, List
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from app.config import settings


class MCPService:
    def __init__(self):
        self.server_url = settings.mcp_server_url

    async def list_tools(self) -> List[Dict[str, Any]]:
        async with streamable_http_client(self.server_url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools_response = await session.list_tools()

                return [
                    {
                        "name": tool.name,
                        "description": tool.description or "",
                        "input_schema": tool.inputSchema,
                    }
                    for tool in tools_response.tools
                ]

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        async with streamable_http_client(self.server_url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)
                return result