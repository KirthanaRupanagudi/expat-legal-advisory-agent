# project/agents/worker.py
from project.tools.tools import GoogleTranslator, GeminiLLM, SimpleSearch, DomainTools
from project.core.context_engineering import ContextEngine
from langdetect import detect, LangDetectException

class Worker:
    def __init__(self):
        self.llm = GeminiLLM()
        self.context_engine = ContextEngine()
        self.search = SimpleSearch()

    def _detect_language(self, text):
        """Auto-detect language using langdetect. Returns language code or 'en' on failure."""
        if not text or len(text) < 3:
            return 'en'
        try:
            detected = detect(text)
            # Map common codes: pt->es, zh-cn->auto, etc.
            lang_map = {'pt': 'es', 'zh-cn': 'en', 'zh-tw': 'en'}
            return lang_map.get(detected, detected)
        except LangDetectException:
            return 'en'

    def _translate_safe(self, text, target='en'):
        try:
            if not text:
                return None
            translator = GoogleTranslator()
            return translator.translate(text, target=target)
        except Exception as e:
            # Log but don't raise; fallback to original
            print(f"⚠️ Translation failed: {str(e)}")
            return None

    def execute(self, task):
        a = task.get("action")
        d = task.get("details", {})
        if a != "process":
            return "Unknown action"

        user_input_original = d.get("user_input", "")
        document = d.get("document")
        document_language = d.get("document_language", "auto")
        preferred_language = d.get("preferred_language", 'en')

        # Auto-detect document language if 'auto' is specified
        if document_language == "auto" and document:
            document_language = self._detect_language(document)
            print(f"📍 Auto-detected document language: {document_language}")

        # Translate question to English for internal reasoning
        user_input_en = self._translate_safe(user_input_original, target='en')

        # FIX #1 & #4: Translate document to preferred language (for user communication)
        # Also use document_language as source hint for better translation
        document_translated = self._translate_safe(document, target=preferred_language) if document else None

        # Also translate to English for search/reasoning if preferred language is not English
        document_en = self._translate_safe(document, target='en') if document and preferred_language != 'en' else document_translated

        # Build local search corpus using English content for better search accuracy
        doc_for_search = document_en or document or ""
        if doc_for_search:
            self.search.add("doc", doc_for_search)
        citations = [t for _, _, t in self.search.query(user_input_en or user_input_original, top_k=2)]
        domain_info = DomainTools.extract_visa_requirements(doc_for_search)

        # LLM generation: Pass translated document and enforced reply language
        # Use document_translated (in preferred language) for reasoning
        base = self.llm.generate_response(
            user_question_original=user_input_original,
            user_question_en=user_input_en,
            document_content_en=document_translated,
            citations=citations,
            document_content_original=document if (document and not document_translated) else None,
            reply_language=preferred_language
        )

        if domain_info.get("has_visa_context"):
            matched = ', '.join(domain_info.get('matched_keywords', []))
            base = f"{base}\n\n(Detected visa-related context: {matched})"

        return base
