# app/tests/test_prompt_safety.py

from app.prompts.system_prompt import SYSTEM_PROMPT


def test_prompt_prevents_inventing_order_status():
    assert "Do not invent" in SYSTEM_PROMPT
    assert "order" in SYSTEM_PROMPT.lower()