"""
Pytest Configuration and Shared Fixtures

This module provides common test fixtures and configuration for all test suites.
It eliminates code duplication and provides consistent test data across all tests.
"""

import os
import tempfile
from pathlib import Path

import pytest
from cryptography.fernet import Fernet


# ============================================================================
# Pytest Configuration
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers and settings."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "e2e: marks tests as end-to-end tests"
    )
    config.addinivalue_line(
        "markers", "security: marks tests as security tests"
    )
    config.addinivalue_line(
        "markers", "performance: marks tests as performance tests"
    )


# ============================================================================
# Environment and API Key Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def fake_api_key():
    """Provide a fake API key for testing."""
    return "fake_test_key_for_testing_12345"


@pytest.fixture(scope="function")
def mock_google_api_key(monkeypatch, fake_api_key):
    """Set up a fake GOOGLE_API_KEY environment variable."""
    monkeypatch.setenv('GOOGLE_API_KEY', fake_api_key)
    yield fake_api_key
    monkeypatch.delenv('GOOGLE_API_KEY', raising=False)


@pytest.fixture(scope="function")
def mock_flask_api_key(monkeypatch):
    """Set up a fake FLASK_API_KEY environment variable."""
    test_key = "test_flask_api_key"
    monkeypatch.setenv('FLASK_API_KEY', test_key)
    yield test_key
    monkeypatch.delenv('FLASK_API_KEY', raising=False)


@pytest.fixture(scope="function")
def mock_session_secret(monkeypatch):
    """Set up a SESSION_SECRET environment variable."""
    secret = Fernet.generate_key().decode()
    monkeypatch.setenv('SESSION_SECRET', secret)
    yield secret
    monkeypatch.delenv('SESSION_SECRET', raising=False)


# ============================================================================
# Test Data Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def sample_documents():
    """Provide sample documents for testing."""
    return {
        'english': {
            'text': 'This is a sample legal document about visa requirements and residence permits.',
            'language': 'en',
            'keywords': ['visa', 'residence', 'permit']
        },
        'spanish': {
            'text': 'Este es un documento legal sobre requisitos de visa y permisos de residencia.',
            'language': 'es',
            'keywords': ['visa', 'requisitos', 'residencia']
        },
        'french': {
            'text': 'Ceci est un document juridique sur les exigences de visa et les permis de séjour.',
            'language': 'fr',
            'keywords': ['visa', 'permis', 'séjour']
        },
        'german': {
            'text': 'Dies ist ein Rechtsdokument über Visaanforderungen und Aufenthaltsgenehmigungen.',
            'language': 'de',
            'keywords': ['visa', 'aufenthalt']
        }
    }


@pytest.fixture(scope="session")
def sample_questions():
    """Provide sample questions in multiple languages."""
    return {
        'english': 'What are the visa requirements for work permits?',
        'spanish': '¿Cuáles son los requisitos de visa para permisos de trabajo?',
        'french': 'Quelles sont les exigences de visa pour les permis de travail?',
        'german': 'Was sind die Visaanforderungen für Arbeitsgenehmigungen?',
        'dutch': 'Wat zijn de visumvereisten voor werkvergunningen?'
    }


@pytest.fixture(scope="session")
def sample_translations():
    """Provide sample translation pairs for testing."""
    return [
        {'source': 'Hello', 'target': 'es', 'translated': 'Hola'},
        {'source': 'Goodbye', 'target': 'fr', 'translated': 'Au revoir'},
        {'source': 'Thank you', 'target': 'de', 'translated': 'Danke'},
        {'source': 'Yes', 'target': 'nl', 'translated': 'Ja'},
    ]


@pytest.fixture(scope="session")
def mock_llm_responses():
    """Provide sample LLM responses for mocking."""
    return {
        'visa_query': 'Based on the document, you need a valid passport and visa application.',
        'residence_query': 'The residence permit requires proof of employment and housing.',
        'general_query': 'Here is my assessment based on the provided information.',
        'error_response': 'Unable to generate response at this time.'
    }


# ============================================================================
# Temporary File and Directory Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture(scope="function")
def temp_pdf_file(temp_dir):
    """Create a temporary PDF file for testing."""
    from reportlab.pdfgen import canvas
    
    pdf_path = temp_dir / 'test_document.pdf'
    c = canvas.Canvas(str(pdf_path))
    c.drawString(100, 750, 'Sample PDF content with visa and permit information.')
    c.save()
    
    yield pdf_path


@pytest.fixture(scope="function")
def temp_docx_file(temp_dir):
    """Create a temporary DOCX file for testing."""
    from docx import Document
    
    docx_path = temp_dir / 'test_document.docx'
    doc = Document()
    doc.add_paragraph('Sample DOCX content with residence permit details.')
    doc.save(str(docx_path))
    
    yield docx_path


