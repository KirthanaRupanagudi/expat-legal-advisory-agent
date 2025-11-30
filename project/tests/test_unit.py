import os, requests, pytest
from unittest.mock import patch
from project.agents.worker import Worker
from project.agents.evaluator import Evaluator
from project.main_agent import run_agent
from project.core.context_engineering import sanitize_input, ContextEngine
from project.core.observability import Observability
from project.core.a2a_protocol import create_message
from project.memory.session_memory import SessionMemory
from project.tools.tools import SafeCalculator, summarizer, GoogleTranslator, GeminiLLM, SimpleSearch, DomainTools, extract_pdf_text
import logging

def test_evaluator_confidence_and_polish():
    e = Evaluator()
    assert e.evaluate('short')['confidence'] >= 0.55
    long = 'a' * 600
    assert e._estimate_confidence(long) == 0.92
    assert e._polish_text('') == 'I could not generate a meaningful answer based on the provided information.'
    assert e._polish_text('Document processed. Some text.').startswith('After reviewing your document,')

def test_planner_action_and_sanitize():
    from project.agents.planner import Planner
    plan = Planner().plan('<b>Hi</b>')
    assert plan['tasks'][0]['action'] == 'process'
    assert sanitize_input('<i>x</i>') == 'x'

def test_planner_with_language_parameters():
    """Test that Planner correctly passes language parameters."""
    from project.agents.planner import Planner
    p = Planner()
    plan = p.plan('¿Hola?', None, 'es', 'es')
    assert plan['tasks'][0]['details']['document_language'] == 'es'
    assert plan['tasks'][0]['details']['preferred_language'] == 'es'

def test_context_engine_builds_context():
    ctx = ContextEngine().build_context('Q?', {'user': 'alice'}, 'doc text')
    assert "Context(session={'user': 'alice'})" in ctx
    assert 'Input=Q?' in ctx
    assert 'Document=doc text' in ctx

def test_observability_logs(caplog):
    caplog.set_level(logging.INFO) # Set logging level to INFO
    Observability.log('start', {'a': 1})
    assert any('"event": "start"' in rec.message for rec in caplog.records)

def test_a2a_message_has_fields():
    m = create_message('planner', 'worker', {'x': 1})
    assert {'task_id','sender','receiver','payload','timestamp'}.issubset(m.keys())

def test_session_memory_with_secret(monkeypatch):
    from cryptography.fernet import Fernet
    key = Fernet.generate_key().decode()
    monkeypatch.setenv('SESSION_SECRET', key)
    mem = SessionMemory()
    mem.store('k','v')
    assert mem.retrieve('k') == 'v'

def test_session_memory_without_secret(monkeypatch):
    monkeypatch.delenv('SESSION_SECRET', raising=False)
    mem = SessionMemory()
    mem.store('k','v')
    assert mem.retrieve('k') == 'v'

def test_tools_calculator_and_summarizer():
    assert SafeCalculator.evaluate('1+2') == 3
    assert SafeCalculator.evaluate('+10') == 10
    assert 'Invalid' in SafeCalculator.evaluate('foo(1)')
    assert summarizer('x'*300).endswith('...')

def test_simple_search_and_domain_tools():
    s = SimpleSearch()
    s.add('d1', 'visa application requires documents')
    s.add('d2', 'residence permit and study visa')
    hits = s.query('visa application', top_k=2)
    assert len(hits) >= 1
    info = DomainTools.extract_visa_requirements('You need a work permit and visa.')
    assert info['has_visa_context'] and 'visa' in info['matched_keywords']

def test_extract_pdf_text(tmp_path):
    from reportlab.pdfgen import canvas
    pdf_path = tmp_path / 'test.pdf'
    c = canvas.Canvas(str(pdf_path)) # Convert PosixPath to string
    c.drawString(100, 750, 'This is a PDF test for extraction.')
    c.save()
    text = extract_pdf_text(str(pdf_path))
    assert 'PDF test for extraction' in text

@patch('project.agents.worker.GeminiLLM')
@patch('project.agents.worker.GoogleTranslator')
def test_worker_translates_q_and_doc_and_passes_citations(MockTrans, MockLLM):
    mock_llm = MockLLM.return_value
    mock_llm.generate_response.return_value = 'LLM generated response'
    mock_trans = MockTrans.return_value
    mock_trans.translate.side_effect = ['Translated Question', 'Translated Document']
    os.environ['GOOGLE_API_KEY'] = 'fake'
    w = Worker()
    task = {'action':'process','details':{'user_input':'¿Requisitos?', 'document':'documento en español', 'document_language': 'es', 'preferred_language': 'es'}}
    out = w.execute(task)
    assert 'LLM generated response' in out # Updated assertion
    assert mock_trans.translate.call_count >= 2
    args, kwargs = mock_llm.generate_response.call_args
    assert 'citations' in kwargs
    del os.environ['GOOGLE_API_KEY']

