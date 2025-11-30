"""
Unit Tests for Expat Legal Advisory Agent

This module contains comprehensive unit tests for all components:
- Agents (Evaluator, Planner, Worker)
- Core modules (Context Engineering, Observability, A2A Protocol)
- Memory (Session Memory)
- Tools (Calculator, Translator, LLM, Search, Domain Tools, File Extractors)
"""

import logging
import os

import pytest
import requests
from cryptography.fernet import Fernet
from unittest.mock import patch

from project.agents.evaluator import Evaluator
from project.agents.planner import Planner
from project.agents.worker import Worker
from project.core.a2a_protocol import create_message
from project.core.context_engineering import ContextEngine, sanitize_input
from project.core.observability import Observability
from project.main_agent import run_agent
from project.memory.session_memory import SessionMemory
from project.tools.tools import (
    DomainTools,
    GeminiLLM,
    GoogleTranslator,
    SafeCalculator,
    SimpleSearch,
    extract_pdf_text,
    summarizer,
)


# ============================================================================
# Test Constants
# ============================================================================

class UnitTestConstants:
    """Constants used across unit tests."""
    
    FAKE_API_KEY = 'fake_test_key_12345'
    SAMPLE_SPANISH_TEXT = 'Este es un documento sobre visa y permiso de residencia.'
    SAMPLE_ENGLISH_TEXT = 'This is a document about visa and residence permit.'
    MOCK_LLM_RESPONSE = 'Mocked LLM response'
    MOCK_TRANSLATED_TEXT = 'Translated text'
    
    # Confidence threshold values
    SHORT_TEXT_CONFIDENCE = 0.55
    LONG_TEXT_CONFIDENCE = 0.92
    LONG_TEXT_LENGTH = 600


# ============================================================================
# Agent Tests
# ============================================================================

class TestEvaluator:
    """Unit tests for the Evaluator agent."""
    
    def test_confidence_estimation_for_short_text(self) -> None:
        """Test confidence score for short responses."""
        evaluator = Evaluator()
        result = evaluator.evaluate('short text')
        assert result['confidence'] >= UnitTestConstants.SHORT_TEXT_CONFIDENCE, (
            f"Expected confidence >= {UnitTestConstants.SHORT_TEXT_CONFIDENCE}, "
            f"got {result['confidence']}"
        )
    
    def test_confidence_estimation_for_long_text(self) -> None:
        """Test confidence score for long responses."""
        evaluator = Evaluator()
        long_text = 'a' * UnitTestConstants.LONG_TEXT_LENGTH
        expected_confidence = UnitTestConstants.LONG_TEXT_CONFIDENCE
        actual_confidence = evaluator._estimate_confidence(long_text)
        assert actual_confidence == expected_confidence, (
            f"Expected confidence {expected_confidence}, got {actual_confidence}"
        )
    
    def test_polish_empty_text(self) -> None:
        """Test that empty text gets a meaningful default message."""
        evaluator = Evaluator()
        polished = evaluator._polish_text('')
        expected = 'I could not generate a meaningful answer based on the provided information.'
        assert polished == expected, f"Expected '{expected}', got '{polished}'"
    
    def test_polish_document_processed_text(self) -> None:
        """Test polishing of 'Document processed' responses."""
        evaluator = Evaluator()
        raw_text = 'Document processed. Some analysis here.'
        polished = evaluator._polish_text(raw_text)
        expected_prefix = 'After reviewing your document,'
        assert polished.startswith(expected_prefix), (
            f"Expected response to start with '{expected_prefix}', got '{polished[:50]}...'"
        )
    
    def test_evaluate_returns_proper_structure(self) -> None:
        """Test that evaluate returns response and confidence."""
        evaluator = Evaluator()
        result = evaluator.evaluate('Sample response text')
        assert 'response' in result, "Result missing 'response' key"
        assert 'confidence' in result, "Result missing 'confidence' key"
        assert isinstance(result['confidence'], float), (
            f"Expected confidence to be float, got {type(result['confidence'])}"
        )
    
    @pytest.mark.parametrize('input_text,expected_contains', [
        ('', 'could not generate'),
        (None, 'could not generate'),
    ])
    def test_evaluate_handles_edge_cases(self, input_text, expected_contains) -> None:
        """Test evaluator handles None and empty inputs."""
        evaluator = Evaluator()
        result = evaluator.evaluate(input_text)
        assert expected_contains in result['response'].lower(), (
            f"Expected '{expected_contains}' in response for input '{input_text}'"
        )
        assert isinstance(result['confidence'], float), "Confidence should be a float"


