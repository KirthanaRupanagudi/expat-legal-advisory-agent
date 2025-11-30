import re
PRIVACY_DISCLAIMER = (
    "Privacy Notice: Your input may contain sensitive legal information. "
    "We do not persist document contents."
)

def sanitize_input(text: str) -> str:
    text = re.sub(r"<[^>]*>", "", str(text or ""))
    text = re.sub(r"\s+", " ", text).strip()
    return text[:10000]

class ContextEngine:
    def build_context(self, user_input, session_data=None, document_content=None):
        parts = []
        parts.append(f"Context(session={session_data or {}})")
        parts.append(f"Input={sanitize_input(user_input)}")
        if document_content:
            parts.append(f"Document={sanitize_input(document_content)}")
        return " ".join(parts)
