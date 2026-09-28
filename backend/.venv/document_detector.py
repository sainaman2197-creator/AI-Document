def detect_document_type(text: str) -> str:
    text_lower = text.lower()
    
    if "aadhaar" in text_lower or "government of india" in text_lower or "unique identification authority" in text_lower:
        return "aadhaar"
    elif "income tax department" in text_lower or "permanent account number" in text_lower or "pancard" in text_lower:
        return "pan"
    elif "passport" in text_lower or "republic of india" in text_lower:
        return "passport"
    else:
        return "generic"