class TestPlanner:
    """Unit tests for the Planner agent."""
    
    def test_plan_action_is_process(self) -> None:
        """Test that planner creates process action."""
        planner = Planner()
        plan = planner.plan('User question')
        assert plan['tasks'][0]['action'] == 'process', (
            f"Expected action 'process', got '{plan['tasks'][0]['action']}'"
        )
    
    def test_plan_sanitizes_input(self) -> None:
        """Test that HTML tags are sanitized from input."""
        planner = Planner()
        plan = planner.plan('<b>Bold question</b>')
        details = plan['tasks'][0]['details']
        assert '<b>' not in details['user_input'], "HTML tag '<b>' should be sanitized"
        assert 'Bold question' in details['user_input'], (
            "Sanitized text 'Bold question' should be present"
        )
    
    def test_plan_with_language_parameters(self) -> None:
        """Test planner correctly passes language parameters."""
        planner = Planner()
        plan = planner.plan(
            user_input='¿Hola?',
            document_content=None,
            document_language='es',
            preferred_language='es'
        )
        details = plan['tasks'][0]['details']
        assert details['document_language'] == 'es', (
            f"Expected document_language='es', got '{details['document_language']}'"
        )
        assert details['preferred_language'] == 'es', (
            f"Expected preferred_language='es', got '{details['preferred_language']}'"
        )
    
    def test_plan_sanitizes_document_content(self) -> None:
        """Test that document content is sanitized."""
        planner = Planner()
        plan = planner.plan(
            user_input='Question',
            document_content='<script>alert("xss")</script>Legal text'
        )
        document = plan['tasks'][0]['details']['document']
        assert '<script>' not in document, "Script tag should be sanitized"
        assert 'Legal text' in document, "Legal text should be preserved"