@pytest.fixture(scope="function")
def temp_txt_file(temp_dir):
    """Create a temporary text file for testing."""
    txt_path = temp_dir / 'test_document.txt'
    txt_path.write_text('Sample text file with legal information about visas.')
    
    yield txt_path


# ============================================================================
# Mock Object Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def mock_translator():
    """Provide a mock Google Translator."""
    from unittest.mock import Mock
    
    translator = Mock()
    translator.translate.return_value = "Mocked translation"
    
    return translator


@pytest.fixture(scope="function")
def mock_llm():
    """Provide a mock Gemini LLM."""
    from unittest.mock import Mock
    
    llm = Mock()
    llm.generate_response.return_value = "Mocked LLM response"
    
    return llm


@pytest.fixture(scope="function")
def mock_worker():
    """Provide a mock Worker agent."""
    from unittest.mock import Mock
    
    worker = Mock()
    worker.execute.return_value = "Mocked worker execution result"
    
    return worker


@pytest.fixture(scope="function")
def worker_with_mocked_env(monkeypatch, mock_google_api_key):
    """Provide a Worker instance with mocked environment and dependencies."""
    from unittest.mock import patch
    from project.agents.worker import Worker
    
    with patch('project.agents.worker.GeminiLLM') as MockLLM, \
         patch('project.agents.worker.GoogleTranslator') as MockTranslator:
        
        # Setup mocks
        mock_llm = MockLLM.return_value
        mock_llm.generate_response.return_value = "Mocked LLM response"
        
        mock_translator = MockTranslator.return_value
        mock_translator.translate.return_value = "Mocked translation"
        
        worker = Worker()
        worker._mock_llm = mock_llm
        worker._mock_translator = mock_translator
        
        yield worker


@pytest.fixture(scope="function")
def valid_task():
    """Provide a valid task structure for Worker tests."""
    return {
        'action': 'process',
        'details': {
            'user_input': 'What are visa requirements?',
            'document': 'Sample legal document about visas.',
            'document_language': 'en',
            'preferred_language': 'en'
        }
    }


@pytest.fixture(scope="function")
def invalid_tasks():
    """Provide various invalid task structures for negative testing."""
    return {
        'missing_action': {
            'details': {'user_input': 'test'}
        },
        'missing_details': {
            'action': 'process'
        },
        'none_task': None,
        'empty_task': {},
        'wrong_type': "not a dict",
        'unknown_action': {
            'action': 'invalid_action',
            'details': {'user_input': 'test'}
        },
        'missing_user_input': {
            'action': 'process',
            'details': {'document': 'text'}
        }
    }


# ============================================================================
# Flask App Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def flask_app(mock_flask_api_key):
    """Create a Flask app instance for testing."""
    from project.app import create_app
    
    app = create_app()
    app.config['TESTING'] = True
    
    yield app


@pytest.fixture(scope="function")
def flask_client(flask_app):
    """Create a Flask test client."""
    with flask_app.test_client() as client:
        with flask_app.app_context():
            yield client


# ============================================================================
# Test Markers and Utilities
# ============================================================================

@pytest.fixture(autouse=True)
def reset_environment(request):
    """Automatically reset environment variables after each test."""
    # Store original environment
    original_env = os.environ.copy()
    
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture(scope="function")
def capture_logs(caplog):
    """Capture log output at INFO level."""
    import logging
    caplog.set_level(logging.INFO)
    return caplog


# ============================================================================
# Session-wide Test Data
# ============================================================================

@pytest.fixture(scope="session")
def test_constants():
    """Provide common test constants."""
    return {
        'max_document_size': 1_000_000,  # 1MB
        'translation_chunk_size': 2000,
        'supported_languages': ['en', 'es', 'fr', 'nl', 'de'],
        'supported_file_types': ['.pdf', '.docx', '.doc', '.txt'],
        'rate_limit_per_minute': 10,
        'confidence_thresholds': {
            'high': 0.9,
            'medium': 0.7,
            'low': 0.5
        }
    }


# ============================================================================
# Cleanup Hooks
# ============================================================================

def pytest_sessionfinish(session, exitstatus):
    """Clean up after all tests complete."""
    # Clean up any temporary files that weren't auto-cleaned
    temp_files = [
        'smoke_test.pdf',
        'smoke_test.docx',
        'test.pdf',
        'test.docx'
    ]
    
    for filename in temp_files:
        if os.path.exists(filename):
            try:
                os.remove(filename)
            except OSError:
                pass  # Ignore errors during cleanup
