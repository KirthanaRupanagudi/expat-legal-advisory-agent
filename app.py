import gradio as gr
from project.main_agent import run_agent
from project.tools.tools import extract_pdf_text, extract_docx_text
from project.ui.i18n import t
import subprocess
import os
import logging
from pathlib import Path
from typing import Optional, Tuple, List, Any, Dict
from datetime import datetime
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Validate API key on startup
def check_api_key():
    """Verify that GOOGLE_API_KEY is set in environment."""
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        logger.error("GOOGLE_API_KEY environment variable is not set!")
        return False
    logger.info("✓ GOOGLE_API_KEY is configured")
    return True

API_KEY_CONFIGURED = check_api_key()

# Usage Monitoring Configuration
USAGE_LOG_FILE = os.getenv('USAGE_LOG_FILE', 'usage_stats.json')
DAILY_QUERY_LIMIT = int(os.getenv('DAILY_QUERY_LIMIT', '1000'))  # Configurable limit
ALERT_THRESHOLD = int(os.getenv('ALERT_THRESHOLD', '800'))  # Alert at 80%

# Usage tracking state
usage_stats = {
    'total_queries': 0,
    'daily_queries': 0,
    'last_reset': datetime.now().strftime('%Y-%m-%d'),
    'document_uploads': 0,
    'language_usage': {},
    'errors': 0
}

def log_usage(event_type: str, details: Optional[dict] = None):
    """Log usage statistics for monitoring."""
    global usage_stats
    
    # Reset daily counter if new day
    today = datetime.now().strftime('%Y-%m-%d')
    if usage_stats['last_reset'] != today:
        logger.info(f"📊 Daily reset - Previous day queries: {usage_stats['daily_queries']}")
        usage_stats['daily_queries'] = 0
        usage_stats['last_reset'] = today
    
    # Update counters
    if event_type == 'query':
        usage_stats['total_queries'] += 1
        usage_stats['daily_queries'] += 1
        
        # Track language usage
        if details and 'language' in details:
            lang = details['language']
            usage_stats['language_usage'][lang] = usage_stats['language_usage'].get(lang, 0) + 1
        
        # Alert if approaching limit
        if usage_stats['daily_queries'] >= ALERT_THRESHOLD:
            logger.warning(f"⚠️  USAGE ALERT: {usage_stats['daily_queries']}/{DAILY_QUERY_LIMIT} daily queries used")
        
        # Log milestone queries
        if usage_stats['total_queries'] % 100 == 0:
            logger.info(f"🎯 Milestone: {usage_stats['total_queries']} total queries processed")
            
    elif event_type == 'document_upload':
        usage_stats['document_uploads'] += 1
        
    elif event_type == 'error':
        usage_stats['errors'] += 1
    
    # Log current stats
    logger.info(f"📈 Usage: {usage_stats['daily_queries']}/{DAILY_QUERY_LIMIT} today | {usage_stats['total_queries']} total | {usage_stats['document_uploads']} docs | {usage_stats['errors']} errors")
    
    # Optionally save to file for persistence
    try:
        with open(USAGE_LOG_FILE, 'w') as f:
            json.dump({
                **usage_stats,
                'timestamp': datetime.now().isoformat(),
                'details': details
            }, f, indent=2)
    except Exception as e:
        logger.debug(f"Could not write usage log: {e}")

def check_daily_limit() -> Tuple[bool, str]:
    """Check if daily query limit has been reached."""
    if usage_stats['daily_queries'] >= DAILY_QUERY_LIMIT:
        logger.error(f"🚫 DAILY LIMIT REACHED: {usage_stats['daily_queries']}/{DAILY_QUERY_LIMIT}")
        return False, f"⚠️ **Daily query limit reached ({DAILY_QUERY_LIMIT} queries).** Please try again tomorrow. This limit helps us manage API costs and ensure service availability for everyone."
    return True, ""

# Constants
MAX_Q = 15
MAX_Q_LEN = 5000
MAX_DOC_LEN = 1000000

# Language codes
SUPPORTED_LANGUAGES = {'en', 'es', 'fr', 'nl', 'de'}
VALID_DOC_LANGS = {'auto'} | SUPPORTED_LANGUAGES  # Document can be auto-detected
VALID_RESPONSE_LANGS = SUPPORTED_LANGUAGES  # Response must be a specific language

