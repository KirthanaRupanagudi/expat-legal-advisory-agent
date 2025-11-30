import os
from unittest.mock import patch
from project.main_agent import MainAgent
import logging

@patch('project.main_agent.Worker')
def test_integration_with_observability_and_a2a(MockWorker, monkeypatch, caplog):
    # Ensure caplog captures INFO level messages
    caplog.set_level(logging.INFO)

    mock_w = MockWorker.return_value
    mock_w.execute.return_value = 'Mocked LLM response for Check visa'
    monkeypatch.setenv('GOOGLE_API_KEY','k')
    res = MainAgent().handle_message('Check visa')
    assert isinstance(res, dict) and 'response' in res and 'confidence' in res

    # Check for log messages. The messages are JSON strings, so we need to check if the string contains the JSON fragment.
    assert any('"event": "start"' in r.message for r in caplog.records), "'start' event not found in logs"
    assert any('"event": "end"' in r.message for r in caplog.records), "'end' event not found in logs"

    monkeypatch.delenv('GOOGLE_API_KEY', raising=False)
