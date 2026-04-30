# Meridian Electronics Support Chatbot

A small prototype of a customer support chatbot for Meridian Electronics.

The bot helps customers ask about products, check availability, look up orders, and place orders. It uses Meridian’s MCP server to access product, customer, and order data. The chatbot does not connect directly to the database.

## What it can do

- Search for products
- List products by category
- Get product details by SKU
- Verify a customer using email and PIN
- Show a customer’s orders
- Get order details
- Create an order

## Tech stack

- Python
- FastAPI
- Gradio
- uv
- MCP Python SDK
- OpenAI GPT-4o-mini
- Docker

## How it works

```txt
Customer
  -> Gradio chat UI
  -> FastAPI app
  -> LLM
  -> MCP server
  -> Meridian business systems