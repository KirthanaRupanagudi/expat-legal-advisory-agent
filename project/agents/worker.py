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

    def _translate_safe(self, text: str, target: str = 'en', source_lang: str = 'auto') -> tuple[str, bool]:
        """
        Safely translate text with fallback to original.
        
        Returns:
            tuple of (translated_text, success_flag)
        """
        try:
            if not text:
                return "", True  # Empty string is valid
            translator = GoogleTranslator()
            result = translator.translate(text, target=target, source=source_lang)
            # Ensure result is not None
            if result is None:
                return text, False
            return result, True  # Translation succeeded
        except Exception as e:
            # Log but don't raise; fallback to original
            print(f"⚠️  Translation failed: {str(e)}")
            return text if text else "", False  # Translation failed, return original

    def execute(self, task: dict) -> str:
        """Execute worker task with document processing and translation."""
        if not isinstance(task, dict):
            return "Error: Invalid task format"
        
        action = task.get("action")
        details = task.get("details", {})
        
        if action != "process":
            return "Unknown action"

        user_input_original = details.get("user_input", "")
        document = details.get("document")
        document_language = details.get("document_language", "auto")
        preferred_language = details.get("preferred_language", 'en')

        # Auto-detect document language if 'auto' is specified
        if document_language == "auto" and document:
            document_language = self._detect_language(document)
            print(f"📍 Auto-detected document language: {document_language}")

        # Translate question to English for internal reasoning
        user_input_en, _ = self._translate_safe(user_input_original, target='en')

        # Translate document to preferred language (for user communication)
        # Use detected document_language as source hint for better translation
        document_translated = None
        document_en = None
        translation_succeeded = False
        
        if document:
            # Optimize: If preferred language is English, only translate once
            if preferred_language == 'en':
                translated, success = self._translate_safe(document, target='en', source_lang=document_language) if document_language not in ['en', 'auto'] else (document, True)
                document_en = translated
                document_translated = translated
                translation_succeeded = success
            else:
                # Translate to preferred language
                translated, success = self._translate_safe(document, target=preferred_language, source_lang=document_language) if document_language not in [preferred_language, 'auto'] else (document, True)
                document_translated = translated
                translation_succeeded = success
                # Also translate to English for search (if not already English)
                document_en, _ = self._translate_safe(document, target='en', source_lang=document_language) if document_language not in ['en', 'auto'] else (document, True)

        # Build local search corpus using English content for better search accuracy
        doc_for_search = document_en or document or ""
        if doc_for_search:
            self.search.add("doc", doc_for_search)
        citations = [t for _, _, t in self.search.query(user_input_en or user_input_original, top_k=2)]
        domain_info = DomainTools.extract_visa_requirements(doc_for_search)

        # LLM generation: Pass translated document and enforced reply language
        # If translation failed, pass original document for LLM to handle
        try:
            base = self.llm.generate_response(
                user_question_original=user_input_original,
                user_question_en=user_input_en,
                document_content_en=document_translated if translation_succeeded else None,
                citations=citations,
                document_content_original=document if (document and not translation_succeeded) else None,
                reply_language=preferred_language
            )
        except TimeoutError:
            return "I apologize, but the request took too long to process. Please try with a shorter document or simpler question."
        except Exception as e:
            print(f"⚠️  LLM generation failed: {str(e)}")
            base = None

        # Validate LLM response
        if not base or not isinstance(base, str):
            return "I apologize, but I couldn't generate a valid response at this time. Please try rephrasing your question."
        
        # Ensure response is not empty or too short
        if len(base.strip()) < 10:
            return "I apologize, but I couldn't generate a meaningful response. Please provide more context or rephrase your question."
        
        # Check for response quality indicators
        if base.strip().lower() in ['error', 'none', 'null', 'undefined']:
            return "I apologize, but I encountered an error while processing your request. Please try again."

        if domain_info.get("has_visa_context"):
            matched = ', '.join(domain_info.get('matched_keywords', []))
            base = f"{base}\n\n(Detected visa-related context: {matched})"

        return base
