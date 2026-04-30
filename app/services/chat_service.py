import json
import re
import time
from typing import Any
from uuid import uuid4

from app.observability.logging import get_logger
from app.observability.metrics import CHAT_ERRORS_TOTAL, CHAT_REQUESTS_TOTAL
from app.prompts.system_prompt import SYSTEM_PROMPT
from app.services.llm_service import LLMService
from app.services.mcp_service import MCPService


logger = get_logger(__name__)


class ChatService:
    """
    Coordinates:
    user message -> LLM -> MCP tool call -> tool result -> final LLM response.

    Also applies simple safety rules:
    - customer/order actions require authentication
    - create_order requires an authenticated customer_id
    - customer_id is stored after verify_customer_pin succeeds
    """

    def __init__(self):
        self.mcp_service = MCPService()
        self.llm_service = LLMService()

    async def respond(
        self,
        user_message: str,
        history: list[dict[str, str]],
        session_state: dict[str, Any] | None = None,
    ) -> tuple[str, dict[str, Any]]:
        start = time.perf_counter()
        conversation_turn_id = str(uuid4())

        CHAT_REQUESTS_TOTAL.inc()

        if session_state is None:
            session_state = self._default_session_state()

        logger.info(
            "chat_turn_started",
            conversation_turn_id=conversation_turn_id,
            is_authenticated=session_state.get("is_authenticated", False),
            history_length=len(history or []),
        )

        try:
            mcp_tools = await self.mcp_service.list_tools()
            openai_tools = self.llm_service.convert_mcp_tools_to_openai_tools(
                mcp_tools
            )

            messages = self._build_messages(
                user_message=user_message,
                history=history,
                session_state=session_state,
            )

            first_response = self.llm_service.create_response(
                messages=messages,
                tools=openai_tools,
            )

            assistant_message = first_response.choices[0].message

            if not assistant_message.tool_calls:
                duration_ms = round((time.perf_counter() - start) * 1000, 2)

                logger.info(
                    "chat_turn_completed",
                    conversation_turn_id=conversation_turn_id,
                    duration_ms=duration_ms,
                    tool_call_count=0,
                    is_authenticated=session_state.get("is_authenticated", False),
                )

                return assistant_message.content or "", session_state

            messages.append(assistant_message)

            tool_call_count = len(assistant_message.tool_calls)

            for tool_call in assistant_message.tool_calls:
                tool_name = tool_call.function.name
                arguments = self._parse_tool_arguments(tool_call.function.arguments)

                logger.info(
                    "chat_tool_requested",
                    conversation_turn_id=conversation_turn_id,
                    tool_name=tool_name,
                )

                blocked_message = self._block_unsafe_tool_call(
                    tool_name=tool_name,
                    arguments=arguments,
                    session_state=session_state,
                )

                if blocked_message:
                    duration_ms = round((time.perf_counter() - start) * 1000, 2)

                    logger.info(
                        "chat_tool_blocked",
                        conversation_turn_id=conversation_turn_id,
                        tool_name=tool_name,
                        reason="auth_or_safety_gate",
                        duration_ms=duration_ms,
                    )

                    return blocked_message, session_state

                tool_result = await self.mcp_service.call_tool(
                    tool_name=tool_name,
                    arguments=arguments,
                )

                session_state = self._update_session_state_from_tool_result(
                    tool_name=tool_name,
                    arguments=arguments,
                    result=tool_result,
                    session_state=session_state,
                )

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": self._tool_result_to_text(tool_result),
                    }
                )

            final_response = self.llm_service.create_response(messages=messages)

            duration_ms = round((time.perf_counter() - start) * 1000, 2)

            logger.info(
                "chat_turn_completed",
                conversation_turn_id=conversation_turn_id,
                duration_ms=duration_ms,
                tool_call_count=tool_call_count,
                is_authenticated=session_state.get("is_authenticated", False),
            )

            return final_response.choices[0].message.content or "", session_state

        except Exception as error:
            CHAT_ERRORS_TOTAL.inc()

            duration_ms = round((time.perf_counter() - start) * 1000, 2)

            logger.exception(
                "chat_turn_failed",
                conversation_turn_id=conversation_turn_id,
                duration_ms=duration_ms,
                error=str(error),
            )

            return (
                "Sorry, I’m having trouble connecting to Meridian’s support systems right now. "
                "Please try again in a moment.",
                session_state,
            )

    def _build_messages(
        self,
        user_message: str,
        history: list[dict[str, str]],
        session_state: dict[str, Any],
    ) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "system", "content": self._build_auth_context(session_state)},
        ]

        for item in history:
            user_text = item.get("user")
            assistant_text = item.get("assistant")

            if user_text:
                messages.append({"role": "user", "content": user_text})

            if assistant_text:
                messages.append({"role": "assistant", "content": assistant_text})

        messages.append({"role": "user", "content": user_message})

        return messages

    def _build_auth_context(self, session_state: dict[str, Any]) -> str:
        if session_state.get("is_authenticated"):
            return (
                "Current customer session: authenticated. "
                f"customer_id={session_state.get('customer_id')}. "
                "Use this customer_id for customer-specific order actions. "
                "Do not ask the customer to authenticate again unless a tool fails."
            )

        return (
            "Current customer session: not authenticated. "
            "For order history, customer details, or order creation, ask the customer "
            "for their email address and 4-digit PIN first."
        )

    def _block_unsafe_tool_call(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        session_state: dict[str, Any],
    ) -> str | None:
        customer_specific_tools = {
            "get_customer",
            "list_orders",
            "create_order",
        }

        if tool_name in customer_specific_tools and not session_state.get(
            "is_authenticated"
        ):
            return (
                "I can help with that, but I need to verify your identity first. "
                "Please provide the email address on your Meridian account and your 4-digit PIN."
            )

        if tool_name == "create_order":
            authenticated_customer_id = session_state.get("customer_id")

            if not authenticated_customer_id:
                return (
                    "I need to verify your identity before I can create an order. "
                    "Please provide the email address on your Meridian account and your 4-digit PIN."
                )

            # Force all created orders to belong to the authenticated customer.
            arguments["customer_id"] = authenticated_customer_id

            items = arguments.get("items")

            if not items or not isinstance(items, list):
                return (
                    "I need the product SKU, quantity, and price before I can create the order."
                )

            for item in items:
                if not isinstance(item, dict):
                    return "I need valid order item details before I can create the order."

                if not item.get("sku"):
                    return "I need the product SKU before I can create the order."

                if not item.get("quantity"):
                    return "I need the quantity before I can create the order."

                if not item.get("unit_price"):
                    return "I need the unit price before I can create the order."

        return None

    def _update_session_state_from_tool_result(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        result: Any,
        session_state: dict[str, Any],
    ) -> dict[str, Any]:
        if tool_name != "verify_customer_pin":
            return session_state

        result_text = self._tool_result_to_text(result)
        customer_id = self._extract_customer_id(result_text)

        if customer_id:
            session_state["is_authenticated"] = True
            session_state["customer_id"] = customer_id
            session_state["customer_email"] = arguments.get("email")

            logger.info(
                "customer_authenticated",
                customer_id=customer_id,
                # Do not log PIN. Email is okay for demo, but in stricter production,
                # prefer hashing or omitting it.
                customer_email=arguments.get("email"),
            )

        return session_state

    def _extract_customer_id(self, text: str) -> str | None:
        uuid_pattern = (
            r"[0-9a-fA-F]{8}-"
            r"[0-9a-fA-F]{4}-"
            r"[0-9a-fA-F]{4}-"
            r"[0-9a-fA-F]{4}-"
            r"[0-9a-fA-F]{12}"
        )

        match = re.search(uuid_pattern, text)

        return match.group(0) if match else None

    def _parse_tool_arguments(self, raw_arguments: str | None) -> dict[str, Any]:
        if not raw_arguments:
            return {}

        try:
            return json.loads(raw_arguments)
        except json.JSONDecodeError:
            logger.warning("tool_arguments_parse_failed")
            return {}

    def _tool_result_to_text(self, result: Any) -> str:
        """
        MCP tool results often come back as:
        result.content = [TextContent(type='text', text='...')]

        This converts the MCP result into plain text for the LLM.
        """

        if hasattr(result, "content"):
            parts = []

            for item in result.content:
                if hasattr(item, "text"):
                    parts.append(item.text)
                else:
                    parts.append(str(item))

            return "\n".join(parts)

        return str(result)

    def _default_session_state(self) -> dict[str, Any]:
        return {
            "is_authenticated": False,
            "customer_id": None,
            "customer_email": None,
        }