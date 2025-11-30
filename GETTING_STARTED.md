# Getting Started Guide - Expat Legal Advisory Agent

This guide helps you run the agent in **VSCode, Jupyter, Colab, or Kaggle**.

---

## 🚀 Quick Start by Platform

### Option 1: VSCode (Recommended for Development)

**Step 1: Clone & Install**
```bash
git clone https://github.com/KirthanaRupanagudi/expat-legal-advisory-agent.git
cd expatLegalAdvisoryAgent
pip install -r requirements.txt
```

**Step 2: Configure API Key**

Option A - `.env` file (recommended):
```bash
# Copy template
cp .env.template .env

# Edit .env and add your key
GOOGLE_API_KEY=your_actual_key_here
```

Option B - Environment variable:
```bash
# Linux/Mac
export GOOGLE_API_KEY="your_key_here"

# Windows PowerShell
$env:GOOGLE_API_KEY="your_key_here"

# Windows CMD
set GOOGLE_API_KEY=your_key_here
```

**Step 3: Run**

Interactive CLI:
```bash
python run_notebook.py
```

Or open `expat_legal_advisor.ipynb` in VSCode:
1. Install "Jupyter" extension
2. Click "Select Kernel" → Choose Python environment
3. Run cells

**VSCode Debug Options:**
- Press F5 → Select "Python: Interactive Agent"
- Or: Run > Start Debugging

---

### Option 2: Google Colab (Zero Setup)

**Easiest option - no installation needed!**

