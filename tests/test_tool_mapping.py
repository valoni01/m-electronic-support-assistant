from app.services.llm_service import LLMService


def test_mcp_tool_converts_to_openai_tool():
    service = LLMService()

    tools = [
        {
            "name": "check_inventory",
            "description": "Check product inventory",
            "input_schema": {
                "type": "object",
                "properties": {
                    "sku": {"type": "string"}
                },
                "required": ["sku"],
            },
        }
    ]

    result = service.convert_mcp_tools_to_openai_tools(tools)

    assert result[0]["type"] == "function"
    assert result[0]["function"]["name"] == "check_inventory"