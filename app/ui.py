import gradio as gr
from app.services.chat_service import ChatService

chat_service = ChatService()


def default_session_state():
    return {
        "is_authenticated": False,
        "customer_id": None,
        "customer_email": None,
    }


def normalize_history(history):

    formatted_history = []

    if not history:
        return formatted_history

    if isinstance(history[0], dict):
        pending_user_message = None

        for message in history:
            role = message.get("role")
            content = message.get("content")

            if role == "user":
                pending_user_message = content

            elif role == "assistant" and pending_user_message is not None:
                formatted_history.append(
                    {
                        "user": pending_user_message,
                        "assistant": content,
                    }
                )
                pending_user_message = None

        return formatted_history

    for item in history:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            formatted_history.append(
                {
                    "user": item[0],
                    "assistant": item[1],
                }
            )

    return formatted_history


async def chat(user_message, history, session_state):
    if session_state is None:
        session_state = default_session_state()

    formatted_history = normalize_history(history)

    response, updated_state = await chat_service.respond(
        user_message=user_message,
        history=formatted_history,
        session_state=session_state,
    )

    return response, updated_state


def build_ui():
    with gr.Blocks(title="Meridian Electronics Support Assistant") as mui:
        session_state = gr.State(default_session_state())

        gr.Markdown(
            """
            # Meridian Electronics Support Assistant

            Ask about product availability, product details, order history, or placing an order.
            """
        )

        chatbot = gr.Chatbot(height=500)

        gr.ChatInterface(
            fn=chat,
            chatbot=chatbot,
            additional_inputs=[session_state],
            additional_outputs=[session_state],
            textbox=gr.Textbox(
                placeholder="Ask about products, orders, or your account...",
                container=False,
                scale=7,
            ),
            examples=[
                ["Show me active monitors"],
                ["Search for wireless keyboards"],
                ["Tell me about SKU MON-0054"],
                ["I want to check my order history"],
                ["I want to place an order"],
            ],
        )

    return mui

