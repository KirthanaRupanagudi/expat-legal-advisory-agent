import os
from unittest.mock import patch
from project.main_agent import run_agent

# Ensure the directory exists before writing the file
os.makedirs('project/tests', exist_ok=True)

file_content = """\
import os
from unittest.mock import patch
from project.main_agent import run_agent
os.environ['E2E_TEST_MODE'] = 'true'
USE_MOCK_FOR_FALLBACK_SMOKE = True
if USE_MOCK_FOR_FALLBACK_SMOKE:
    with patch('project.tools.tools.GeminiLLM') as MockGeminiLLM:
        mock = MockGeminiLLM.return_value
        mock.generate_response.return_value = 'Mocked response: Pipeline OK.'
        res = run_agent('¿Cuáles son los requisitos de visa?', 'Este documento menciona visa y permiso.', 'es', 'es')
        print('Response:', res['response'][:200])
        print('Confidence:', res['confidence'])
else:
    res = run_agent('What are visa requirements?', 'This document mentions visa and permit.', 'en', 'en')
    print('Response:', res['response'][:200])
    print('Confidence:', res['confidence'])
print('✅ Agent smoke test executed.')
"""

with open('project/tests/smoke_test.py', 'w', encoding='utf-8') as f:
    f.write(file_content)

print('Writing project/tests/smoke_test.py')
import os
from reportlab.pdfgen import canvas
from project.tools.tools import extract_pdf_text

# Ensure the directory exists
os.makedirs('project/tests', exist_ok=True)

file_content = """\
from reportlab.pdfgen import canvas
from project.tools.tools import extract_pdf_text
pdf_path = 'smoke_test.pdf'
c = canvas.Canvas(pdf_path)
c.drawString(100, 750, 'This is a smoke test PDF with visa and permit text.')
c.save()
parsed_text = extract_pdf_text(pdf_path)
print('Parsed PDF contains:', 'visa' in parsed_text and 'permit' in parsed_text)
print('Parsed snippet:', parsed_text[:120])
"""

with open('project/tests/smoke_test.py', 'a', encoding='utf-8') as f:
    f.write(file_content)

print('Appending to project/tests/smoke_test.py for PDF parsing check.')
from docx import Document
from project.tools.tools import extract_docx_text

path = 'smoke_test.docx'
doc = Document()
doc.add_paragraph('This is a smoke test DOCX with residence permit text.')
doc.save(path)
parsed_docx = extract_docx_text(path)
print('Parsed DOCX contains:', 'residence permit' in parsed_docx)
print('Parsed snippet:', parsed_docx[:120])
from unittest.mock import patch
from project.main_agent import run_agent

# Force translator failure
with patch('project.tools.tools.GoogleTranslator.translate', side_effect=Exception('Forced failure')):
    res = run_agent('Pregunta en español sobre residencia', 'Documento original en español con detalles de visa y permiso de trabajo.')
    print('Response (fallback path):', res['response'][:200])
    print('Confidence:', res['confidence'])
print('✅ Fallback smoke test executed.')
import os
from unittest.mock import patch
from project.main_agent import run_agent

# Ensure the directory exists
os.makedirs('project/tests', exist_ok=True)

file_content = """\
from unittest.mock import patch
from project.main_agent import run_agent

# Force translator failure
with patch('project.tools.tools.GoogleTranslator.translate', side_effect=Exception('Forced failure')):
    res = run_agent('Pregunta en español sobre residencia', 'Documento original en español con detalles de visa y permiso de trabajo.')
    print('Response (fallback path):', res['response'][:200])
    print('Confidence:', res['confidence'])
print('✅ Fallback smoke test executed.')
"""

with open('project/tests/smoke_test.py', 'a', encoding='utf-8') as f:
    f.write(file_content)

print('Appending to project/tests/smoke_test.py for Translation Fallback check.')
from reportlab.pdfgen import canvas
from project.tools.tools import extract_pdf_text
pdf_path = 'smoke_test.pdf'
c = canvas.Canvas(str(pdf_path)) # Convert PosixPath to string
c.drawString(100, 750, 'This is a smoke test PDF with visa and permit text.')
c.save()
parsed_text = extract_pdf_text(pdf_path)
print('Parsed PDF contains:', 'visa' in parsed_text and 'permit' in parsed_text)
print('Parsed snippet:', parsed_text[:120])

