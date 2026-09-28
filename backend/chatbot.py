"""
chatbot.py
----------
This file contains only the AI/LLM chatbot logic (using Google Gemini) —
no OCR/document processing code lives here. Plug it into your existing
main.py with just 2 lines (see "WHAT TO ADD IN MAIN.PY" below).

Setup:
    pip install google-generativeai python-dotenv

    Create a ".env" file in the same folder as main.py and add:
        GEMINI_API_KEY=your-actual-gemini-key-here
"""

import os
import re
import json
import google.generativeai as genai
from fastapi import APIRouter, Form, HTTPException
from dotenv import load_dotenv

load_dotenv()  # Loads variables from the .env file next to main.py

router = APIRouter()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

MODEL_NAME = "gemini-3.6-flash"


def get_llm_answer(raw_text: str, query: str, doc_type: str = "generic") -> str:
    """
    Sends the OCR-extracted raw_text and the user's query to Gemini, and
    returns a clean, direct, natural-language answer. The model can also
    correct small OCR mistakes (e.g. "PAN" misread as "PEN") when the
    context makes it clear.
    """
    if not raw_text or not raw_text.strip():
        return "No readable text was extracted from the document, so I can't answer that."

    if not GEMINI_API_KEY:
        return "AI can't answer because GEMINI_API_KEY is not set. Add it to your .env file and restart the server."

    system_prompt = (
        "You are a document assistant that reads OCR-extracted text and gives "
        "the user a direct, clean answer to their question. OCR sometimes "
        "misreads characters (e.g. PAN as PEN, 0 as O) - if it's clear from "
        "context that this happened, correct it in your answer. "
        "If the answer isn't found in the document, say so plainly. "
        "Keep answers short and direct - no extra formatting or prefixes "
        "like 'Answer:'. Only mention the document type if the user "
        "specifically asked about it; otherwise answer the question directly."
    )

    user_message = (
        f"Document type: {doc_type}\n\n"
        f"OCR-extracted text:\n\"\"\"\n{raw_text}\n\"\"\"\n\n"
        f"Question: {query}"
    )

    try:
        model = genai.GenerativeModel(
            model_name=MODEL_NAME,
            system_instruction=system_prompt,
        )
        response = model.generate_content(user_message)
        answer_text = (response.text or "").strip()
        return answer_text if answer_text else "Could not generate an answer."
    except Exception as e:
        return f"Error while getting an answer from the AI: {str(e)}"


@router.post("/chatbot/ask")
async def chatbot_ask(
    raw_text: str = Form(...),
    query: str = Form(...),
    doc_type: str = Form("generic"),
):
    """
    Standalone endpoint: send the OCR raw_text you already extracted, the
    user's query, and an optional doc_type - returns a real AI-generated
    answer (ai_answer).

    How the frontend should call it (this is ADDITIONAL to your existing
    /extract/ endpoint, not a replacement):

        POST /chatbot/ask
        form-data:
            raw_text = <raw_text returned by extract_document>
            query    = <user's question>
            doc_type = <optional, e.g. "pan", "aadhaar">
    """
    if not query or not query.strip():
        raise HTTPException(status_code=400, detail="query field cannot be empty.")

    answer = get_llm_answer(raw_text, query, doc_type)
    return {"status": "success", "ai_answer": answer}


def get_structured_fields(raw_text: str, doc_type: str = "generic") -> list:
    """
    Sends the raw OCR text to Gemini and asks it to pull out clean,
    labeled key-value fields (e.g. Name, PAN Number, Father's Name, DOB)
    instead of showing every individual noisy OCR word as its own field.
    Returns a list of {"label": ..., "value": ...} dicts.
    """
    if not raw_text or not raw_text.strip():
        return []

    if not GEMINI_API_KEY:
        return []

    system_prompt = (
        "You are a document data-extraction assistant. You will be given "
        "OCR-extracted text from an identity/official document, which may "
        "contain OCR noise (garbled or misread words). Your job is to "
        "identify only the genuine, meaningful fields on the document "
        "(e.g. Name, Father's Name, Date of Birth, Document Number, "
        "Address, Gender) and their values, correcting obvious OCR "
        "mistakes when the context makes the correction clear. "
        "Ignore boilerplate/noise words that are not real field values "
        "(e.g. government department headers, random single letters, "
        "misread fragments). "
        "Respond with ONLY a valid JSON array, no other text, no markdown "
        "fences. Each item must be an object with exactly two keys: "
        "\"label\" and \"value\". Example: "
        "[{\"label\": \"Name\", \"value\": \"RAHUL MISHRA\"}, "
        "{\"label\": \"PAN Number\", \"value\": \"ELWPM8089J\"}]"
    )

    user_message = (
        f"Document type: {doc_type}\n\n"
        f"OCR-extracted text:\n\"\"\"\n{raw_text}\n\"\"\""
    )

    try:
        model = genai.GenerativeModel(
            model_name=MODEL_NAME,
            system_instruction=system_prompt,
        )
        response = model.generate_content(user_message)
        text = (response.text or "").strip()

        # Gemini sometimes wraps JSON in ```json ... ``` fences - strip those.
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.IGNORECASE)

        parsed = json.loads(text)
        if isinstance(parsed, list):
            clean = []
            for item in parsed:
                if isinstance(item, dict) and item.get("label") and item.get("value"):
                    clean.append({
                        "label": str(item["label"]).strip(),
                        "value": str(item["value"]).strip(),
                    })
            return clean
        return []
    except Exception:
        # Agar JSON parse fail ho ya AI call me koi issue aaye, to bas
        # empty list return karein - frontend fallback pe chala jayega.
        return []


@router.post("/chatbot/extract_fields")
async def chatbot_extract_fields(
    raw_text: str = Form(...),
    doc_type: str = Form("generic"),
):
    """
    Returns clean, meaningful fields (Name, PAN Number, DOB, etc.)
    extracted from raw OCR text - for use in the "Extracted Fields" UI
    tab, INSTEAD OF showing every noisy individual OCR word.

        POST /chatbot/extract_fields
        form-data:
            raw_text = <raw_text returned by extract_document>
            doc_type = <optional, e.g. "pan", "aadhaar">
    """
    fields = get_structured_fields(raw_text, doc_type)
    return {"status": "success", "fields": fields}