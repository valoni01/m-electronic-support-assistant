from typing import Any, Dict, List
from openai import OpenAI

from app.config import settings


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
        return self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools or [],
            tool_choice="auto",
            temperature=0.2,
        )