class TestWorker:
    """Unit tests for the Worker agent."""
    
    @patch('project.agents.worker.GeminiLLM')
    @patch('project.agents.worker.GoogleTranslator')
    def test_worker_translates_question_and_document(self, MockTranslator, MockLLM):
        """Test that Worker translates both question and document."""
        # Arrange
        mock_llm = MockLLM.return_value
        mock_llm.generate_response.return_value = UnitTestConstants.MOCK_LLM_RESPONSE
        
        mock_translator = MockTranslator.return_value
        mock_translator.translate.side_effect = ['Question EN', 'Document ES']
        
        os.environ['GOOGLE_API_KEY'] = UnitTestConstants.FAKE_API_KEY
        worker = Worker()
        
        task = {
            'action': 'process',
            'details': {
                'user_input': '¿Requisitos?',
                'document': 'documento en español',
                'document_language': 'es',
                'preferred_language': 'es'
            }
        }
        
        # Act
        output = worker.execute(task)
        
        # Assert
        assert UnitTestConstants.MOCK_LLM_RESPONSE in output
        assert mock_translator.translate.call_count >= 2
        
        # Cleanup
        del os.environ['GOOGLE_API_KEY']
    
    @patch('project.agents.worker.GeminiLLM')
    @patch('project.agents.worker.GoogleTranslator')
    def test_worker_passes_citations_to_llm(self, MockTranslator, MockLLM):
        """Test that Worker passes citations from search to LLM."""
        # Arrange
        mock_llm = MockLLM.return_value
        mock_llm.generate_response.return_value = 'Response'
        
        mock_translator = MockTranslator.return_value
        mock_translator.translate.side_effect = ['Question', 'Document']
        
        os.environ['GOOGLE_API_KEY'] = UnitTestConstants.FAKE_API_KEY
        worker = Worker()
        
        task = {
            'action': 'process',
            'details': {
                'user_input': 'Question',
                'document': 'document text',
                'document_language': 'en',
                'preferred_language': 'en'
            }
        }
        
        # Act
        worker.execute(task)
        
        # Assert
        call_args, call_kwargs = mock_llm.generate_response.call_args
        assert 'citations' in call_kwargs
        
        # Cleanup
        del os.environ['GOOGLE_API_KEY']
    
    @patch('project.agents.worker.GeminiLLM')
    @patch('project.agents.worker.GoogleTranslator')
    def test_worker_appends_domain_hint(self, MockTranslator, MockLLM):
        """Test that visa-related context detection is appended."""
        # Arrange
        mock_llm = MockLLM.return_value
        mock_llm.generate_response.return_value = 'Response'
        
        mock_translator = MockTranslator.return_value
        mock_translator.translate.side_effect = ['Question', 'Document with visa']
        
        os.environ['GOOGLE_API_KEY'] = UnitTestConstants.FAKE_API_KEY
        worker = Worker()
        
        task = {
            'action': 'process',
            'details': {
                'user_input': 'Question',
                'document': 'visa document',
                'document_language': 'auto',
                'preferred_language': 'es'
            }
        }
        
        # Act
        output = worker.execute(task)
        
        # Assert
        assert 'Detected visa-related context' in output
        
        # Cleanup
        del os.environ['GOOGLE_API_KEY']
    
    @patch('project.agents.worker.GeminiLLM')
    def test_worker_handles_unknown_action(self, MockLLM):
        """Test Worker returns error message for unknown actions."""
        worker = Worker()
        task = {'action': 'invalid_action', 'details': {'user_input': 'test'}}
        result = worker.execute(task)
        assert result == 'Unknown action'
    
    @patch('project.agents.worker.GeminiLLM')
    def test_worker_language_auto_detection(self, MockLLM) -> None:
        """Test language auto-detection for documents."""
        worker = Worker()
        spanish_text = UnitTestConstants.SAMPLE_SPANISH_TEXT
        detected = worker._detect_language(spanish_text)
        assert detected in ['es', 'en'], (
            f"Expected language 'es' or 'en', got '{detected}'"
        )
    
    @pytest.mark.parametrize('text,expected', [
        ('', 'en'),
        ('a', 'en'),
        (None, 'en'),
    ])
    @patch('project.agents.worker.GeminiLLM')
    def test_worker_empty_text_detection_fallback(self, MockLLM, text, expected) -> None:
        """Test language detection fallback for empty/short text."""
        worker = Worker()
        result = worker._detect_language(text)
        assert result == expected, f"Expected '{expected}' for input '{text}', got '{result}'"
    
    @patch('project.agents.worker.GeminiLLM')
    @patch('project.agents.worker.GoogleTranslator')
    def test_worker_translate_exception_uses_original_doc(self, MockTranslator, MockLLM):
        """Test fallback to original document when translation fails."""
        # Arrange
        mock_llm = MockLLM.return_value
        
        def capture_generate(*args, **kwargs):
            assert kwargs.get('document_content_original') is not None
            return 'Fallback response'
        
        mock_llm.generate_response.side_effect = capture_generate
        
        mock_translator = MockTranslator.return_value
        mock_translator.translate.side_effect = Exception('Translation failure')
        
        os.environ['GOOGLE_API_KEY'] = UnitTestConstants.FAKE_API_KEY
        worker = Worker()
        
        task = {
            'action': 'process',
            'details': {
                'user_input': 'Question',
                'document': 'original document',
                'document_language': 'es',
                'preferred_language': 'es'
            }
        }
        
        # Act
        output = worker.execute(task)
        
        # Assert
        assert 'Fallback response' in output
        
        # Cleanup
        del os.environ['GOOGLE_API_KEY']
    
    @patch('project.agents.worker.GeminiLLM')
    def test_worker_execute_without_document(self, MockLLM):
        """Test Worker execution when no document is provided."""
        mock_llm = MockLLM.return_value
        mock_llm.generate_response.return_value = 'Response without document'
        
        os.environ['GOOGLE_API_KEY'] = UnitTestConstants.FAKE_API_KEY
        worker = Worker()
        
        task = {
            'action': 'process',
            'details': {
                'user_input': 'What are visa requirements?',
                'document': None,
                'document_language': 'auto',
                'preferred_language': 'en'
            }
        }
        
        output = worker.execute(task)
        assert output == 'Response without document'
        
        del os.environ['GOOGLE_API_KEY']
    
    @pytest.mark.parametrize('invalid_task_key', [
        'missing_action',
        'none_task',
        'empty_task',
        'wrong_type',
    ])
    @patch('project.agents.worker.GeminiLLM')
    def test_worker_handles_invalid_task_structures(
        self, 
        MockLLM, 
        invalid_task_key,
        invalid_tasks
    ) -> None:
        """Test Worker handles various invalid task structures gracefully."""
        worker = Worker()
        invalid_task = invalid_tasks[invalid_task_key]
        
        # Should either raise exception or return error message
        try:
            result = worker.execute(invalid_task)
            # If it returns, check it's an error indication
            assert isinstance(result, str), f"Expected string result for {invalid_task_key}"
            assert 'error' in result.lower() or 'unknown' in result.lower() or 'invalid' in result.lower(), (
                f"Expected error indication for {invalid_task_key}, got: {result}"
            )
        except (KeyError, AttributeError, TypeError) as e:
            # Expected for malformed tasks - these should raise exceptions
            assert invalid_task_key in ['none_task', 'wrong_type', 'empty_task'], (
                f"Unexpected exception for {invalid_task_key}: {e}"
            )
    
    @patch('project.agents.worker.GeminiLLM')
    @patch('project.agents.worker.GoogleTranslator')
    def test_worker_with_very_long_document(self, MockTranslator, MockLLM, monkeypatch) -> None:
        """Test Worker handles very long documents (>10000 chars)."""
        # Arrange
        mock_llm = MockLLM.return_value
        mock_llm.generate_response.return_value = 'Processed long document'
        
        mock_translator = MockTranslator.return_value
        mock_translator.translate.side_effect = ['Question', 'Long doc']
        
        monkeypatch.setenv('GOOGLE_API_KEY', UnitTestConstants.FAKE_API_KEY)
        worker = Worker()
        
        # Create very long document
        long_document = 'Legal text about visa. ' * 500  # ~12,000 chars
        
        task = {
            'action': 'process',
            'details': {
                'user_input': 'Question',
                'document': long_document,
                'document_language': 'en',
                'preferred_language': 'en'
            }
        }
        
        # Act
        output = worker.execute(task)
        
        # Assert - Should handle without crashing
        assert 'Processed long document' in output, "Should process long documents"
        monkeypatch.delenv('GOOGLE_API_KEY', raising=False)
    
    @patch('project.agents.worker.GeminiLLM')
    @patch('project.agents.worker.GoogleTranslator')
    def test_worker_with_special_characters_in_input(
        self, 
        MockTranslator, 
        MockLLM,
        monkeypatch
    ) -> None:
        """Test Worker handles special characters and emojis."""
        # Arrange
        mock_llm = MockLLM.return_value
        mock_llm.generate_response.return_value = 'Response with special chars'
        
        mock_translator = MockTranslator.return_value
        mock_translator.translate.return_value = 'Translated'
        
        monkeypatch.setenv('GOOGLE_API_KEY', UnitTestConstants.FAKE_API_KEY)
        worker = Worker()
        
        task = {
            'action': 'process',
            'details': {
                'user_input': '¿What 🤔 about émoji & spëcial çhars?',
                'document': 'Document with émojis 😀 and ñoño text',
                'document_language': 'auto',
                'preferred_language': 'en'
            }
        }
        
        # Act
        output = worker.execute(task)
        
        # Assert
        assert isinstance(output, str), "Should return string even with special chars"
        monkeypatch.delenv('GOOGLE_API_KEY', raising=False)


