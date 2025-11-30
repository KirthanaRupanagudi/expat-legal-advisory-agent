import gradio as gr
from project.main_agent import run_agent
from project.tools.tools import extract_pdf_text, extract_docx_text
from project.ui.i18n import t
import subprocess
import os
import logging
from pathlib import Path
from typing import Optional, Tuple, List, Any, Dict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

MAX_Q = 15
MAX_Q_LEN = 5000
MAX_DOC_LEN = 1000000
VALID_LANGS = {'auto', 'en', 'es', 'fr', 'nl', 'de'}

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
    if doc_lang not in VALID_LANGS:
        errors.append(f"❌ Invalid document language: {doc_lang}")
    if pref_lang not in {'en', 'es', 'fr', 'nl', 'de'}:
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
        Tuple of (Gradio update object, updated counter)
    """
    logger.info("Starting process_input function")
    progress(0, desc="Initializing...")
    
    current = counter_state or 0
    
    if not consent_given:
        logger.warning("Consent not given")
        return (gr.update(value=f"### {t('title', ui_lang)}\\n\\n{t('welcome', ui_lang)}\\n\\n**{t('disclaimer', ui_lang)}**\\n\\nPlease agree to the privacy notice to proceed."), current)

    if current >= MAX_Q:
        logger.warning(f"Question limit reached: {current}/{MAX_Q}")
        return (gr.update(value=f"### {t('title', ui_lang)}\\n\\nLimit reached: You can ask a maximum of {MAX_Q} questions per session."), current)

    progress(0.1, desc="Validating inputs...")
    doc_content = None
    
    # Document extraction with specific exception handling
    try:
        if legal_document is not None:
            name = legal_document.name.lower()
            logger.info(f"Processing document: {name}")
            progress(0.2, desc="Reading document...")
            
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
            progress(0.3, desc="Document processed")
    except FileNotFoundError as e:
        logger.error(f"File not found: {legal_document.name}")
        return (gr.update(value=f"### {t('title', ui_lang)}\n\n**Error reading document:**\n\n**Error Type:** File not found\n**Message:** {str(e)}\n\nPlease check the file and try again."), current)
    except UnicodeDecodeError as e:
        logger.error(f"Encoding error in document: {legal_document.name}")
        return (gr.update(value=f"### {t('title', ui_lang)}\n\n**Error reading document:**\n\n**Error Type:** Encoding error\n**Message:** The file encoding is not supported. Please ensure the file is in UTF-8 format.\n\nPlease try another file."), current)
    except subprocess.TimeoutExpired:
        logger.error("Document conversion timed out")
        return (gr.update(value=f"### {t('title', ui_lang)}\n\n**Error reading document:**\n\n**Error Type:** Timeout\n**Message:** Document conversion took too long. The file may be too large.\n\nPlease try a smaller file."), current)
    except Exception as e:
        logger.error(f"Error reading document: {type(e).__name__} - {str(e)}", exc_info=True)
        return (gr.update(value=f"### {t('title', ui_lang)}\n\n**Error reading document:**\n\n**Error Type:** {type(e).__name__}\n**Message:** {str(e)}\n\nPlease try another file."), current)

    # Validate all inputs
    progress(0.4, desc="Validating inputs...")
    validation_errors = validate_inputs(user_input, doc_content, doc_lang, pref_lang)
    if validation_errors:
        error_msg = "\n".join(validation_errors)
        logger.warning(f"Input validation error: {error_msg}")
        return (gr.update(value=f"### {t('title', ui_lang)}\n\n**Input Error:**\n\n{error_msg}"), current)

    # Run agent analysis
    try:
        logger.info("Running main agent")
        progress(0.5, desc="Analyzing with AI...")
        result = run_agent(user_input, doc_content, doc_lang, pref_lang)
        logger.info("Main agent finished successfully")
        progress(0.9, desc="Finalizing response...")
    except TimeoutError as e:
        logger.error(f"Agent processing timeout: {str(e)}")
        return (gr.update(value=f"### {t('title', ui_lang)}\n\n**Processing Timeout:**\n\nThe request took too long to process. Please try with a shorter document or simpler question."), current)
    except Exception as e:
        logger.error(f"Processing error from main agent: {str(e)}", exc_info=True)
        return (gr.update(value=f"### {t('title', ui_lang)}\n\n**Processing Error:**\n\n{str(e)}\n\nPlease try again."), current)

    current += 1
    progress(1.0, desc="Complete!")
    logger.info(f"Request processed successfully (question {current}/{MAX_Q})")
    return (gr.update(value=f"### {t('title', ui_lang)}\n\n{result['response']}\n\n**Confidence:** {result['confidence']}"), current)

with gr.Blocks() as demo:
    gr.Markdown('# Expat Legal Aid Advisor')
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
        file_in = gr.File(label='📄 Legal Document (Optional)', file_count='single') # Removed file_types constraint

        # Language configuration section
        gr.Markdown("### 🌐 Language Configuration")
        gr.Markdown(
            '**How it works:** The system will translate your document to your chosen communication language, \n'  # Corrected line
            'analyze it, and respond in that language. Auto-detection identifies the document language automatically.'
        )

        # FIX #2: Define all language dropdowns at same scope level (outside Row) to avoid scope issues
        ui_lang = gr.Dropdown(
            choices=['en', 'es', 'fr', 'nl', 'de'],
            value='en',
            label='🎨 UI Display Language',
            info='Language for interface labels and messages'
        )

        # Create a row for communication and document language dropdowns
        with gr.Row():
            pref_lang = gr.Dropdown(
                choices=['en', 'es', 'fr', 'nl', 'de'],
                value='en',
                label='💬 Communication Language',
                info='Select the language you want to communicate in and receive responses'
            )
            doc_lang = gr.Dropdown(
                choices=['auto', 'en', 'es', 'fr', 'nl', 'de'],
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
        submit = gr.Button('Submit', variant='primary')
        out = gr.Markdown()
        counter_state = gr.State(0)

    def toggle(consent_val):
        return gr.update(visible=not consent_val), gr.update(visible=consent_val)
    consent.change(toggle, inputs=[consent], outputs=[consent_group, main_group])
    submit.click(fn=process_input, inputs=[user_in, file_in, ui_lang, pref_lang, doc_lang, consent, counter_state], outputs=[out, counter_state])

demo.launch(debug=True)
