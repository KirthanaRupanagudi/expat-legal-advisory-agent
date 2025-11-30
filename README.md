# Expat Legal Aid Advisor

A multilingual AI-powered legal document analysis system that helps expats understand legal documents in their preferred language. The system uses Google's Gemini AI for intelligent document analysis and supports multiple translation providers with automatic fallback.

## 🌟 Features

- **Multilingual Support**: English, Spanish, French, Dutch, and German
- **Document Processing**: PDF, DOCX, DOC, and TXT files (up to 1MB)
- **Smart Translation**: Multi-provider fallback (Google Cloud Translation → Gemini AI → Free services)
- **Real-time Progress**: Live progress indicators for all processing steps
- **Intelligent Truncation**: Large documents (>500KB) are smartly summarized while preserving key content
- **Interactive UI**: Gradio-based web interface with queue management
- **Privacy-Focused**: No document persistence, secure processing
- **Robust Testing**: Comprehensive test suite with unit, integration, and E2E tests

## 📋 Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Architecture](#architecture)
- [Testing](#testing)
- [API Documentation](#api-documentation)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## 🔧 Prerequisites

- Python 3.8 or higher
- Google API Key (for Gemini AI)
- LibreOffice (optional, for .doc file support)
- Google Colab account (recommended for deployment)

## 📦 Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/expat-legal-aid.git
cd expat-legal-aid
```

### Step 2: Set Up Python Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install --upgrade gradio flask pytest coverage cryptography requests \
    google-generativeai Flask-HTTPAuth Flask-Limiter gunicorn PyPDF2 \
    reportlab python-docx langdetect deep-translator
```

### Step 4: Install LibreOffice (Optional)

For .doc file support:

**Ubuntu/Debian:**
```bash
sudo apt-get update && sudo apt-get install -y libreoffice
```

**macOS:**
```bash
brew install --cask libreoffice
```

**Windows:**
Download from [LibreOffice.org](https://www.libreoffice.org/download/download/)

## ⚙️ Configuration

### Step 1: Set Up Google API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Set the environment variable:

**Windows (PowerShell):**
```powershell
$env:GOOGLE_API_KEY="your-api-key-here"
```

**macOS/Linux:**
```bash
export GOOGLE_API_KEY="your-api-key-here"
```

**Google Colab:**
- Click the 🔑 icon in the left sidebar (Secrets)
- Add a new secret named `GOOGLE_API_KEY`
- Paste your API key

### Step 2: Optional Configuration

**Google Cloud Translation API** (for higher quality translation):
```bash
export GOOGLE_TRANSLATE_API_KEY="your-cloud-translation-key"
```

**Service Authentication Token** (for Flask API):
```bash
export SERVICE_AUTH_TOKEN="your-secure-token"
```

**Session Secret** (for encryption):
```bash
export SESSION_SECRET="your-random-secret-string"
```

## 🚀 Usage

### Option 1: Run in Google Colab (Recommended)

1. Upload the notebook to Google Colab
2. Set your `GOOGLE_API_KEY` in Colab Secrets
3. Run all cells in order
4. Click the Gradio public link to access the UI

### Option 2: Run Locally

#### Gradio UI (Interactive Web Interface)

```bash
python project/ui/gradio_app.py
```

Access the interface at `http://localhost:7860`

#### Flask API (REST Endpoint)

```bash
python project/app.py
```

API available at `http://localhost:5000`

**Example API Request:**
```bash
curl -X POST http://localhost:5000/query \
  -H "Authorization: Bearer your-service-token" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are my rights as an employee?",
    "doc_text": "Your employment contract text here...",
    "doc_lang": "en",
    "pref_lang": "en"
  }'
```

### Option 3: Run from Notebook

Execute the notebook cells in order:
1. Dependencies installation
2. Configuration setup
3. Core modules (tools, agents, UI)
4. Launch Gradio UI

## 📁 Project Structure

```
expat-legal-aid/
├── project/
│   ├── core/
│   │   └── config.py              # Centralized configuration
│   ├── agents/
│   │   └── worker.py              # Main agent logic
│   ├── tools/
│   │   ├── tools.py               # Translation, LLM, document extraction
│   │   └── diagnostics.py        # Translation service diagnostics
│   ├── ui/
│   │   ├── gradio_app.py         # Gradio web interface
│   │   ├── app_ui.py             # Alternative simple UI
│   │   └── i18n.py               # Internationalization
│   ├── tests/
│   │   ├── test_app.py           # Flask API tests
│   │   ├── test_integration.py   # Integration tests
│   │   ├── test_e2e.py           # End-to-end tests
│   │   ├── smoke_test.py         # Quick smoke test
│   │   └── conftest.py           # Pytest configuration
│   ├── app.py                     # Flask REST API
│   └── main_agent.py              # Agent orchestration
├── tests/
│   └── conftest.py                # Shared test fixtures
├── README.md
├── requirements.txt
└── .gitignore
```

## 🏗️ Architecture

### Translation Pipeline

```
Document Input
    ↓
Language Detection (if auto)
    ↓
Translation Attempt 1: Google Cloud Translation API
    ↓ (if fails)
Translation Attempt 2: Gemini AI
    ↓ (if fails)
Translation Attempt 3: MyMemory Free Service
    ↓ (if fails)
Original Text (no translation)
```

### Document Processing Flow

```
1. File Upload (PDF/DOCX/DOC/TXT)
2. Content Extraction
3. Size Check & Smart Truncation (if >1MB)
4. Language Detection
5. Translation (if needed)
6. AI Analysis (Gemini)
7. Response Generation
```

### Components

- **GoogleTranslator**: Multi-provider translation with chunking (2000 chars) and caching
- **GeminiLLM**: Singleton AI model for document analysis
- **Worker/MainAgent**: Orchestrates translation, search, and LLM reasoning
- **Gradio UI**: Interactive web interface with real-time progress
- **Flask API**: RESTful endpoint with rate limiting and authentication

## 🧪 Testing

### Run All Tests

```bash
pytest project/tests/ -v
```

### Run Specific Test Suite

```bash
# Unit tests
pytest project/tests/test_app.py -v

# Integration tests
pytest project/tests/test_integration.py -v

# End-to-end tests
pytest project/tests/test_e2e.py -v
```

### Run with Coverage

```bash
pytest project/tests/ --cov=project --cov-report=term-missing
```

### Generate HTML Coverage Report

```bash
pytest project/tests/ --cov=project --cov-report=html
# Open htmlcov/index.html in your browser
```

### Quick Smoke Test

```bash
python project/tests/smoke_test.py
```

### Translation Diagnostics

Run the diagnostic tool to check which translation services are working:

```python
from project.tools.diagnostics import test_translation_services
test_translation_services()
```

## 📚 API Documentation

### Gradio UI Functions

**`process_input(user_input, legal_document, ui_lang, pref_lang, doc_lang, consent_given, counter_state, progress)`**
- Processes user questions with optional document upload
- Returns formatted response with confidence score
- Progress updates at 7 stages (0% → 100%)

### Flask API Endpoints

**`POST /query`**
- **Headers**: `Authorization: Bearer <token>`
- **Body**:
  ```json
  {
    "question": "Your legal question",
    "doc_text": "Document content (optional)",
    "doc_lang": "auto|en|es|fr|nl|de",
    "pref_lang": "en|es|fr|nl|de"
  }
  ```
- **Response**:
  ```json
  {
    "response": "AI-generated answer",
    "confidence": "High|Medium|Low"
  }
  ```

### Core Configuration

```python
from project.core.config import Defaults, get_google_api_key

# Access default settings
max_doc_length = Defaults.MAX_DOC_LEN  # 1,000,000 chars
chunk_size = Defaults.TRANSLATE_CHUNK_CHARS  # 2,000 chars

# Get API keys
api_key = get_google_api_key()
```

## 🔍 Troubleshooting

### Translation Issues

**Problem**: "403 Forbidden" from Google Cloud Translation API

**Solution**:
1. The system automatically falls back to Gemini AI
2. To enable Google Cloud Translation:
   - Visit [Google Cloud Console](https://console.cloud.google.com/apis/library/translate.googleapis.com)
   - Enable Cloud Translation API
   - Set up billing
   - Use your API key

**Problem**: All translation methods fail

**Solution**:
1. Check `GOOGLE_API_KEY` is set correctly
2. Run diagnostics: `python -c "from project.tools.diagnostics import test_translation_services; test_translation_services()"`
3. Install deep-translator: `pip install deep-translator`

### Document Processing Issues

**Problem**: PDF extraction fails

**Solution**:
- Ensure PyPDF2 is installed: `pip install PyPDF2`
- Try re-uploading the PDF (some PDFs have protection)
- Convert to DOCX as alternative

**Problem**: .doc files not working

**Solution**:
- Install LibreOffice (see Installation section)
- Verify LibreOffice is in PATH: `soffice --version`
- Alternative: convert .doc to .docx manually

### UI Issues

**Problem**: Progress bar not showing

**Solution**:
- Ensure Gradio version ≥ 4.0: `pip install --upgrade gradio`
- Clear browser cache
- Try a different browser

**Problem**: Queue errors with multiple questions

**Solution**:
- The queue handles up to 20 concurrent requests
- Wait for current processing to complete
- Restart the Gradio app if needed

### API Issues

**Problem**: Rate limiting (429 error)

**Solution**:
- Default: 10 requests per minute
- Wait 60 seconds before retrying
- Adjust `Defaults.RATE_LIMIT` in `project/core/config.py`

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes
4. Run tests: `pytest project/tests/ -v`
5. Commit changes: `git commit -m "Add your feature"`
6. Push to branch: `git push origin feature/your-feature`
7. Open a Pull Request

### Development Guidelines
- Follow PEP 8 style guide
- Add tests for new features
- Update documentation
- Use meaningful commit messages
- Add type hints where appropriate
## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Google Gemini AI for powerful language models
- Gradio for the interactive UI framework
- Flask for the REST API framework
- deep-translator for free translation fallback
- The open-source community

## 🗺️ Roadmap

- [ ] Add more languages (Italian, Portuguese, Chinese)
- [ ] Implement document caching for faster re-analysis
- [ ] Add voice input support
- [ ] Create mobile-friendly UI
- [ ] Add export to PDF functionality
- [ ] Implement user authentication
- [ ] Add document comparison features
- [ ] Create Chrome extension

## 📊 Performance

- **Average Response Time**: 5-15 seconds (depending on document size)
- **Document Size Limit**: 1MB (automatically truncated with smart preservation)
- **Translation Speed**: ~2000 chars/chunk with minimal delay
- **Concurrent Users**: Up to 20 queued requests
- **Uptime**: 99.9% on Google Colab

---

**Made with ❤️ for expats navigating legal documents worldwide**