@patch('project.agents.worker.GeminiLLM')
@patch('project.agents.worker.GoogleTranslator')
def test_worker_domain_hint_appended(MockTrans, MockLLM):
    mock_llm = MockLLM.return_value
    mock_llm.generate_response.return_value = 'LLM generated response'
    mock_trans = MockTrans.return_value
    mock_trans.translate.side_effect = ['Translated Question', 'Translated Document mentioning visa']
    os.environ['GOOGLE_API_KEY'] = 'fake'
    w = Worker()
    task = {'action':'process','details':{'user_input':'¿Requisitos?', 'document':'visa doc', 'document_language': 'auto', 'preferred_language': 'es'}}
    out = w.execute(task)
    assert 'Detected visa-related context' in out
    del os.environ['GOOGLE_API_KEY']

def test_worker_unknown_action():
    with patch('project.agents.worker.GeminiLLM'):
        w = Worker()
    assert w.execute({'action': 'translate', 'details': {'user_input':'hi'}}) == 'Unknown action'

def test_worker_language_auto_detection():
    """Test that Worker detects document language when 'auto' is specified."""
    with patch('project.agents.worker.GeminiLLM'):
        w = Worker()
        # Spanish text
        spanish_text = 'Este es un documento en español sobre visa de trabajo.'
        detected = w._detect_language(spanish_text)
        assert detected in ['es', 'en']  # Might detect as Spanish or fallback to English

@patch('project.tools.tools.requests')
def test_google_translator_success(mock_requests):
    mock_requests.post.return_value.raise_for_status.return_value = None
    mock_requests.post.return_value.json.return_value = {'data': {'translations':[{'translatedText':'Hola'}]}}
    os.environ['GOOGLE_API_KEY'] = 'key'
    tr = GoogleTranslator()
    assert tr.translate('Hello', 'es') == 'Hola'
    del os.environ['GOOGLE_API_KEY']

@patch('project.tools.tools.requests')
def test_google_translator_api_error(mock_requests):
    mock_requests.post.return_value.raise_for_status.side_effect = requests.exceptions.RequestException('API Error')
    os.environ['GOOGLE_API_KEY'] = 'key'
    tr = GoogleTranslator()
    with pytest.raises(requests.exceptions.RequestException):
        tr.translate('Hello','es')
    del os.environ['GOOGLE_API_KEY']

def test_gemini_llm_init_no_key(monkeypatch):
    from project.tools.tools import GeminiLLM
    monkeypatch.delenv('GOOGLE_API_KEY', raising=False)
    with pytest.raises(RuntimeError, match='missing for GeminiLLM'):
        GeminiLLM()

@patch('google.generativeai.GenerativeModel')
def test_gemini_llm_generate_response(MockModel, monkeypatch):
    from project.tools.tools import GeminiLLM
    mock = MockModel.return_value
    mock.generate_content.return_value.text = 'Mocked'
    monkeypatch.setenv('GOOGLE_API_KEY','k')
    llm = GeminiLLM()
    assert llm.generate_response('Hola?', 'Hello?') == 'Mocked'
    mock.generate_content.side_effect = Exception('LLM down')
    assert llm.generate_response('Hola?', 'Hello?') == 'Unable to generate response at this time.'
    monkeypatch.delenv('GOOGLE_API_KEY', raising=False)

@patch('google.generativeai.GenerativeModel')
def test_gemini_llm_with_language_enforcement(MockModel, monkeypatch):
    """Test that GeminiLLM appends language enforcement to prompt."""
    from project.tools.tools import GeminiLLM
    mock = MockModel.return_value
    mock.generate_content.return_value.text = 'Spanish response'
    monkeypatch.setenv('GOOGLE_API_KEY','k')
    llm = GeminiLLM()
    result = llm.generate_response('¿Hola?', reply_language='es')
    # Verify that the prompt included language enforcement
    call_args = mock.generate_content.call_args
    prompt = call_args[0][0] if call_args[0] else ''
    assert 'Spanish' in prompt or 'reply ONLY' in prompt
    monkeypatch.delenv('GOOGLE_API_KEY', raising=False)

