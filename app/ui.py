import gradio as gr
from app.services.chat_service import ChatService

chat_service = ChatService()


async def chat(user_message, history, session_state):
    if session_state is None:
        session_state = {
            "is_authenticated": False,
            "customer_id": None,
            "customer_email": None,
        }

    formatted_history = []

    for user, assistant in history:
        formatted_history.append(
            {
                "user": user,
                "assistant": assistant,
            }
        )

    response, updated_state = await chat_service.respond(
        user_message=user_message,
        history=formatted_history,
        session_state=session_state,
    )

    return response, updated_state


def build_ui():
    with gr.Blocks(title="Meridian Electronics Support Assistant") as mui:
        session_state = gr.State(
            {
                "is_authenticated": False,
                "customer_id": None,
                "customer_email": None,
            }
        )

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
                "Show me active monitors",
                "Search for wireless keyboards",
                "Tell me about SKU MON-0054",
                "I want to check my order history",
                "I want to place an order",
            ],
        )

    return mui