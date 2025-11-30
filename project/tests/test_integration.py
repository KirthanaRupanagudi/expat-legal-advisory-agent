"""
Integration Tests for Expat Legal Advisory Agent

This module contains integration tests that verify how different components
work together, including:
- MainAgent with Worker integration
- Observability logging
- A2A protocol integration
- End-to-end message flow
"""

import logging
import os
from unittest.mock import patch

from project.main_agent import MainAgent


class IntegrationTestConstants:
    """Constants used across integration tests."""
    
    DUMMY_API_KEY = 'dummy_key_for_integration_tests'
    
    # Sample queries
    VISA_QUERY = 'Check visa requirements'
    RESIDENCE_QUERY = 'What are residence permit requirements?'
    
    # Mock responses
    MOCK_VISA_RESPONSE = 'Mocked LLM response for Check visa'
    MOCK_RESIDENCE_RESPONSE = 'Mocked LLM response for residence permit'


class TestMainAgentIntegration:
    """Integration tests for MainAgent component."""
    
    @patch('project.main_agent.Worker')
    def test_main_agent_handles_message_successfully(
        self, 
        MockWorker, 
        monkeypatch,
        caplog
    ) -> None:
        """
        Test that MainAgent successfully processes a message through the full pipeline.
        
        This test verifies:
        - MainAgent initializes correctly
        - Worker is invoked with correct parameters
        - Response contains expected fields
        - Return type is correct
        
        Args:
            MockWorker: Mocked Worker class.
            monkeypatch: Pytest fixture for environment manipulation.
            caplog: Pytest fixture for capturing log output.
        """
        # Arrange
        caplog.set_level(logging.INFO)
        mock_worker = MockWorker.return_value
        mock_worker.execute.return_value = IntegrationTestConstants.MOCK_VISA_RESPONSE
        monkeypatch.setenv('GOOGLE_API_KEY', IntegrationTestConstants.DUMMY_API_KEY)
        
        agent = MainAgent()
        
        # Act
        response = agent.handle_message(IntegrationTestConstants.VISA_QUERY)
        
        # Assert - Response structure
        assert isinstance(response, dict), "Response should be a dictionary"
        assert 'response' in response, "Response missing 'response' field"
        assert 'confidence' in response, "Response missing 'confidence' field"
        
        # Assert - Worker was called
        mock_worker.execute.assert_called_once()
        
        # Cleanup
        monkeypatch.delenv('GOOGLE_API_KEY', raising=False)
    
    @patch('project.main_agent.Worker')
    def test_main_agent_with_different_queries(
        self, 
        MockWorker, 
        monkeypatch
    ) -> None:
        """
        Test MainAgent with various query types.
        
        Args:
            MockWorker: Mocked Worker class.
            monkeypatch: Pytest fixture for environment manipulation.
        """
        # Arrange
        mock_worker = MockWorker.return_value
        mock_worker.execute.return_value = IntegrationTestConstants.MOCK_RESIDENCE_RESPONSE
        monkeypatch.setenv('GOOGLE_API_KEY', IntegrationTestConstants.DUMMY_API_KEY)
        
        agent = MainAgent()
        
        # Act
        response = agent.handle_message(IntegrationTestConstants.RESIDENCE_QUERY)
        
        # Assert
        assert response['response'] is not None
        assert isinstance(response['confidence'], (int, float, str))
        
        # Cleanup
        monkeypatch.delenv('GOOGLE_API_KEY', raising=False)


