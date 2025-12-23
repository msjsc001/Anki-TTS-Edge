import re

def sanitize_text(text):
    """
    Cleans up text for TTS generation.
    Preserves all Unicode characters including Chinese punctuation.
    Only removes control characters and normalizes whitespace.
    """
    if not text:
        return ""
    # Only remove control characters (except newline and tab which become spaces)
    # Keep all printable Unicode characters including Chinese punctuation
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    # Collapse multiple whitespace (spaces, tabs, newlines) into one space
    text = re.sub(r'\s+', ' ', text).strip()
    return text if text else ""