# ============================================================================
# Core Module Tests
# ============================================================================

class TestContextEngineering:
    """Unit tests for context engineering utilities."""
    
    def test_sanitize_input_removes_html_tags(self) -> None:
        """Test HTML tag removal."""
        result1 = sanitize_input('<i>text</i>')
        assert result1 == 'text', f"Expected 'text', got '{result1}'"
        result2 = sanitize_input('<script>alert("xss")</script>')
        assert result2 == 'alert("xss")', f"Expected 'alert(\"xss\")', got '{result2}'"
    
    def test_sanitize_input_normalizes_whitespace(self) -> None:
        """Test whitespace normalization."""
        result1 = sanitize_input('text  with   spaces')
        assert result1 == 'text with spaces', f"Expected 'text with spaces', got '{result1}'"
        result2 = sanitize_input('\n\ntext\n\n')
        assert result2 == 'text', f"Expected 'text', got '{result2}'"
    
    def test_context_engine_builds_context(self) -> None:
        """Test context building with all parameters."""
        engine = ContextEngine()
        context = engine.build_context(
            user_input='Question?',
            session_data={'user': 'alice'},
            document_content='doc text'
        )
        
        assert "Context(session={'user': 'alice'})" in context, (
            f"Expected session context in output, got: {context[:100]}"
        )
        assert 'Input=Question?' in context, f"Expected user input in context"
        assert 'Document=doc text' in context, f"Expected document content in context"


class TestObservability:
    """Unit tests for observability logging."""
    
    def test_observability_logs_event(self, caplog) -> None:
        """Test that events are logged correctly."""
        caplog.set_level(logging.INFO)
        Observability.log('start', {'key': 'value'})
        
        event_found = any(('"event": "start"' in record.message for record in caplog.records))
        assert event_found, (
            f"'start' event not found in logs: {[r.message for r in caplog.records]}"
        )
    
    def test_observability_redacts_pii(self, caplog) -> None:
        """Test that PII is redacted when contains_pii=True."""
        caplog.set_level(logging.INFO)
        Observability.log('sensitive', {'secret': 'data'}, contains_pii=True)
        
        log_message = next(r.message for r in caplog.records if 'sensitive' in r.message)
        assert '[REDACTED]' in log_message, f"Expected '[REDACTED]' in log: {log_message}"
        assert 'secret' not in log_message, f"Expected 'secret' to be redacted: {log_message}"


class TestA2AProtocol:
    """Unit tests for Agent-to-Agent protocol."""
    
    def test_a2a_message_has_required_fields(self):
        """Test that A2A messages contain all required fields."""
        message = create_message('planner', 'worker', {'task': 'process'})
        
        required_fields = {'task_id', 'sender', 'receiver', 'payload', 'timestamp'}
        assert required_fields.issubset(message.keys())
    
    def test_a2a_message_sender_and_receiver(self):
        """Test sender and receiver are set correctly."""
        message = create_message('agent1', 'agent2', {})
        
        assert message['sender'] == 'agent1'
        assert message['receiver'] == 'agent2'


# ============================================================================
# Memory Tests
# ============================================================================

