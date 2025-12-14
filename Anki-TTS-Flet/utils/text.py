import re

def sanitize_text(text):
    """
    Cleans up text for TTS generation.
    Removes unsupported characters and normalizes whitespace.
    """
    if not text:
        return ""
    # Remove characters that might cause issues, keeping punctuation and common symbols
    text = re.sub(r'[^\w\s\.,!?;:\'"()\[\]{}<>%&$@#*+\-=/]', '', text, flags=re.UNICODE)
    # Collapse multiple spaces into one
    text = re.sub(r'\s+', ' ', text).strip()
    return text if text else ""