def read_doc_file(doc_path: str) -> str:
    """Convert .doc to .txt using LibreOffice headless conversion.
    
    Args:
        doc_path: Path to the .doc file
        
    Returns:
        Extracted text content
        
    Raises:
        RuntimeError: If conversion fails or path is invalid
    """
    try:
        # Sanitize path to prevent path traversal
        safe_path = Path(doc_path).resolve()
        if '..' in str(safe_path) or not safe_path.exists():
            raise RuntimeError("❌ Invalid or inaccessible file path")
        
        txt_path = str(safe_path).replace('.doc', '.txt')
        output_dir = os.path.dirname(str(safe_path))
        
        subprocess.run(
            ['soffice', '--headless', '--convert-to', 'txt', '--outdir', output_dir, str(safe_path)],
            check=True,
            timeout=30,
            capture_output=True
        )
        
        with open(txt_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        raise RuntimeError("❌ LibreOffice not installed. Please install it or upload a .docx/.pdf file instead.")
    except subprocess.TimeoutExpired:
        raise RuntimeError("❌ .doc conversion timed out. Document may be too large.")
    except Exception as e:
        raise RuntimeError(f"❌ Failed to convert .doc file: {str(e)}")

def validate_inputs(user_input: str, doc_content: Optional[str], doc_lang: str, pref_lang: str) -> List[str]:
    """Validate user inputs before processing.
    
    Args:
        user_input: User's question text
        doc_content: Optional document content
        doc_lang: Document language code
        pref_lang: Preferred response language code
        
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    # Validate question
    if not user_input or len(user_input.strip()) == 0:
        errors.append("❌ Question cannot be empty.")
    elif len(user_input) > MAX_Q_LEN:
        errors.append(f"❌ Question too long (max {MAX_Q_LEN} chars).")

    # Validate document
    if doc_content and len(doc_content) > MAX_DOC_LEN:
        errors.append(f"❌ Document too large (max {MAX_DOC_LEN} chars).")

    # Validate language codes
    if doc_lang not in VALID_DOC_LANGS:
        errors.append(f"❌ Invalid document language: {doc_lang}")
    if pref_lang not in VALID_RESPONSE_LANGS:
        errors.append(f"❌ Invalid reply language: {pref_lang}")

    return errors

def process_input(
    user_input: str,
    legal_document: Any,  # Gradio File type
    ui_lang: str,
    pref_lang: str,
    doc_lang: str,
    consent_given: bool,
    counter_state: Optional[int],
    progress: Any = gr.Progress()  # Gradio Progress type
) -> Tuple[Dict[str, Any], int]:
    """Process user input with optional document upload.
    
    Args:
        user_input: User's question text
        legal_document: Optional uploaded document file
        ui_lang: UI display language code
        pref_lang: Preferred response language code
        doc_lang: Document language code
        consent_given: Whether user agreed to privacy notice
        counter_state: Current question counter
        progress: Gradio progress indicator
        
    Returns:
        Tuple[gr.update, int]: Gradio Markdown update with response and updated question counter
    """
    logger.info(f"Process started - Question: {'Yes' if user_input else 'No'}, Document: {'Yes' if legal_document else 'No'}")
    
    current = counter_state or 0
    
    # Check daily limit first
    limit_ok, limit_msg = check_daily_limit()
    if not limit_ok:
        return (gr.update(value=f"### {t('title', ui_lang)}\n\n{limit_msg}"), current)
    
    # Immediate validation checks (before progress bar)
    if not consent_given:
        logger.warning("Consent not given")
        return (gr.update(value=f"### {t('title', ui_lang)}\n\n⚠️ **Please agree to the privacy notice to proceed.**"), current)
    
    # Check for empty input immediately
    if not user_input or len(user_input.strip()) == 0:
        logger.warning("Empty question submitted")
        log_usage('error', {'type': 'empty_input', 'ui_lang': ui_lang})
        return (gr.update(value=f"### {t('title', ui_lang)}\n\n❌ **Error: Question cannot be empty.**\n\nPlease enter your legal question and try again."), current)
    
    if current >= MAX_Q:
        logger.warning(f"Question limit reached: {current}/{MAX_Q}")
        log_usage('error', {'type': 'session_limit', 'ui_lang': ui_lang})
        return (gr.update(value=f"### {t('title', ui_lang)}\n\n⚠️ **Limit reached:** You can ask a maximum of {MAX_Q} questions per session."), current)
    
    # Log successful query
    log_usage('query', {'language': pref_lang, 'has_document': bool(legal_document), 'ui_lang': ui_lang})
    
    # Now start processing with visual feedback
    progress(0, desc="🔄 Starting...")
    
    # Check API key before processing
    if not API_KEY_CONFIGURED:
        logger.error("API key not configured - cannot process request")
        return (gr.update(value="### ⚠️ Configuration Error\n\n**GOOGLE_API_KEY is not set.**\n\nPlease set the environment variable or add it in Hugging Face Spaces Secrets.\n\nFor local development:\n```bash\nexport GOOGLE_API_KEY='your-api-key-here'\n```"), current)

    progress(0.1, desc="✅ Validating inputs...")
    doc_content = None
    
    # Document extraction with specific exception handling
    try:
        if legal_document is not None:
            name = legal_document.name.lower()
            logger.info(f"Processing document: {name}")
            log_usage('document_upload', {'file_type': name.split('.')[-1], 'ui_lang': ui_lang})
            progress(0.2, desc="📄 Reading document...")
            
            if name.endswith('.pdf'):
                doc_content = extract_pdf_text(legal_document.name)
            elif name.endswith('.docx'):
                doc_content = extract_docx_text(legal_document.name)
            elif name.endswith('.doc'):
                doc_content = read_doc_file(legal_document.name)
            else:
                with open(legal_document.name, 'r', encoding='utf-8') as f:
                    doc_content = f.read()
            
            logger.info(f"Document processed, content length: {len(doc_content) if doc_content else 0}")
            progress(0.3, desc="✅ Document processed")
        else:
            logger.info("No document uploaded - processing question only")
            progress(0.3, desc="💬 Processing question...")
    except FileNotFoundError as e:
        logger.error(f"File not found: {legal_document.name}")
        log_usage('error', {'type': 'file_not_found', 'ui_lang': ui_lang})
        return (gr.update(value=f"### {t('title', ui_lang)}\n\n**Error reading document:**\n\n**Error Type:** File not found\n**Message:** {str(e)}\n\nPlease check the file and try again."), current)
    except UnicodeDecodeError as e:
        logger.error(f"Encoding error in document: {legal_document.name}")
        log_usage('error', {'type': 'encoding_error', 'ui_lang': ui_lang})
        return (gr.update(value=f"### {t('title', ui_lang)}\n\n**Error reading document:**\n\n**Error Type:** Encoding error\n**Message:** The file encoding is not supported. Please ensure the file is in UTF-8 format.\n\nPlease try another file."), current)
    except subprocess.TimeoutExpired:
        logger.error("Document conversion timed out")
        log_usage('error', {'type': 'conversion_timeout', 'ui_lang': ui_lang})
        return (gr.update(value=f"### {t('title', ui_lang)}\n\n**Error reading document:**\n\n**Error Type:** Timeout\n**Message:** Document conversion took too long. The file may be too large.\n\nPlease try a smaller file."), current)
    except Exception as e:
        logger.error(f"Error reading document: {type(e).__name__} - {str(e)}", exc_info=True)
        log_usage('error', {'type': 'document_processing', 'error': type(e).__name__, 'ui_lang': ui_lang})
        return (gr.update(value=f"### {t('title', ui_lang)}\n\n**Error reading document:**\n\n**Error Type:** {type(e).__name__}\n**Message:** {str(e)}\n\nPlease try another file."), current)

    # Validate all inputs
    progress(0.4, desc="Validating inputs...")
    validation_errors = validate_inputs(user_input, doc_content, doc_lang, pref_lang)
    if validation_errors:
        error_msg = "\n".join(validation_errors)
        logger.warning(f"Input validation error: {error_msg}")
        log_usage('error', {'type': 'validation', 'ui_lang': ui_lang})
        return (gr.update(value=f"### {t('title', ui_lang)}\n\n**Input Error:**\n\n{error_msg}"), current)

    # Run agent analysis
    try:
        logger.info(f"Running main agent with: user_input={user_input[:50]}..., doc_content={'Yes' if doc_content else 'No'}, doc_lang={doc_lang}, pref_lang={pref_lang}")
        progress(0.5, desc="🤖 AI is analyzing...")
        result = run_agent(user_input, doc_content, doc_lang, pref_lang)
        logger.info(f"Main agent finished successfully. Result type: {type(result)}, Keys: {result.keys() if isinstance(result, dict) else 'N/A'}")
        progress(0.9, desc="✨ Finalizing response...")
    except TimeoutError as e:
        logger.error(f"Agent processing timeout: {str(e)}")
        log_usage('error', {'type': 'agent_timeout', 'ui_lang': ui_lang})
        return (gr.update(value=f"### {t('title', ui_lang)}\n\n**Processing Timeout:**\n\nThe request took too long to process. Please try with a shorter document or simpler question."), current)
    except Exception as e:
        logger.error(f"Processing error from main agent: {str(e)}", exc_info=True)
        log_usage('error', {'type': 'agent_error', 'error': type(e).__name__, 'ui_lang': ui_lang})
        # Don't expose raw exception details to users for security
        return (gr.update(value=f"### {t('title', ui_lang)}\n\n**Processing Error:**\n\nAn unexpected error occurred while processing your request. Please try again or contact support if the issue persists."), current)

    # Validate result structure
    if not isinstance(result, dict):
        logger.error(f"Invalid result type: {type(result)}")
        return (gr.update(value=f"### {t('title', ui_lang)}\n\n**Processing Error:**\n\nReceived invalid response format from agent."), current)
    
    if 'response' not in result or 'confidence' not in result:
        logger.error(f"Missing keys in result: {result.keys()}")
        return (gr.update(value=f"### {t('title', ui_lang)}\n\n**Processing Error:**\n\nIncomplete response from agent."), current)

    current += 1
    progress(1.0, desc="Complete!")
    logger.info(f"Request processed successfully (question {current}/{MAX_Q})")
    
    # Format response
    response_text = f"### {t('title', ui_lang)}\n\n{result['response']}\n\n**Confidence:** {result['confidence']}"
    logger.info(f"Returning response with length: {len(response_text)}")
    
    return (gr.update(value=response_text), current)

with gr.Blocks(title="Expat Legal Aid Advisor - Multi-Agent AI") as demo:
    gr.Markdown('# 🤖 Expat Legal Aid Advisor')
    gr.Markdown('**Multi-Agent AI System** for legal advisory assistance. Upload documents and ask questions in multiple languages.')
    gr.Markdown('⚖️ *Note: This is an AI assistant, NOT a replacement for professional legal advice.*')
    
    # Usage status banner
    usage_banner = gr.Markdown(
        f"📊 **Service Status:** Available | Daily queries: {usage_stats['daily_queries']}/{DAILY_QUERY_LIMIT}",
        visible=True
    )
    
    consent_group = gr.Group(visible=True)
    with consent_group:
        gr.Markdown('**Privacy Notice**')
        gr.Markdown("Your input may contain sensitive legal information. We do not persist document contents.")
        consent = gr.Checkbox(label='I agree to the privacy notice', value=False)
    main_group = gr.Group(visible=False)
    with main_group:
        # Input section
        gr.Markdown('### 📝 Your Input')
        user_in = gr.Textbox(label='🤔 Your Legal Question', placeholder='Ask in any language (e.g., English, Spanish, French, etc.)', lines=3)
        file_in = gr.File(label='📄 Legal Document (Optional)', file_count='single')

        # Language configuration section
        gr.Markdown("### 🌐 Language Configuration")
        gr.Markdown(
            '**How it works:** The system will translate your document to your chosen communication language, '
            'analyze it, and respond in that language. Auto-detection identifies the document language automatically.'
        )

        # Define all language dropdowns at same scope level (outside Row) to avoid scope issues
        ui_lang = gr.Dropdown(
            choices=sorted(SUPPORTED_LANGUAGES),
            value='en',
            label='🎨 UI Display Language',
            info='Language for interface labels and messages'
        )

        # Create a row for communication and document language dropdowns
        with gr.Row():
            pref_lang = gr.Dropdown(
                choices=sorted(SUPPORTED_LANGUAGES),
                value='en',
                label='💬 Communication Language',
                info='Select the language you want to communicate in and receive responses'
            )
            doc_lang = gr.Dropdown(
                choices=sorted(VALID_DOC_LANGS),
                value='auto',
                label='📋 Document Language',
                info='Choose language or select "auto" to auto-detect'
            )

        # Translation flow info
        gr.Markdown(
            '**🔄 Translation Flow:**\n'
            '1. Document language is detected or you specify it\n'
            '2. Document is translated to your communication language\n'
            '3. System analyzes and reasons over the translated content\n'
            '4. Response is generated in your chosen language'
        )

        gr.Markdown('**✅ Supported Languages:** English, Spanish, French, Dutch, German')

        # Submit section
        gr.Markdown('### ⚡ Process')
        submit = gr.Button('🚀 Submit Question', variant='primary', size='lg')
        
        # Status indicator (will show processing state)
        status = gr.Markdown(value="", visible=True)
        
        out = gr.Markdown()
        counter_state = gr.State(0)

    def toggle(consent_val):
        return gr.update(visible=not consent_val), gr.update(visible=consent_val)
    
    def show_processing():
        """Show immediate feedback when submit is clicked."""
        return gr.update(value="🔄 **Processing your request...** Please wait.", visible=True)
    
    def clear_status():
        """Clear the status message after processing."""
        return gr.update(value="", visible=False)
    
    def update_usage_banner():
        """Update the usage statistics banner."""
        percentage = (usage_stats['daily_queries'] / DAILY_QUERY_LIMIT) * 100
        status_emoji = "✅" if percentage < 80 else "⚠️" if percentage < 100 else "🔴"
        return gr.update(
            value=f"{status_emoji} **Service Status:** Available | Daily queries: {usage_stats['daily_queries']}/{DAILY_QUERY_LIMIT} ({percentage:.0f}%)"
        )
    
    consent.change(toggle, inputs=[consent], outputs=[consent_group, main_group])
    
    # Show processing message immediately on click, then process
    submit.click(
        fn=show_processing,
        inputs=None,
        outputs=[status],
        queue=False  # Run immediately without queuing
    ).then(
        fn=process_input,
        inputs=[user_in, file_in, ui_lang, pref_lang, doc_lang, consent, counter_state],
        outputs=[out, counter_state]
    ).then(
        fn=clear_status,
        inputs=None,
        outputs=[status],
        queue=False
    ).then(
        fn=update_usage_banner,
        inputs=None,
        outputs=[usage_banner],
        queue=False
    )

if __name__ == "__main__":
    import socket
    
    def is_port_in_use(port):
        """Check if a port is already in use."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) == 0
    
    def find_free_port(start_port=7860, max_attempts=10):
        """Find the next available port starting from start_port."""
        for port in range(start_port, start_port + max_attempts):
            if not is_port_in_use(port):
                return port
        return None
    
    # Display startup status
    if API_KEY_CONFIGURED:
        logger.info("✓ Starting Gradio UI with API key configured")
    else:
        logger.warning("⚠ Starting Gradio UI WITHOUT API key - functionality will be limited")
    
    # Find available port
    preferred_port = 7860
    available_port = find_free_port(preferred_port)
    
    if available_port is None:
        logger.error(f"No available ports found in range {preferred_port}-{preferred_port+9}")
        print(f"❌ Error: All ports from {preferred_port} to {preferred_port+9} are in use.")
        print("Please close other applications or wait a moment and try again.")
        exit(1)
    
    if available_port != preferred_port:
        logger.warning(f"Port {preferred_port} is in use, using port {available_port} instead")
        print(f"⚠️  Port {preferred_port} is in use. Starting on port {available_port} instead.")
    
    # Use try-finally to ensure clean shutdown
    try:
        demo.launch(
            server_name="0.0.0.0",  # Required for HF Spaces (use localhost for local dev)
            server_port=available_port,
            share=False,             # Set to True to create public share link
            inbrowser=True,          # Auto-open browser
            prevent_thread_lock=False  # Allow proper cleanup on exit
        )
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
    except Exception as e:
        logger.error(f"Server error: {e}")
    finally:
        logger.info("Gradio server stopped")