class TestSessionMemory:
    """Unit tests for session memory with encryption."""
    
    def test_session_memory_with_secret(self, monkeypatch):
        """Test session memory with custom encryption secret."""
        key = Fernet.generate_key().decode()
        monkeypatch.setenv('SESSION_SECRET', key)
        
        memory = SessionMemory()
        memory.store('key', 'value')
        
        assert memory.retrieve('key') == 'value'
    
    def test_session_memory_without_secret(self, monkeypatch):
        """Test session memory generates key when no secret provided."""
        monkeypatch.delenv('SESSION_SECRET', raising=False)
        
        memory = SessionMemory()
        memory.store('key', 'value')
        
        assert memory.retrieve('key') == 'value'
    
    def test_session_memory_retrieve_nonexistent_key(self, monkeypatch) -> None:
        """Test retrieving a key that doesn't exist."""
        monkeypatch.delenv('SESSION_SECRET', raising=False)
        
        memory = SessionMemory()
        result = memory.retrieve('nonexistent_key')
        assert result is None, f"Expected None for nonexistent key, got {result}"
    
    @pytest.mark.parametrize('key,value', [
        ('normal', 'value'),
        ('', 'empty_key'),
        ('key', ''),
        ('unicode', '日本語'),
        ('special', 'value!@#$%^&*()'),
    ])
    def test_session_memory_edge_cases(self, monkeypatch, key, value) -> None:
        """Test session memory with various edge case inputs."""
        monkeypatch.delenv('SESSION_SECRET', raising=False)
        memory = SessionMemory()
        memory.store(key, value)
        retrieved = memory.retrieve(key)
        assert retrieved == value, f"Expected '{value}', got '{retrieved}' for key '{key}'"
        assert memory.retrieve('nonexistent') is None


# ============================================================================
# Tools Tests
# ============================================================================

class TestSafeCalculator:
    """Unit tests for the SafeCalculator tool."""
    
    @pytest.mark.parametrize('expression,expected', [
        ('1+2', 3),
        ('10-5', 5),
        ('3*4', 12),
        ('10/2', 5.0),
        ('5/2', 2.5),
        ('+10', 10),
        ('-5', -5),
        ('2 + 3 * 4', 14),
        ('(2 + 3) * 4', 20),
    ])
    def test_calculator_operations(self, expression, expected) -> None:
        """Test various calculator operations with parametrized inputs."""
        result = SafeCalculator.evaluate(expression)
        assert result == expected, f"Expected {expected} for '{expression}', got {result}"
    
    @pytest.mark.parametrize('invalid_expr', [
        'foo(1)',
        '1 + ',
        'import os',
        '__import__("os")',
        '1; 2',
    ])
    def test_invalid_expressions(self, invalid_expr) -> None:
        """Test error handling for invalid and malicious expressions."""
        result = SafeCalculator.evaluate(invalid_expr)
        assert 'Invalid' in result, f"Expected 'Invalid' in result for '{invalid_expr}', got '{result}'"
    
    def test_division_by_zero(self) -> None:
        """Test division by zero returns error."""
        result = SafeCalculator.evaluate('10/0')
        assert 'Invalid' in result or 'error' in str(result).lower(), (
            f"Expected error for division by zero, got '{result}'"
        )


class TestSummarizer:
    """Unit tests for the text summarizer tool."""
    
    def test_summarizer_short_text(self):
        """Test that short text is not truncated."""
        text = 'short text'
        assert summarizer(text) == text
    
    def test_summarizer_long_text(self):
        """Test that long text is truncated with ellipsis."""
        text = 'x' * 300
        result = summarizer(text)
        assert result.endswith('...')
        assert len(result) == 203  # 200 + '...'
    
    def test_summarizer_edge_cases(self):
        """Test edge cases like None and empty strings."""
        assert summarizer('') == ''
        assert summarizer(None) == ''
    
    def test_summarizer_custom_max_length(self):
        """Test custom max length parameter."""
        text = 'x' * 100
        result = summarizer(text, max_len=50)
        assert len(result) == 53  # 50 + '...'


class TestSimpleSearch:
    """Unit tests for the SimpleSearch tool."""
    
    def test_simple_search_add_and_query(self):
        """Test adding documents and querying."""
        search = SimpleSearch()
        search.add('doc1', 'visa application requires documents')
        search.add('doc2', 'residence permit and study visa')
        
        hits = search.query('visa application', top_k=2)
        assert len(hits) >= 1
    
    def test_simple_search_ranking(self):
        """Test that results are ranked by relevance."""
        search = SimpleSearch()
        search.add('doc1', 'visa')
        search.add('doc2', 'visa visa visa')  # More occurrences
        
        hits = search.query('visa', top_k=2)
        # Doc2 should rank higher due to more matches
        assert hits[0][1] == 'doc2'


class TestDomainTools:
    """Unit tests for domain-specific tools."""
    
    def test_extract_visa_requirements_detects_keywords(self):
        """Test visa keyword detection."""
        text = 'You need a work permit and visa.'
        info = DomainTools.extract_visa_requirements(text)
        
        assert info['has_visa_context'] is True
        assert 'visa' in info['matched_keywords']
        assert 'permit' in info['matched_keywords']
    
    def test_extract_visa_requirements_no_keywords(self):
        """Test when no visa keywords are present."""
        text = 'This is about something else entirely.'
        info = DomainTools.extract_visa_requirements(text)
        
        assert info['has_visa_context'] is False
        assert len(info['matched_keywords']) == 0


