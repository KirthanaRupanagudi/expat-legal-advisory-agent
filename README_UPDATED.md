# 🌍 Expat Legal Advisory Agent

Multi-language legal document assistant for expats. Provides legal guidance in English, Spanish, French, Dutch, and German.

## ✨ Features

- 🌐 **Multi-language Support**: Ask questions and receive answers in 5 languages
- 📄 **Document Analysis**: Upload PDF/DOCX legal documents for analysis
- 🤖 **AI-Powered**: Uses Google Gemini for intelligent responses
- 🔒 **Privacy-Focused**: Documents not persisted, PII redacted in logs
- 💻 **Multi-Platform**: Works in VSCode, Jupyter, Colab, Kaggle

## 🚀 Quick Start

### Option 1: VSCode (Interactive Python)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set API key
export GOOGLE_API_KEY="your_key_here"  # Linux/Mac
set GOOGLE_API_KEY=your_key_here       # Windows CMD
$env:GOOGLE_API_KEY="your_key_here"    # Windows PowerShell

# 3. Run interactive mode
python run_notebook.py
```

### Option 2: Jupyter Notebook (VSCode/Local)

```bash
# 1. Install Jupyter
pip install jupyter

# 2. Open notebook
jupyter notebook expat_legal_advisor.ipynb
```

### Option 3: Google Colab

1. Open [expat_legal_advisor.ipynb](https://colab.research.google.com/github/KirthanaRupanagudi/expat-legal-advisory-agent/blob/main/expat_legal_advisor.ipynb)
2. Run setup cells
3. Enter API key when prompted
4. Start asking questions!

### Option 4: Kaggle Notebooks

1. Upload `expat_legal_advisor.ipynb` to Kaggle
2. Add secrets: `GOOGLE_API_KEY`
3. Run all cells

## 📋 Requirements

### API Keys

**Required:**
- Google API Key (for Gemini LLM and Translate)
  - Get it: [Google AI Studio](https://makersuite.google.com/app/apikey)

**Optional:**
- Flask API Key (auto-generated for notebook mode)

### Dependencies

```bash
pip install -r requirements.txt
```

Core packages:
- `google-generativeai` - Gemini LLM
- `PyPDF2` - PDF text extraction
- `python-docx` - DOCX text extraction
- `langdetect` - Language detection
- `flask` - REST API (optional)
- `cryptography` - Session encryption

## 💡 Usage Examples

### VSCode Interactive Mode

```bash
python run_notebook.py
```

```
💬 You: What visa do I need for working in Germany?
🤖 Agent: To work in Germany, you typically need...

💬 You: load documents/visa_requirements.pdf
✅ Document loaded: visa_requirements.pdf

💬 You: Am I eligible based on this document?
🤖 Agent: Based on the document provided...

💬 You: lang es
✅ Response language: Spanish

💬 You: ¿Cuánto tiempo tarda?
🤖 Agent: El proceso generalmente tarda...
```

### Jupyter/Colab

```python
from project.main_agent import run_agent

# Simple question
result = run_agent(
    user_input="What are German work visa requirements?",
    preferred_language='en'
)
print(result['response'])

# With document
result = run_agent(
    user_input="Am I eligible?",
    document_content=open('visa_doc.txt').read(),
    document_language='auto',
    preferred_language='en'
)
```

### REST API (Optional)

```bash
# Start Flask server
python -m project.app

# Query endpoint
curl -X POST http://localhost:5000/query \
  -H "X-API-Key: your_flask_key" \
  -H "Content-Type: application/json" \
  -d '{
    "input": "What visa do I need?",
    "document_content": "...",
    "preferred_language": "en"
  }'
