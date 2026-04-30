import asyncio
import json
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


MCP_SERVER_URL = "https://order-mcp-74afyau24q-uc.a.run.app/mcp"


def pretty_print(value):
    try:
        print(json.dumps(value, indent=2, default=str))
    except TypeError:
        print(value)


async def main():
    async with streamable_http_client(MCP_SERVER_URL) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            print("\nConnected to MCP server")

            tools_response = await session.list_tools()

            print("\nAvailable tools:")
            for tool in tools_response.tools:
                print("\n-------------------------")
                print(f"Name: {tool.name}")
                print(f"Description: {tool.description}")
                print("Input schema:")
                pretty_print(tool.inputSchema)


if __name__ == "__main__":
    asyncio.run(main())