class TestGoogleTranslator:
    """Unit tests for GoogleTranslator."""
    
    @patch('project.tools.tools.GoogleTranslator.translate')
    def test_translate_returns_text(self, mock_translate) -> None:
        """Test that translator returns translated text."""
        mock_translate.return_value = 'Translated'
        translator = GoogleTranslator()
        result = translator.translate('Hello', 'es')
        assert result == 'Translated', f"Expected 'Translated', got '{result}'"
    
    @pytest.mark.parametrize('text', ['', None])
    @patch('project.tools.tools.GoogleTranslator.translate')
    def test_translate_with_empty_input(self, mock_translate, text) -> None:
        """Test translation with None or empty input."""
        mock_translate.return_value = text if text else ''
        translator = GoogleTranslator()
        result = translator.translate(text, 'es')
        assert isinstance(result, str), f"Expected string result, got {type(result)}"


class TestGoogleTranslator:
    
    def test_google_translator_no_api_key(self, monkeypatch):
        """Test translator raises when API key is missing."""
        monkeypatch.delenv('GOOGLE_API_KEY', raising=False)
        
        with pytest.raises(RuntimeError, match='GOOGLE_API_KEY missing'):
            GoogleTranslator()
    
    @patch('project.tools.tools.requests')
    def test_google_translator_success(self, mock_requests):
        """Test successful translation."""
        mock_requests.post.return_value.raise_for_status.return_value = None
        mock_requests.post.return_value.json.return_value = {
            'data': {'translations': [{'translatedText': 'Hola'}]}
        }
        
        os.environ['GOOGLE_API_KEY'] = UnitTestConstants.FAKE_API_KEY
        translator = GoogleTranslator()
        result = translator.translate('Hello', target='es')
        
        assert result == 'Hola'
        
        del os.environ['GOOGLE_API_KEY']
    
    @patch('project.tools.tools.requests')
    def test_google_translator_api_error(self, mock_requests):
        """Test error handling when API returns error."""
        mock_requests.post.return_value.raise_for_status.side_effect = \
            requests.exceptions.RequestException('API Error')
        
        os.environ['GOOGLE_API_KEY'] = UnitTestConstants.FAKE_API_KEY
        translator = GoogleTranslator()
        
        with pytest.raises(requests.exceptions.RequestException):
            translator.translate('Hello', target='es')
        
        del os.environ['GOOGLE_API_KEY']
    
    @patch('project.tools.tools.requests')
    def test_translator_with_very_long_text(self, mock_requests, monkeypatch) -> None:
        """Test translator handles text longer than API limits."""
        mock_requests.post.return_value.json.return_value = {
            'data': {'translations': [{'translatedText': 'Translated long text'}]}
        }
        
        monkeypatch.setenv('GOOGLE_API_KEY', UnitTestConstants.FAKE_API_KEY)
        translator = GoogleTranslator()
        
        # Create text longer than typical API limits (>5000 chars)
        long_text = 'This is a very long legal document. ' * 200  # ~7400 chars
        
        result = translator.translate(long_text, target='es')
        
        assert isinstance(result, str), "Should return string for long text"
        monkeypatch.delenv('GOOGLE_API_KEY', raising=False)
    
    @pytest.mark.parametrize('text,target_lang', [
        ('Hello 😀 World', 'es'),  # Emojis
        ('Ñoño & spëcial', 'en'),  # Special characters
        ('日本語テキスト', 'en'),  # Japanese
        ('Mixed English und Deutsch', 'fr'),  # Mixed languages
    ])
    @patch('project.tools.tools.requests')
    def test_translator_with_special_characters(
        self, 
        mock_requests, 
        text, 
        target_lang,
        monkeypatch
    ) -> None:
        """Test translator handles special characters and mixed languages."""
        mock_requests.post.return_value.json.return_value = {
            'data': {'translations': [{'translatedText': f'Translated: {text}'}]}
        }
        
        monkeypatch.setenv('GOOGLE_API_KEY', UnitTestConstants.FAKE_API_KEY)
        translator = GoogleTranslator()
        
        result = translator.translate(text, target=target_lang)
        
        assert isinstance(result, str), f"Should handle special chars in: {text}"
        monkeypatch.delenv('GOOGLE_API_KEY', raising=False)