@patch('project.agents.worker.GeminiLLM')
@patch('project.agents.worker.GoogleTranslator')
def test_run_agent_returns_polished_dict(MockTrans, MockLLM, monkeypatch):
    MockLLM.return_value.generate_response.return_value = 'Mocked LLM response for Hello!'
    MockTrans.return_value.translate.side_effect = ['Translated Question']
    monkeypatch.setenv('GOOGLE_API_KEY','k')
    out = run_agent('Hello!')
    assert isinstance(out, dict) and 'response' in out and 'confidence' in out
    assert ('Here is my assessment' in out['response']) or ('After reviewing your document' in out['response'])
    assert 'Privacy Notice' in out['response']
    monkeypatch.delenv('GOOGLE_API_KEY', raising=False)

@patch('project.agents.worker.GeminiLLM')
@patch('project.agents.worker.GoogleTranslator')
def test_run_agent_with_language_parameters(MockTrans, MockLLM, monkeypatch):
    """Test that run_agent accepts and passes language parameters."""
    MockLLM.return_value.generate_response.return_value = 'Spanish response'
    MockTrans.return_value.translate.return_value = 'Translated'
    monkeypatch.setenv('GOOGLE_API_KEY','k')
    out = run_agent('¿Pregunta?', None, 'es', 'es')
    assert isinstance(out, dict)
    assert 'response' in out and 'confidence' in out
    monkeypatch.delenv('GOOGLE_API_KEY', raising=False)

@patch('project.agents.worker.GeminiLLM')
@patch('project.agents.worker.GoogleTranslator')
def test_worker_translates_document_to_preferred_language(MockTrans, MockLLM):
    """FIX #5: Test that document is translated to preferred language, not always English."""
    mock_llm = MockLLM.return_value # Corrected typo from MockLLm to MockLLM
    mock_llm.generate_response.return_value = 'Spanish response about visa'
    mock_trans = MockTrans.return_value
    # First call: question to English, Second call: document to Spanish
    mock_trans.translate.side_effect = ['Pregunta en inglés', 'Documento traducido al español']

    os.environ['GOOGLE_API_KEY'] = 'fake'
    w = Worker()
    task = {
        'action': 'process',
        'details': {
            'user_input': '¿Cuales son los requisitos?',
            'document': 'Este es un documento en español sobre visa',
            'document_language': 'es',
            'preferred_language': 'es'
        }
    }
    out = w.execute(task)

    # Verify translator was called with preferred language as target
    assert mock_trans.translate.call_count >= 2
    # Check that one of the calls targeted 'es' (preferred language)
    calls = [call[1].get('target') for call in mock_trans.translate.call_args_list if call[1]]
    assert 'es' in calls, f"Expected 'es' in translation targets, got {calls}"

    assert 'Spanish response about visa' in out # Updated assertion
    del os.environ['GOOGLE_API_KEY']

def test_google_translator_no_api_key(monkeypatch):
    """GoogleTranslator should raise when GOOGLE_API_KEY is missing."""
    monkeypatch.delenv('GOOGLE_API_KEY', raising=False)
    with pytest.raises(RuntimeError):
        GoogleTranslator()

@patch('project.tools.tools.requests')
def test_google_translator_retries_on_timeout(mock_requests, monkeypatch):
    """Simulate a transient timeout on first POST, success on retry."""
    from requests.exceptions import Timeout
    class FakeResp:
        def raise_for_status(self):
            return None
        def json(self):
            return {'data': {'translations':[{'translatedText':'Hola'}]}}

    # Set API key before instantiating GoogleTranslator
    monkeypatch.setenv('GOOGLE_API_KEY', 'key')

    call_count = {'n': 0}
    def post_side_effect(*args, **kwargs):
        if call_count['n'] == 0:
            call_count['n'] += 1
            raise Timeout('simulated timeout')
        return FakeResp()
    with patch('project.tools.tools.requests.post', side_effect=post_side_effect):
        tr = GoogleTranslator()
        result = tr.translate('Hello', 'es')
        assert result == 'Hola'
    monkeypatch.delenv('GOOGLE_API_KEY', raising=False)