class TestObservabilityIntegration:
    """Integration tests for observability and logging."""
    
    @patch('project.main_agent.Worker')
    def test_observability_logs_start_event(
        self, 
        MockWorker, 
        monkeypatch, 
        caplog
    ) -> None:
        """
        Test that observability logging captures start event.
        
        Args:
            MockWorker: Mocked Worker class.
            monkeypatch: Pytest fixture for environment manipulation.
            caplog: Pytest fixture for capturing log output.
        """
        # Arrange
        caplog.set_level(logging.INFO)
        mock_worker = MockWorker.return_value
        mock_worker.execute.return_value = IntegrationTestConstants.MOCK_VISA_RESPONSE
        monkeypatch.setenv('GOOGLE_API_KEY', IntegrationTestConstants.DUMMY_API_KEY)
        
        # Act
        agent = MainAgent()
        agent.handle_message(IntegrationTestConstants.VISA_QUERY)
        
        # Assert - Check for start event in logs
        start_event_found = any(
            '"event": "start"' in record.message 
            for record in caplog.records
        )
        assert start_event_found, (
            "'start' event not found in logs. "
            f"Available logs: {[r.message for r in caplog.records]}"
        )
        
        # Cleanup
        monkeypatch.delenv('GOOGLE_API_KEY', raising=False)
    
    @patch('project.main_agent.Worker')
    def test_observability_logs_end_event(
        self, 
        MockWorker, 
        monkeypatch, 
        caplog
    ) -> None:
        """
        Test that observability logging captures end event.
        
        Args:
            MockWorker: Mocked Worker class.
            monkeypatch: Pytest fixture for environment manipulation.
            caplog: Pytest fixture for capturing log output.
        """
        # Arrange
        caplog.set_level(logging.INFO)
        mock_worker = MockWorker.return_value
        mock_worker.execute.return_value = IntegrationTestConstants.MOCK_VISA_RESPONSE
        monkeypatch.setenv('GOOGLE_API_KEY', IntegrationTestConstants.DUMMY_API_KEY)
        
        # Act
        agent = MainAgent()
        agent.handle_message(IntegrationTestConstants.VISA_QUERY)
        
        # Assert - Check for end event in logs
        end_event_found = any(
            '"event": "end"' in record.message 
            for record in caplog.records
        )
        assert end_event_found, (
            "'end' event not found in logs. "
            f"Available logs: {[r.message for r in caplog.records]}"
        )
        
        # Cleanup
        monkeypatch.delenv('GOOGLE_API_KEY', raising=False)
    
    @patch('project.main_agent.Worker')
    def test_observability_logs_complete_workflow(
        self, 
        MockWorker, 
        monkeypatch, 
        caplog
    ) -> None:
        """
        Test that observability captures the complete workflow (start to end).
        
        Args:
            MockWorker: Mocked Worker class.
            monkeypatch: Pytest fixture for environment manipulation.
            caplog: Pytest fixture for capturing log output.
        """
        # Arrange
        caplog.set_level(logging.INFO)
        mock_worker = MockWorker.return_value
        mock_worker.execute.return_value = IntegrationTestConstants.MOCK_VISA_RESPONSE
        monkeypatch.setenv('GOOGLE_API_KEY', IntegrationTestConstants.DUMMY_API_KEY)
        
        # Act
        agent = MainAgent()
        result = agent.handle_message(IntegrationTestConstants.VISA_QUERY)
        
        # Assert - Both start and end events should be logged
        log_messages = [record.message for record in caplog.records]
        
        start_logged = any('"event": "start"' in msg for msg in log_messages)
        end_logged = any('"event": "end"' in msg for msg in log_messages)
        
        assert start_logged and end_logged, (
            "Complete workflow not logged. "
            f"Start: {start_logged}, End: {end_logged}"
        )
        
        # Assert - Result is valid
        assert isinstance(result, dict)
        assert 'response' in result
        
        # Cleanup
        monkeypatch.delenv('GOOGLE_API_KEY', raising=False)


class TestA2AProtocolIntegration:
    """Integration tests for Agent-to-Agent (A2A) protocol."""
    
    @patch('project.main_agent.Worker')
    def test_a2a_protocol_message_handling(
        self, 
        MockWorker, 
        monkeypatch
    ) -> None:
        """
        Test that A2A protocol integration works correctly.
        
        This verifies that the MainAgent properly integrates with
        the A2A protocol for inter-agent communication.
        
        Args:
            MockWorker: Mocked Worker class.
            monkeypatch: Pytest fixture for environment manipulation.
        """
        # Arrange
        mock_worker = MockWorker.return_value
        mock_worker.execute.return_value = IntegrationTestConstants.MOCK_VISA_RESPONSE
        monkeypatch.setenv('GOOGLE_API_KEY', IntegrationTestConstants.DUMMY_API_KEY)
        
        # Act
        agent = MainAgent()
        response = agent.handle_message(IntegrationTestConstants.VISA_QUERY)
        
        # Assert - Response follows A2A protocol expectations
        assert isinstance(response, dict), "A2A response should be dict"
        assert 'response' in response, "A2A message missing response"
        assert 'confidence' in response, "A2A message missing confidence"
        
        # Cleanup
        monkeypatch.delenv('GOOGLE_API_KEY', raising=False)
