import os, pytest
from project.app import create_app # Import create_app factory
from flask_limiter import Limiter # Still needed for type hinting or if you manually manipulate Limiter
from flask_limiter.util import get_remote_address
from unittest.mock import patch

@pytest.fixture
def client(monkeypatch):
    # Create a fresh app for each test
    test_app = create_app() # Get app
    test_app.config['TESTING'] = True
    monkeypatch.setenv('FLASK_API_KEY', 'test_api_key')

    # Push an application context to ensure everything is set up correctly
    with test_app.test_client() as c:
        with test_app.app_context(): # Ensure app context for extensions like limiter
            yield c
    monkeypatch.delenv('FLASK_API_KEY', raising=False)

def test_auth_required(client):
    r = client.post('/query', json={'input': 'hello'})
    assert r.status_code in (401, 403)

@patch('project.app.run_agent')
def test_query_success(mock_run_agent, client):
    mock_run_agent.return_value = {'response': 'ok', 'confidence': 0.9}
    headers = {'X-API-Key': 'test_api_key'}
    r = client.post('/query', headers=headers, json={'input': 'hello', 'document_content': 'text'})
    assert r.status_code == 200
    data = r.get_json()
    assert 'response' in data and 'privacy' in data
    assert data['response']['response'] == 'ok'

@patch('project.app.run_agent')
def test_rate_limiting(mock_run_agent, client):
    mock_run_agent.return_value = {'response': 'ok', 'confidence': 0.9}
    headers = {'X-API-Key': 'test_api_key'}
    for i in range(10):
        r = client.post('/query', headers=headers, json={'input': f'hello {i}'})
        assert r.status_code == 200
    r = client.post('/query', headers=headers, json={'input': 'exceed'})
    assert r.status_code == 429
    assert r.get_json()['description'] == 'You have exceeded your rate limit.'