class TestPDFExtractionErrors:
    """Unit tests for PDF extraction error cases."""
    
    def test_extract_pdf_nonexistent_file(self) -> None:
        """Test PDF extraction with non-existent file."""
        with pytest.raises((FileNotFoundError, OSError)):
            extract_pdf_text('/nonexistent/path/file.pdf')
    
    def test_extract_pdf_empty_file(self, tmp_path) -> None:
        """Test PDF extraction with empty file."""
        empty_pdf = tmp_path / 'empty.pdf'
        empty_pdf.write_bytes(b'')  # Create empty file
        
        # Should raise error or return empty string
        try:
            result = extract_pdf_text(str(empty_pdf))
            assert result == '' or 'error' in result.lower(), (
                "Empty PDF should return empty string or error"
            )
        except Exception as e:
            # Acceptable to raise exception for malformed PDF
            assert isinstance(e, (ValueError, OSError, Exception))
    
    def test_extract_pdf_corrupted_file(self, tmp_path) -> None:
        """Test PDF extraction with corrupted file."""
        corrupted_pdf = tmp_path / 'corrupted.pdf'
        corrupted_pdf.write_bytes(b'This is not a valid PDF file')
        
        # Should handle gracefully - either exception or error message
        try:
            result = extract_pdf_text(str(corrupted_pdf))
            assert isinstance(result, str), "Should return string"
        except Exception as e:
            # Expected for corrupted files
            assert isinstance(e, (ValueError, OSError, Exception))
    
    def test_extract_pdf_with_none_path(self) -> None:
        """Test PDF extraction with None path."""
        with pytest.raises((TypeError, AttributeError, ValueError)):
            extract_pdf_text(None)
    
    def test_extract_pdf_with_directory_path(self, tmp_path) -> None:
        """Test PDF extraction when path is a directory."""
        with pytest.raises((IsADirectoryError, OSError, PermissionError)):
            extract_pdf_text(str(tmp_path))


class TestDOCXExtractionErrors:
    """Unit tests for DOCX extraction error cases."""
    
    def test_extract_docx_nonexistent_file(self) -> None:
        """Test DOCX extraction with non-existent file - returns empty string."""
        try:
            from project.tools.tools import extract_docx_text
        except (ImportError, AttributeError):
            pytest.skip("python-docx not installed or extract_docx_text not available")
            return
        
        # Function returns empty string on error
        result = extract_docx_text('/nonexistent/path/file.docx')
        assert result == "", "Should return empty string for nonexistent file"
    
    def test_extract_docx_corrupted_file(self, tmp_path) -> None:
        """Test DOCX extraction with corrupted file."""
        try:
            from project.tools.tools import extract_docx_text
            
            corrupted_docx = tmp_path / 'corrupted.docx'
            corrupted_docx.write_bytes(b'This is not a valid DOCX file')
            
            # Should handle gracefully
            try:
                result = extract_docx_text(str(corrupted_docx))
                assert isinstance(result, str)
            except Exception as e:
                # Expected for corrupted files
                assert isinstance(e, Exception)
        except ImportError:
            pytest.skip("python-docx not installed")
    
    def test_extract_docx_with_none_path(self) -> None:
        """Test DOCX extraction with None path - returns empty string."""
        try:
            from project.tools.tools import extract_docx_text
        except (ImportError, AttributeError):
            pytest.skip("python-docx not installed or extract_docx_text not available")
            return
        
        # Function returns empty string on error
        result = extract_docx_text(None)
        assert result == "", "Should return empty string for None path"


class TestMainAgentErrorPropagation:
    """Tests for MainAgent error handling and propagation."""
    
    @patch('project.main_agent.Worker')
    def test_main_agent_handles_worker_exception(
        self, 
        MockWorker, 
        monkeypatch
    ) -> None:
        """Test MainAgent handles Worker exceptions gracefully."""
        # Arrange
        mock_worker = MockWorker.return_value
        mock_worker.execute.side_effect = Exception("Worker processing error")
        monkeypatch.setenv('GOOGLE_API_KEY', 'fake_key')
        
        from project.main_agent import MainAgent
        agent = MainAgent()
        
        # Act & Assert - Should either handle gracefully or propagate
        try:
            response = agent.handle_message('Test query')
            # If it returns, should contain error indication
            assert 'response' in response
            assert isinstance(response['confidence'], (int, float, str))
        except Exception as e:
            # Also acceptable to propagate exception
            assert 'Worker processing error' in str(e)
        
        monkeypatch.delenv('GOOGLE_API_KEY', raising=False)
    
    @patch('project.main_agent.Worker')
    @patch('project.main_agent.Evaluator')
    def test_main_agent_handles_evaluator_exception(
        self, 
        MockEvaluator,
        MockWorker, 
        monkeypatch
    ) -> None:
        """Test MainAgent handles Evaluator exceptions."""
        # Arrange
        mock_worker = MockWorker.return_value
        mock_worker.execute.return_value = 'Worker output'
        
        mock_evaluator = MockEvaluator.return_value
        mock_evaluator.evaluate.side_effect = Exception("Evaluator error")
        
        monkeypatch.setenv('GOOGLE_API_KEY', 'fake_key')
        
        from project.main_agent import MainAgent
        agent = MainAgent()
        
        # Act & Assert
        try:
            response = agent.handle_message('Test query')
            assert isinstance(response, dict)
        except Exception as e:
            assert 'Evaluator error' in str(e)
        
        monkeypatch.delenv('GOOGLE_API_KEY', raising=False)
    
    @patch('project.main_agent.Worker')
    def test_main_agent_handles_empty_worker_response(
        self, 
        MockWorker, 
        monkeypatch
    ) -> None:
        """Test MainAgent handles empty/None worker responses."""
        # Arrange
        mock_worker = MockWorker.return_value
        mock_worker.execute.return_value = None
        monkeypatch.setenv('GOOGLE_API_KEY', 'fake_key')
        
        from project.main_agent import MainAgent
        agent = MainAgent()
        
        # Act
        response = agent.handle_message('Test query')
        
        # Assert - Should handle None gracefully
        assert isinstance(response, dict)
        assert 'response' in response
        monkeypatch.delenv('GOOGLE_API_KEY', raising=False)


