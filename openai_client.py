# openai_client.py
import os
import json
import openai
from dotenv import load_dotenv
from procurement.logic import find_best_fuzzy_match

load_dotenv()  # loads .env
openai.api_key = os.getenv("OPENAI_API_KEY")

KNOWN_PRODUCTS = [
    "Laptop i7 16GB",
    "Desktop i5 8GB",
    "4K Monitor"
    # Add more if you expand vendor_data
]

def call_openai(prompt: str) -> str:
    """
    Simple wrapper around OpenAI ChatCompletion (GPT-3.5-turbo).
    Returns the assistant's text response.
    """
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful procurement assistant."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
        max_tokens=200
    )
    return response.choices[0].message.content

def llm_extract_requirements(user_input: str) -> dict:
    """
    Uses the LLM to parse a natural language procurement request
    into an exact product name from KNOWN_PRODUCTS plus a quantity integer.

    If the LLM fails or doesn't produce valid JSON, or doesn't pick a valid product,
    we'll fallback to fuzzy matching from the final text.
    """

    # 1) Provide the known product list to the LLM
    known_list_str = "\n".join(f"- {p}" for p in KNOWN_PRODUCTS)

    extraction_prompt = f"""
You are given a set of known products:
{known_list_str}

The user says: "{user_input}"

You must return a JSON object with exactly two fields:
  "item_name": (one from the known list above, if possible)
  "quantity": (an integer)

If you must guess the item_name, pick the closest from the known list.
If user_input doesn't specify a quantity, guess 1 or ask for clarification.
Output ONLY valid JSON, no extra text.
"""

    ai_text = call_openai(extraction_prompt)
    
    # 2) Attempt to parse JSON
    try:
        parsed = json.loads(ai_text)
    except json.JSONDecodeError:
        parsed = {}
    
    if not isinstance(parsed, dict):
        return {}

    # 3) Validate the LLM output
    item = parsed.get("item_name", "")
    qty = parsed.get("quantity", None)

    if not item or not qty:
        # Possibly fallback to fuzzy matching
        # If the user_input had something like "Need 10 laptops i7..."
        # The LLM might have returned partial or invalid. We'll try to salvage.
        return fallback_extract(user_input)
    
    # 4) If the item_name isn't in known list, fallback to fuzzy match
    if item not in KNOWN_PRODUCTS:
        # Attempt to fuzzy match it
        best_match = find_best_fuzzy_match(item)
        if best_match:
            item = best_match
    
    # Return final structured data
    return {
        "item_name": item,
        "quantity": qty
    }

def fallback_extract(user_input: str) -> dict:
    """
    Basic fallback if LLM didn't produce valid JSON or required fields.
    We'll just guess by using fuzzy matching on the entire user_input
    and parse out a quantity if we spot a digit.
    """
    # 1) Attempt to find quantity by searching digits
    import re
    numbers = re.findall(r"\d+", user_input)
    quantity = int(numbers[0]) if numbers else 1

    # 2) Fuzzy match the entire user_input to the known products
    best_match = find_best_fuzzy_match(user_input)
    if not best_match:
        # If we fail to find anything
        return {}
    
    return {
        "item_name": best_match,
        "quantity": quantity
    }