1. **Open notebook**: [Click here to open in Colab](https://colab.research.google.com/github/KirthanaRupanagudi/expat-legal-advisory-agent/blob/main/expat_legal_advisor.ipynb)

2. **Run setup cells** (first 3 cells)

3. **Enter API key** when prompted:
   ```
   Get it from: https://makersuite.google.com/app/apikey
   ```

4. **Start using**:
   ```python
   ask_agent("What visa do I need for Germany?")
   ```

**Pro tip:** Save API key to Colab secrets:
- Click 🔑 in left sidebar
- Add secret: `GOOGLE_API_KEY`
- Value: your API key
- Auto-loads on future runs!

---

### Option 3: Kaggle Notebooks

1. **Upload notebook**:
   - Go to Kaggle → New Notebook
   - File → Upload → Select `expat_legal_advisor.ipynb`

2. **Add API key to secrets**:
   - Click "Add-ons" → "Secrets"
   - Label: `GOOGLE_API_KEY`
   - Value: your API key

3. **Run all cells**

4. **Use agent**:
   ```python
   ask_agent("What are the requirements for EU Blue Card?")
   ```

---

### Option 4: JupyterLab/Notebook (Local)

```bash
# Install Jupyter
pip install jupyter

# Start server
jupyter notebook

# Open expat_legal_advisor.ipynb
# Run cells sequentially
```

---

## 🔑 Getting Google API Key

**Required for all platforms**

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Click "Create API Key"
3. Copy the key (starts with `AIza...`)
4. Use in setup (see platform-specific steps above)

**Free tier includes:**
- 60 requests/minute
- Perfect for testing and personal use

---

## 💬 Usage Examples

### Example 1: Simple Question

```python
from project.main_agent import run_agent

result = run_agent(
    user_input="What documents do I need for a work visa in France?",
    preferred_language='en'
)

print(result['response'])
```

### Example 2: With Document (PDF/DOCX)

```python
from project.tools.tools import extract_pdf_text

# Extract text from PDF
doc_text = extract_pdf_text('my_visa_document.pdf')

# Ask about it
result = run_agent(
    user_input="Am I eligible based on this document?",
    document_content=doc_text,
    preferred_language='en'
)

print(result['response'])
```

### Example 3: Multi-language

```python
# Ask in Spanish, get response in Spanish
result = run_agent(
    user_input="¿Qué documentos necesito?",
    preferred_language='es'
)
```

### Example 4: Interactive Mode (VSCode)

```bash
python run_notebook.py
```

```
💬 You: What visa do I need for working in Netherlands?
🤖 Agent: For working in the Netherlands, you'll need...

💬 You: load visa_requirements.pdf
✅ Document loaded

💬 You: Am I eligible?
🤖 Agent: Based on the document...

💬 You: lang fr
✅ Response language: French

💬 You: Combien de temps?
🤖 Agent: Le processus prend généralement...
```

---

## 📁 File Upload Methods

### VSCode (run_notebook.py)
```
💬 You: load path/to/document.pdf
```

### Jupyter/Colab
```python
# Option 1: Upload via UI
from google.colab import files  # Colab only
uploaded = files.upload()

# Option 2: Direct path
doc_text = extract_pdf_text('/content/my_document.pdf')
```

### Supported Formats
- ✅ PDF (`.pdf`)
- ✅ DOCX (`.docx`)
- ✅ TXT (`.txt`)

---

## 🌐 Language Support

| Code | Language | Example Question |
|------|----------|------------------|
| `en` | English  | "What visa do I need?" |
| `es` | Spanish  | "¿Qué visa necesito?" |
| `fr` | French   | "Quel visa me faut-il?" |
| `nl` | Dutch    | "Welke visum heb ik nodig?" |
| `de` | German   | "Welches Visum brauche ich?" |

**Auto-detection available:**
```python
run_agent(
    user_input="Question in any language",
    document_language='auto',  # Auto-detect
    preferred_language='en'    # Response language
)
```

---

## 🐛 Troubleshooting

### "GOOGLE_API_KEY not found"

**VSCode:**
```bash
# Create .env file
echo "GOOGLE_API_KEY=your_key" > .env
```

**Colab/Kaggle:**
- Use secrets manager (see platform-specific setup)

### "ModuleNotFoundError: No module named 'project'"

**VSCode:**
```bash
# Make sure you're in project root
cd expatLegalAdvisoryAgent
python run_notebook.py
```

**Jupyter:**
```python
import sys
sys.path.insert(0, '/path/to/expatLegalAdvisoryAgent')
```

### Jupyter kernel not found

```bash
# Install kernel
python -m ipykernel install --user --name=expat-agent

# Select in VSCode: Ctrl+Shift+P → "Jupyter: Select Interpreter"
```

### File upload not working (Colab)

```python
# Use Colab files API
from google.colab import files
uploaded = files.upload()
filename = list(uploaded.keys())[0]
doc_text = extract_pdf_text(filename)
```

### Slow responses

- **Cause:** Large documents or complex questions
- **Solution:** 
  - Split large PDFs into sections
  - Ask more specific questions
  - Use document excerpts instead of full text

---

## ⚡ Performance Tips

1. **Cache documents**: Load once, ask multiple questions
   ```python
   doc = extract_pdf_text('large_doc.pdf')
   
   ask_agent("Question 1?", document_content=doc)
   ask_agent("Question 2?", document_content=doc)  # Reuses doc
   ```

2. **Batch processing**:
   ```python
   questions = ["Q1?", "Q2?", "Q3?"]
   results = [ask_agent(q, document_content=doc) for q in questions]
   ```

3. **Limit document size**: Use relevant excerpts (< 10,000 chars)

---

## 🔒 Privacy & Security

- ✅ Documents **not stored** on servers
- ✅ API calls use HTTPS encryption
- ✅ PII automatically redacted in logs
- ✅ Session data encrypted (if SESSION_SECRET set)
- ⚠️ Google processes text via Gemini API (see [terms](https://ai.google.dev/terms))

---

## 📊 Limits & Costs

### Free Tier (Google AI Studio)
- **Rate limit**: 60 requests/minute
- **Cost**: FREE
- **Best for**: Personal use, testing

### Production Use
- Consider [Google Cloud Vertex AI](https://cloud.google.com/vertex-ai)
- Higher rate limits
- Pay-per-use pricing

---

## 🆘 Getting Help

**Common issues solved:**
- ✅ API key setup
- ✅ File upload problems
- ✅ Platform-specific configurations
- ✅ Performance optimization

**Still stuck?**
- [GitHub Issues](https://github.com/KirthanaRupanagudi/expat-legal-advisory-agent/issues)
- [Discussions](https://github.com/KirthanaRupanagudi/expat-legal-advisory-agent/discussions)

---

## ⚖️ Legal Disclaimer

This tool provides **general legal information only**. 

**Not legal advice** - Consult a qualified immigration attorney for:
- Specific visa applications
- Legal representation
- Official document review
- Immigration appeals

---

## 🎓 Next Steps

- [x] Set up platform (VSCode/Colab/Kaggle)
- [x] Configure API key
- [x] Run first query
- [ ] Upload your own document
- [ ] Try multi-language queries
- [ ] Explore advanced features (batch processing, export)

**Ready to start?** Choose your platform above and follow the setup!
