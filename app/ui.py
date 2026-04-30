import gradio as gr
from app.services.chat_service import ChatService

chat_service = ChatService()


async def chat(user_message, history):
    formatted_history = []

    for user, assistant in history:
        formatted_history.append(
            {
                "user": user,
                "assistant": assistant,
            }
        )

    response = await chat_service.respond(user_message, formatted_history)

    return response


def build_ui():
    with gr.Blocks(title="Meridian Electronics Support Assistant") as mui:
        gr.Markdown(
            """
            # Meridian Electronics Support Assistant

            Ask about product availability, order history, or placing an order.
            """
        )

        gr.ChatInterface(
            fn=chat,
            chatbot=gr.Chatbot(height=500),
            textbox=gr.Textbox(
                placeholder="Ask about a product, order, or account...",
                container=False,
                scale=7,
            ),
            examples=[
                "Do you have wireless keyboards in stock?",
                "Can you help me check my order status?",
                "I want to place an order for a monitor.",
                "Can you look up my previous orders?",
            ],
        )

    return mui