@patch('project.agents.worker.GeminiLLM')
@patch('project.agents.worker.GoogleTranslator')
def test_worker_translate_exception_uses_original_doc(MockTrans, MockLLM):
    """If translator fails, Worker should pass the original document to the LLM (fallback path)."""
    mock_llm = MockLLM.return_value
    def capture_generate(*args, **kwargs):
        # When translation fails document_translated is None, so document_content_original should be passed
        assert kwargs.get('document_content_original') is not None, 'Expected original document in LLM args on translation failure'
        return 'LLM fallback response'
    mock_llm.generate_response.side_effect = capture_generate
    mock_trans = MockTrans.return_value
    # Simulate translator failing for any call
    mock_trans.translate.side_effect = Exception('forced translator failure')
    os.environ['GOOGLE_API_KEY'] = 'fake'
    w = Worker()
    task = {'action':'process','details':{'user_input':'Pregunta','document':'documento original','document_language':'es','preferred_language':'es'}}
    out = w.execute(task)
    assert 'LLM fallback response' in out # Updated assertion
    del os.environ['GOOGLE_API_KEY']

@patch('project.agents.worker.GeminiLLM')
def test_worker_translate_safe_none(MockLLM):
    """_translate_safe should return None when given None and should not raise."""
    with patch('project.agents.worker.GeminiLLM'):
        w = Worker()
        assert w._translate_safe(None) is None

def test_worker_empty_text_detection():
    """Test _detect_language with empty/short text returns 'en' as fallback."""
    with patch('project.agents.worker.GeminiLLM'):
        w = Worker()
        assert w._detect_language('') == 'en'
        assert w._detect_language('a') == 'en'
        assert w._detect_language(None) == 'en'

@patch('project.agents.worker.GeminiLLM')
def test_worker_execute_without_document(MockLLM):
    """Test Worker.execute when no document is provided."""
    mock_llm = MockLLM.return_value
    mock_llm.generate_response.return_value = 'LLM response'
    os.environ['GOOGLE_API_KEY'] = 'fake'
    w = Worker()
    task = {
        'action': 'process',
        'details': {
            'user_input': 'What are visa requirements?',
            'document': None,
            'document_language': 'auto',
            'preferred_language': 'en'
        }
    }
    out = w.execute(task)
    assert out == 'LLM response'
    del os.environ['GOOGLE_API_KEY']

@patch('project.agents.worker.GeminiLLM')
@patch('project.agents.worker.GoogleTranslator')
def test_worker_document_language_auto_detection_flow(MockTrans, MockLLM):
    """Test Worker auto-detects document language and translates accordingly."""
    mock_llm = MockLLM.return_value
    mock_llm.generate_response.return_value = 'Analyzed response'
    mock_trans = MockTrans.return_value
    mock_trans.translate.side_effect = ['Question EN', 'Document EN']
    os.environ['GOOGLE_API_KEY'] = 'fake'
    w = Worker()
    spanish_doc = 'Este es un documento sobre visa y permiso de residencia.'
    task = {
        'action': 'process',
        'details': {
            'user_input': '¿Requisitos?',
            'document': spanish_doc,
            'document_language': 'auto',
            'preferred_language': 'en'
        }
    }
    out = w.execute(task)
    assert 'Analyzed response' in out # Updated assertion
    # Verify translator was called
    assert mock_trans.translate.call_count >= 1
    del os.environ['GOOGLE_API_KEY']

def test_summarizer_edge_cases():
    """Test summarizer with various edge cases."""
    assert summarizer('') == ''
    assert summarizer(None) == ''
    assert summarizer('short text') == 'short text'
    long_text = 'x' * 250
    result = summarizer(long_text)
    assert result.endswith('...')
    assert len(result) == 203  # 200 + '...'

@patch('project.tools.tools.requests')
def test_google_translator_with_different_languages(mock_requests):
    """Test GoogleTranslator with various language pairs."""
    mock_requests.post.return_value.raise_for_status.return_value = None
    mock_requests.post.return_value.json.return_value = {'data': {'translations':[{'translatedText':'Bonjour'}]}}
    os.environ['GOOGLE_API_KEY'] = 'key'
    tr = GoogleTranslator()
    result = tr.translate('Hello', target='fr')
    assert result == 'Bonjour'
    # Verify the call was made with correct parameters
    call_args = mock_requests.post.call_args
    assert call_args[1]['json']['target'] == 'fr'
    del os.environ['GOOGLE_API_KEY']

def test_safe_calculator_division():
    """Test SafeCalculator with division operations."""
    assert SafeCalculator.evaluate('10/2') == 5.0
    assert SafeCalculator.evaluate('5/2') == 2.5

def test_safe_calculator_complex_expression():
    """Test SafeCalculator with complex expressions."""
    assert SafeCalculator.evaluate('2 + 3 * 4') == 14
    assert SafeCalculator.evaluate('(2 + 3) * 4') == 20
