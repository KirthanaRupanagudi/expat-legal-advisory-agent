# project/tools/tools.py
import os
import ast
import operator
import requests
import time
import google.generativeai as genai
from PyPDF2 import PdfReader
from docx import Document as DocxDocument

# --- Utilities ---
def retry_generic(func, retries=3, delay=2, timeout=30, exceptions=(Exception,)):
    """
    Retry a function with exponential backoff and timeout.
    
    Args:
        func: Function to execute
        retries: Number of retry attempts
        delay: Initial delay between retries (doubles each attempt)
        timeout: Maximum time to wait for single execution (seconds)
        exceptions: Tuple of exceptions to catch
    
    Returns:
        Result from func()
    
    Raises:
        TimeoutError: If execution exceeds timeout
        Exception: If all retries fail
    """
    import threading
    
    for attempt in range(retries):
        result_container = []
        exception_container = []
        
        def target():
            try:
                result_container.append(func())
            except Exception as e:
                exception_container.append(e)
        
        # Run function in thread with timeout
        thread = threading.Thread(target=target)
        thread.daemon = True
        thread.start()
        thread.join(timeout=timeout)
        
        # Check if thread is still alive (timeout)
        if thread.is_alive():
            raise TimeoutError(f"Operation timed out after {timeout} seconds")
        
        # Check for exceptions
        if exception_container:
            e = exception_container[0]
            if isinstance(e, exceptions):
                if attempt < retries - 1:
                    # Exponential backoff
                    wait_time = delay * (2 ** attempt)
                    time.sleep(wait_time)
                else:
                    raise e
            else:
                raise e
        
        # Return result if successful
        if result_container:
            return result_container[0]
        
        # If no result and no exception, retry
        if attempt < retries - 1:
            time.sleep(delay)
    
    raise RuntimeError("Function did not return a result")

def summarizer(text, max_len=200):
    text = str(text or "")
    return text[:max_len] + '...' if len(text) > max_len else text

# --- Calculator ---
class SafeCalculator:
    OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv}

    @classmethod
    def evaluate(cls, expr):
        try:
            node = ast.parse(expr, mode='eval').body
            return cls._eval(node)
        except Exception:
            return 'Invalid expression'

    @classmethod
    def _eval(cls, node):
        # Use ast.Constant for Python 3.8+ compatibility
        if isinstance(node, ast.Constant):
            return node.value
        # Fallback for older Python versions
        if hasattr(ast, 'Num') and isinstance(node, ast.Num):
            return node.n
        if isinstance(node, ast.BinOp):
            return cls.OPS[type(node.op)](cls._eval(node.left), cls._eval(node.right))
        if isinstance(node, ast.UnaryOp):
            if isinstance(node.op, ast.UAdd):
                return +cls._eval(node.operand)
            if isinstance(node.op, ast.USub):
                return -cls._eval(node.operand)
        raise ValueError('Unsupported')

# --- Simple local search ---
class SimpleSearch:
    def __init__(self, corpus=None):
        self.corpus = corpus or []

    def add(self, doc_id, text):
        self.corpus.append({"id": doc_id, "text": str(text or "")})

    def query(self, q, top_k=3):
        ql = [w for w in str(q or "").lower().split() if w]
        scored = []
        for item in self.corpus:
            textl = item["text"].lower()
            score = sum(textl.count(w) for w in ql)
            if score:
                scored.append((score, item["id"], item["text"]))
        return sorted(scored, key=lambda x: -x[0])[:top_k]

# --- Domain tools ---
class DomainTools:
    VISA_KEYWORDS = ['visa', 'residence', 'permit', 'work', 'study', 'family', 'application', 'document']

    @classmethod
    def extract_visa_requirements(cls, text):
        t = str(text or "").lower()
        found = [k for k in cls.VISA_KEYWORDS if k in t]
        return {"has_visa_context": bool(found), "matched_keywords": found}

