import gradio as gr
from project.main_agent import run_agent
from project.tools.tools import extract_pdf_text, extract_docx_text
from project.ui.i18n import t
import subprocess, os

MAX_Q = 15
MAX_Q_LEN = 5000
MAX_DOC_LEN = 1000000
VALID_LANGS = {'auto', 'en', 'es', 'fr', 'nl', 'de'}

def read_doc_file(doc_path):
    """Convert .doc to .txt using LibreOffice headless conversion."""
    try:
        txt_path = doc_path.replace('.doc', '.txt')
        subprocess.run(['soffice', '--headless', '--convert-to', 'txt', '--outdir', os.path.dirname(doc_path), doc_path], check=True, timeout=30, capture_output=True)
        with open(txt_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        raise RuntimeError("❌ LibreOffice not installed. Please install it or upload a .docx/.pdf file instead.")
    except subprocess.TimeoutExpired:
        raise RuntimeError("❌ .doc conversion timed out. Document may be too large.")
    except Exception as e:
        raise RuntimeError(f"❌ Failed to convert .doc file: {str(e)}")

def validate_inputs(user_input, doc_content, doc_lang, pref_lang):
    """Validate user inputs before processing."""
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

def process_input(user_input, legal_document, ui_lang, pref_lang, doc_lang, consent_given, counter_state):
    print("--- Starting process_input function ---")
    if not consent_given:
        print("--- Consent not given ---")
        return (gr.update(value=f"### {t('title', ui_lang)}\n\n{t('welcome', ui_lang)}\n\n**{t('disclaimer', ui_lang)}**\n\nPlease agree to the privacy notice to proceed."), counter_state)

    current = counter_state or 0
    if current >= MAX_Q:
        print("--- Question limit reached ---")
        return (gr.update(value=f"### {t('title', ui_lang)}\n\nLimit reached: You can ask a maximum of {MAX_Q} questions per session."), current)

    doc_content = None
    try:
        if legal_document is not None:
            name = legal_document.name.lower()
            print(f"--- Processing document: {name} ---")
            if name.endswith('.pdf'):
                doc_content = extract_pdf_text(legal_document.name)
            elif name.endswith('.docx'):
                doc_content = extract_docx_text(legal_document.name)
            elif name.endswith('.doc'):
                doc_content = read_doc_file(legal_document.name)
            else:
                with open(legal_document.name, 'r', encoding='utf-8') as f:
                    doc_content = f.read()
            print(f"--- Document processed, content length: {len(doc_content) if doc_content else 0} ---")
    except Exception as e:
        print(f"--- Error reading document: {type(e).__name__} - {str(e)} ---")
        return (gr.update(value=f"### {t('title', ui_lang)}\n\n**Error reading document:**\n\n**Error Type:** {type(e).__name__}\n**Message:** {str(e)}\n\nPlease try another file."), current)

    # Validate all inputs
    validation_errors = validate_inputs(user_input, doc_content, doc_lang, pref_lang)
    if validation_errors:
        error_msg = "\n".join(validation_errors)
        print(f"--- Input validation error: {error_msg} ---")
        return (gr.update(value=f"### {t('title', ui_lang)}\n\n**Input Error:**\n\n{error_msg}"), current)

    try:
        print("--- Running main agent ---")
        result = run_agent(user_input, doc_content, doc_lang, pref_lang)
        print("--- Main agent finished ---")
    except Exception as e:
        print(f"--- Processing Error from main agent: {str(e)} ---")
        return (gr.update(value=f"### {t('title', ui_lang)}\n\n**Processing Error:**\n\n{str(e)}\n\nPlease try again."), current)

    current += 1
    print("--- Returning result from process_input ---")
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