```

## 🌐 Supported Languages

| Code | Language | Supported |
|------|----------|-----------|
| `en` | English  | ✅ |
| `es` | Spanish  | ✅ |
| `fr` | French   | ✅ |
| `nl` | Dutch    | ✅ |
| `de` | German   | ✅ |

Auto-detection available with `document_language='auto'`

## 📁 Project Structure

```
expatLegalAdvisoryAgent/
├── expat_legal_advisor.ipynb  # Jupyter notebook (all platforms)
├── run_notebook.py            # VSCode CLI launcher
├── requirements.txt           # Python dependencies
├── project/
│   ├── agents/               # Agent orchestration
│   │   ├── planner.py       # Task planning
│   │   ├── worker.py        # Document processing
│   │   └── evaluator.py     # Response evaluation
│   ├── core/                # Core utilities
│   │   ├── a2a_protocol.py  # Agent-to-agent messaging
│   │   ├── context_engineering.py
│   │   └── observability.py # Logging
│   ├── memory/              # Session management
│   │   └── session_memory.py
│   ├── tools/               # External tools
│   │   └── tools.py         # LLM, translator, extractors
│   ├── ui/                  # Internationalization
│   │   └── i18n.py
│   └── tests/               # Test suite (119 tests)
└── README.md
```

## 🔧 Configuration

### Environment Variables

```bash
# Required
GOOGLE_API_KEY=your_google_api_key

# Optional
FLASK_API_KEY=your_flask_key
SESSION_SECRET=your_encryption_key
```

### VSCode Settings (`.env` file)

Create `.env` in project root:

```env
GOOGLE_API_KEY=AIza...your_key
FLASK_API_KEY=your_flask_key_12345
```

### Colab Secrets

Use Colab's built-in secret manager:
1. Click 🔑 in left sidebar
2. Add secret: `GOOGLE_API_KEY`
3. Notebook auto-loads it

## 🧪 Testing

```bash
# Run all tests
pytest project/tests/

# With coverage
pytest --cov=project --cov-report=html

# Security tests only
pytest -m security

# Performance tests only
pytest -m performance
```

**Test Coverage:** 73% (119 tests passing)

## 🛠️ Development

### Code Quality

- ✅ Type hints on all new code
- ✅ Comprehensive error handling
- ✅ Platform-agnostic (Windows/Linux/Mac)
- ✅ PEP 8 compliant
- ✅ Security tested (SQL injection, XSS, etc.)

### Recent Improvements

- Fixed deprecated Python 3.14 functions
- Added robust error handling for file operations
- Improved translation logic efficiency
- Added source language hints for better accuracy
- Created cross-platform notebook interface

## 📊 Performance

- **Response Time:** < 5s for simple queries
- **Document Processing:** 1000 pages/min (PDF)
- **Concurrent Requests:** Handles 10+ simultaneous
- **API Calls:** Optimized to minimize translation costs

## 🐛 Troubleshooting

### "ModuleNotFoundError: No module named 'project'"

```bash
# Make sure you're in project root
cd expatLegalAdvisoryAgent

# Or set PYTHONPATH
export PYTHONPATH="$PWD:$PYTHONPATH"  # Linux/Mac
set PYTHONPATH=%CD%;%PYTHONPATH%      # Windows
```

### "RuntimeError: GOOGLE_API_KEY missing"

```bash
# Check if set
echo $GOOGLE_API_KEY  # Linux/Mac
echo %GOOGLE_API_KEY% # Windows

# Set it
export GOOGLE_API_KEY="your_key"  # Linux/Mac
set GOOGLE_API_KEY=your_key       # Windows
```

### VSCode Jupyter not detecting notebook

1. Install Jupyter extension
2. Open Command Palette (Ctrl+Shift+P)
3. Select "Jupyter: Select Interpreter"
4. Choose your Python environment

### Colab "git clone" fails

Network issue - try:
```python
!git clone https://github.com/KirthanaRupanagudi/expat-legal-advisory-agent.git
```

## 📄 License

See [LICENSE.txt](LICENSE.txt)

## 🤝 Contributing

Contributions welcome! Please:
1. Fork repository
2. Create feature branch
3. Add tests
4. Submit pull request

## ⚖️ Disclaimer

This tool provides general legal information only. **Not a substitute for professional legal advice.** For specific legal matters, consult a qualified immigration attorney.

## 📞 Support

- **Issues:** [GitHub Issues](https://github.com/KirthanaRupanagudi/expat-legal-advisory-agent/issues)
- **Discussions:** [GitHub Discussions](https://github.com/KirthanaRupanagudi/expat-legal-advisory-agent/discussions)

---

**Made with ❤️ for expats worldwide**