# --- Translator ---
class GoogleTranslator:
    ENDPOINT = 'https://translation.googleapis.com/language/translate/v2'

    def __init__(self):
        self.api_key = os.getenv('GOOGLE_API_KEY')
        if not self.api_key:
            raise RuntimeError('GOOGLE_API_KEY missing')

    def translate(self, text, target='en', source='auto'):
        def do():
            resp = requests.post(
                self.ENDPOINT,
                params={'key': self.api_key},
                json={'q': text, 'target': target, 'source': source, 'format': 'text'},
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json()['data']['translations'][0]['translatedText']
        return retry_generic(do)

# --- File extractors ---
def extract_pdf_text(pdf_path):
    """Extract text from PDF file with error handling."""
    try:
        if not pdf_path or not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        reader = PdfReader(pdf_path)
        pages = []
        for page in reader.pages:
            pages.append(page.extract_text() or "")
        return "".join(pages)
    except Exception as e:
        # For notebook/Colab compatibility, return empty string with warning
        print(f"⚠️  Warning: Could not extract PDF text from {pdf_path}: {e}")
        return ""

def extract_docx_text(docx_path):
    """Extract text from DOCX file with error handling."""
    try:
        if not docx_path or not os.path.exists(docx_path):
            raise FileNotFoundError(f"DOCX file not found: {docx_path}")
        
        doc = DocxDocument(docx_path)
        return "".join(p.text for p in doc.paragraphs)
    except Exception as e:
        # For notebook/Colab compatibility, return empty string with warning
        print(f"⚠️  Warning: Could not extract DOCX text from {docx_path}: {e}")
        return ""

# --- Gemini LLM ---
class GeminiLLM:
    MAX_RESPONSE_LENGTH = 2000 # Define max response length

    def __init__(self):
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            raise RuntimeError('GOOGLE_API_KEY missing for GeminiLLM')
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash-lite')

    def generate_response(self, user_question_original, user_question_en=None, document_content_en=None, citations=None, document_content_original=None, reply_language='en'):
        def _call():
            from project.ui.i18n import get_language_name
            prompt_parts = [
                "You are an expert legal aid advisor for expats. ",
                "If document translations are provided, use them for reasoning; ",
                "otherwise, reason directly over the original language content. ",
            ]
            prompt_parts.append(f"Original user question (language hint): {summarizer(user_question_original, 200)}")
            if user_question_en:
                prompt_parts.append(f"English-translated user question: {summarizer(user_question_en, 500)}")
            if document_content_en:
                prompt_parts.append(f"Translated legal document (for user's preferred language): {summarizer(document_content_en, 2000)}")
            elif document_content_original:
                prompt_parts.append(f"Original-language legal document (context): {summarizer(document_content_original, 2000)}")
            if citations:
                prompt_parts.append(f"Relevant excerpts: {summarizer(' | '.join(citations), 500)}")
            prompt_parts.append("Provide a precise, structured, and legally sound answer. Cite relevant parts when possible.")
            # FIX #3: Removed contradictory "Always respond in the language of the original user question"
            # Now only enforce the preferred reply language
            lang_name = get_language_name(reply_language)
            prompt_parts.append(f"Reply ONLY in {lang_name}. Do not use any other language.")
            response = self.model.generate_content("".join(prompt_parts))

            # Summarize the final response to ensure it's within limits
            return summarizer(response.text, self.MAX_RESPONSE_LENGTH)
        
        try:
            return retry_generic(_call)
        except Exception as e:
            # Log the actual error for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"LLM generation failed: {type(e).__name__}: {str(e)}", exc_info=True)
            
            # Return user-friendly error message
            error_msg = str(e).lower()
            if 'api key' in error_msg or 'authentication' in error_msg or 'invalid' in error_msg:
                return "Unable to generate response: Invalid API key. Please check your GOOGLE_API_KEY environment variable."
            elif 'quota' in error_msg or 'limit' in error_msg:
                return "Unable to generate response: API quota exceeded. Please try again later."
            elif 'timeout' in error_msg:
                return "Unable to generate response: Request timed out. Please try again."
            else:
                return f"Unable to generate response at this time. Error: {type(e).__name__}"
