import json
from typing import List, Dict, Any

from app.prompts.system_prompt import SYSTEM_PROMPT
from app.services.mcp_service import MCPService
from app.services.llm_service import LLMService


class ChatService:
    def __init__(self):
        self.mcp_service = MCPService()
        self.llm_service = LLMService()

    async def respond(
        self,
        user_message: str,
        history: List[Dict[str, str]],
    ) -> str:
        mcp_tools = await self.mcp_service.list_tools()
        openai_tools = self.llm_service.convert_mcp_tools_to_openai_tools(mcp_tools)

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        for item in history:
            messages.append({"role": "user", "content": item["user"]})
            messages.append({"role": "assistant", "content": item["assistant"]})

        messages.append({"role": "user", "content": user_message})

        first_response = self.llm_service.create_response(
            messages=messages,
            tools=openai_tools,
        )

        assistant_message = first_response.choices[0].message

        if not assistant_message.tool_calls:
            return assistant_message.content or ""

        messages.append(assistant_message)

        for tool_call in assistant_message.tool_calls:
            tool_name = tool_call.function.name

            try:
                arguments = json.loads(tool_call.function.arguments or "{}")
                tool_result = await self.mcp_service.call_tool(tool_name, arguments)

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": str(tool_result),
                    }
                )

            except Exception:
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": "The tool call failed. Please respond with a helpful error message.",
                    }
                )

        final_response = self.llm_service.create_response(messages=messages)

        return final_response.choices[0].message.content or ""