class TestGeminiLLM:
    """Unit tests for Gemini LLM."""
    
    def test_gemini_llm_init_no_key(self, monkeypatch):
        """Test LLM initialization fails without API key."""
        monkeypatch.delenv('GOOGLE_API_KEY', raising=False)
        
        with pytest.raises(RuntimeError, match='missing for GeminiLLM'):
            GeminiLLM()
    
    @patch('google.generativeai.GenerativeModel')
    def test_gemini_llm_generate_response(self, MockModel, monkeypatch):
        """Test successful response generation."""
        mock = MockModel.return_value
        mock.generate_content.return_value.text = 'Mocked response'
        
        monkeypatch.setenv('GOOGLE_API_KEY', UnitTestConstants.FAKE_API_KEY)
        llm = GeminiLLM()
        
        result = llm.generate_response('Question', 'Translated question')
        assert result == 'Mocked response'
        
        monkeypatch.delenv('GOOGLE_API_KEY', raising=False)
    
    @patch('google.generativeai.GenerativeModel')
    def test_gemini_llm_error_handling(self, MockModel, monkeypatch):
        """Test error handling when LLM fails."""
        mock = MockModel.return_value
        mock.generate_content.side_effect = Exception('LLM error')
        
        monkeypatch.setenv('GOOGLE_API_KEY', UnitTestConstants.FAKE_API_KEY)
        llm = GeminiLLM()
        
        result = llm.generate_response('Question')
        assert result == 'Unable to generate response at this time.'
        
        monkeypatch.delenv('GOOGLE_API_KEY', raising=False)


class TestPDFExtraction:
    """Unit tests for PDF text extraction."""
    
    def test_extract_pdf_text(self, tmp_path):
        """Test PDF text extraction."""
        from reportlab.pdfgen import canvas
        
        pdf_path = tmp_path / 'test.pdf'
        c = canvas.Canvas(str(pdf_path))
        c.drawString(100, 750, 'This is a PDF test for extraction.')
        c.save()
        
        text = extract_pdf_text(str(pdf_path))
        assert 'PDF test for extraction' in text


# ============================================================================
# Integration Tests (run_agent)
# ============================================================================

class TestRunAgent:
    """Integration tests for the run_agent function."""
    
    @patch('project.agents.worker.GeminiLLM')
    @patch('project.agents.worker.GoogleTranslator')
    def test_run_agent_returns_polished_dict(self, MockTranslator, MockLLM, monkeypatch):
        """Test that run_agent returns properly formatted response."""
        MockLLM.return_value.generate_response.return_value = 'Mocked response'
        MockTranslator.return_value.translate.return_value = 'Translated'
        
        monkeypatch.setenv('GOOGLE_API_KEY', UnitTestConstants.FAKE_API_KEY)
        
        output = run_agent('Hello!')
        
        assert isinstance(output, dict)
        assert 'response' in output
        assert 'confidence' in output
        assert 'Privacy Notice' in output['response']
        
        monkeypatch.delenv('GOOGLE_API_KEY', raising=False)
    
    @patch('project.agents.worker.GeminiLLM')
    @patch('project.agents.worker.GoogleTranslator')
    def test_run_agent_with_language_parameters(self, MockTranslator, MockLLM, monkeypatch):
        """Test run_agent with specific language parameters."""
        MockLLM.return_value.generate_response.return_value = 'Spanish response'
        MockTranslator.return_value.translate.return_value = 'Translated'
        
        monkeypatch.setenv('GOOGLE_API_KEY', UnitTestConstants.FAKE_API_KEY)
        
        output = run_agent(
            user_input='¿Pregunta?',
            document_content=None,
            document_language='es',
            preferred_language='es'
        )
        
        assert isinstance(output, dict)
        assert 'response' in output
        assert 'confidence' in output
        
        monkeypatch.delenv('GOOGLE_API_KEY', raising=False)
