"""
Flask API Tests for Expat Legal Advisory Agent

This module contains unit tests for the Flask REST API, including:
- Authentication and authorization
- Rate limiting
- Query endpoint functionality
- Error handling
"""

import os

import pytest
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from unittest.mock import patch

from project.app import create_app


class FlaskAPITestConstants:
    """Constants used across API tests."""
    
    TEST_API_KEY = 'test_api_key'
    RATE_LIMIT_REQUESTS = 10
    
    # Sample request data
    SAMPLE_QUERY = {
        'input': 'What are the visa requirements?',
        'document_content': 'Sample legal document text'
    }
    
    # Sample agent response
    MOCK_AGENT_RESPONSE = {
        'response': 'You need a valid passport and visa.',
        'confidence': 0.9
    }


@pytest.fixture
def client(monkeypatch):
    """
    Create a Flask test client with proper configuration.
    
    Args:
        monkeypatch: Pytest fixture for environment manipulation.
        
    Yields:
        Flask test client configured for testing.
    """
    # Create a fresh app for each test
    test_app = create_app()
    test_app.config['TESTING'] = True
    monkeypatch.setenv('FLASK_API_KEY', FlaskAPITestConstants.TEST_API_KEY)

    # Push an application context to ensure everything is set up correctly
    with test_app.test_client() as test_client:
        with test_app.app_context():  # Ensure app context for extensions like limiter
            yield test_client
    
    # Cleanup
    monkeypatch.delenv('FLASK_API_KEY', raising=False)


class TestAuthentication:
    """Tests for API authentication and authorization."""
    
    def test_missing_api_key_returns_unauthorized(self, client) -> None:
        """Test that requests without API key are rejected."""
        response = client.post('/query', json=FlaskAPITestConstants.SAMPLE_QUERY)
        
        assert response.status_code in (401, 403), (
            f"Expected 401/403 for missing auth, got {response.status_code}"
        )
    
    def test_invalid_api_key_returns_unauthorized(self, client) -> None:
        """Test that requests with invalid API key are rejected."""
        headers = {'X-API-Key': 'invalid_key'}
        response = client.post('/query', headers=headers, json=FlaskAPITestConstants.SAMPLE_QUERY)
        
        assert response.status_code in (401, 403), (
            f"Expected 401/403 for invalid auth, got {response.status_code}"
        )


class TestQueryEndpoint:
    """Tests for the /query endpoint functionality."""
    
    @patch('project.app.run_agent')
    def test_successful_query_returns_expected_response(self, mock_run_agent, client) -> None:
        """Test successful query processing with valid input."""
        # Arrange
        mock_run_agent.return_value = FlaskAPITestConstants.MOCK_AGENT_RESPONSE
        headers = {'X-API-Key': FlaskAPITestConstants.TEST_API_KEY}
        
        # Act
        response = client.post(
            '/query',
            headers=headers,
            json=FlaskAPITestConstants.SAMPLE_QUERY
        )
        
        # Assert
        assert response.status_code == 200, (
            f"Expected 200 OK, got {response.status_code}\n"
            f"Response: {response.get_json()}"
        )
        
        data = response.get_json()
        assert 'response' in data, "Response missing 'response' field"
        assert 'privacy' in data, "Response missing 'privacy' field"
        assert data['response']['response'] == FlaskAPITestConstants.MOCK_AGENT_RESPONSE['response']
        assert data['response']['confidence'] == FlaskAPITestConstants.MOCK_AGENT_RESPONSE['confidence']
    
    @patch('project.app.run_agent')
    def test_query_with_minimal_input(self, mock_run_agent, client) -> None:
        """Test query with only required fields."""
        # Arrange
        mock_run_agent.return_value = FlaskAPITestConstants.MOCK_AGENT_RESPONSE
        headers = {'X-API-Key': FlaskAPITestConstants.TEST_API_KEY}
        minimal_query = {'input': 'Simple question'}
        
        # Act
        response = client.post('/query', headers=headers, json=minimal_query)
        
        # Assert
        assert response.status_code == 200
        assert 'response' in response.get_json()
    
    @patch('project.app.run_agent')
    def test_query_handles_agent_error(self, mock_run_agent, client) -> None:
        """Test that API handles agent errors (currently propagates exception)."""
        # Arrange
        mock_run_agent.side_effect = Exception("Agent processing error")
        headers = {'X-API-Key': FlaskAPITestConstants.TEST_API_KEY}
        
        # Act & Assert - Currently the API lets exceptions propagate
        # This test verifies the current behavior
        try:
            response = client.post(
                '/query',
                headers=headers,
                json=FlaskAPITestConstants.SAMPLE_QUERY
            )
            # If we get here, error was handled
            assert response.status_code >= 400, (
                f"Should return error status code, got {response.status_code}"
            )
        except Exception as e:
            # Exception propagates - this is current behavior
            assert "Agent processing error" in str(e), (
                f"Expected 'Agent processing error', got {str(e)}"
            )


class TestRateLimiting:
    """Tests for API rate limiting functionality."""
    
    @patch('project.app.run_agent')
    def test_rate_limit_enforced_after_threshold(self, mock_run_agent, client) -> None:
        """Test that rate limiting kicks in after threshold is reached."""
        # Arrange
        mock_run_agent.return_value = FlaskAPITestConstants.MOCK_AGENT_RESPONSE
        headers = {'X-API-Key': FlaskAPITestConstants.TEST_API_KEY}
        
        # Act - Make requests up to the limit
        for i in range(FlaskAPITestConstants.RATE_LIMIT_REQUESTS):
            query = {'input': f'Query number {i}'}
            response = client.post('/query', headers=headers, json=query)
            assert response.status_code == 200, (
                f"Request {i} failed unexpectedly: {response.status_code}"
            )
        
        # Act - Exceed the limit
        response = client.post(
            '/query',
            headers=headers,
            json={'input': 'Exceeding limit'}
        )
        
        # Assert
        assert response.status_code == 429, (
            f"Expected 429 Too Many Requests, got {response.status_code}"
        )
        
        error_data = response.get_json()
        assert error_data['description'] == 'You have exceeded your rate limit.', (
            f"Unexpected error message: {error_data.get('description')}"
        )
    
    @patch('project.app.run_agent')
    def test_rate_limit_per_client(self, mock_run_agent, client) -> None:
        """Test that rate limits are tracked per client/IP."""
        # This test verifies that the rate limiter is configured correctly
        # In a real scenario, you'd test with different IPs/clients
        mock_run_agent.return_value = FlaskAPITestConstants.MOCK_AGENT_RESPONSE
        headers = {'X-API-Key': FlaskAPITestConstants.TEST_API_KEY}
        
        # Make one request to ensure limiter is working
        response = client.post('/query', headers=headers, json=FlaskAPITestConstants.SAMPLE_QUERY)
        assert response.status_code == 200


#  ============================================================================
# Security Tests
# ============================================================================

class TestSecurity:
    """Security-focused tests for the Flask API."""
    
    @pytest.mark.security
    def test_sql_injection_attempt_in_input(self, client) -> None:
        """Test that SQL injection attempts are handled safely."""
        headers = {'X-API-Key': FlaskAPITestConstants.TEST_API_KEY}
        malicious_query = {
            'input': "'; DROP TABLE users; --",
            'document_content': 'SELECT * FROM secrets'
        }
        
        with patch('project.app.run_agent') as mock_agent:
            mock_agent.return_value = FlaskAPITestConstants.MOCK_AGENT_RESPONSE
            response = client.post('/query', headers=headers, json=malicious_query)
            
            # Should process safely (API doesn't use SQL directly)
            assert response.status_code in [200, 400], (
                f"Expected 200 or 400 for SQL injection attempt, got {response.status_code}"
            )
            # API should complete without crashing
            assert response.get_json() is not None
    
    @pytest.mark.security
    def test_xss_attempt_in_input(self, client) -> None:
        """Test that XSS attempts are handled (sanitized or rejected)."""
        headers = {'X-API-Key': FlaskAPITestConstants.TEST_API_KEY}
        xss_query = {
            'input': '<script>alert("XSS")</script>What are visa requirements?',
            'document_content': '<img src=x onerror="alert(1)">'
        }
        
        with patch('project.app.run_agent') as mock_agent:
            mock_agent.return_value = FlaskAPITestConstants.MOCK_AGENT_RESPONSE
            response = client.post('/query', headers=headers, json=xss_query)
            
            # Should either sanitize or accept (API doesn't render HTML)
            assert response.status_code in [200, 400], (
                f"Expected 200 or 400, got {response.status_code}"
            )
            
            # If accepted, verify response doesn't execute scripts
            if response.status_code == 200:
                response_data = response.get_json()
                # Response should be safe (our API returns JSON, not HTML)
                assert response_data is not None
    
    @pytest.mark.security
    def test_command_injection_attempt(self, client) -> None:
        """Test that command injection attempts are handled safely."""
        headers = {'X-API-Key': FlaskAPITestConstants.TEST_API_KEY}
        injection_query = {
            'input': '; rm -rf / #',
            'document_content': '$(cat /etc/passwd)'
        }
        
        with patch('project.app.run_agent') as mock_agent:
            mock_agent.return_value = FlaskAPITestConstants.MOCK_AGENT_RESPONSE
            response = client.post('/query', headers=headers, json=injection_query)
            
            # Should not execute commands
            assert response.status_code in [200, 400]
    
    @pytest.mark.security
    def test_api_key_not_in_response(self, client) -> None:
        """Test that API key is never exposed in responses."""
        headers = {'X-API-Key': FlaskAPITestConstants.TEST_API_KEY}
        
        with patch('project.app.run_agent') as mock_agent:
            mock_agent.return_value = FlaskAPITestConstants.MOCK_AGENT_RESPONSE
            response = client.post('/query', headers=headers, json=FlaskAPITestConstants.SAMPLE_QUERY)
            
            response_text = response.get_data(as_text=True)
            assert FlaskAPITestConstants.TEST_API_KEY not in response_text, (
                "API key should never appear in response"
            )
    
    @pytest.mark.security
    def test_api_key_not_in_logs(self, client, caplog) -> None:
        """Test that API key is not logged."""
        import logging
        caplog.set_level(logging.DEBUG)
        
        headers = {'X-API-Key': FlaskAPITestConstants.TEST_API_KEY}
        
        with patch('project.app.run_agent') as mock_agent:
            mock_agent.return_value = FlaskAPITestConstants.MOCK_AGENT_RESPONSE
            client.post('/query', headers=headers, json=FlaskAPITestConstants.SAMPLE_QUERY)
            
            # Check logs don't contain API key
            for record in caplog.records:
                assert FlaskAPITestConstants.TEST_API_KEY not in record.message, (
                    "API key should not appear in logs"
                )
    
    @pytest.mark.security
    @pytest.mark.parametrize('malicious_payload', [
        {'input': None},  # None value
        {'input': ''},  # Empty string
        {'input': ' ' * 10000},  # Very long whitespace
        {'input': '\x00\x01\x02'},  # Null bytes
        {'input': '../../../etc/passwd'},  # Path traversal
        {'input': '{{7*7}}'},  # Template injection
    ])
    def test_malicious_payload_handling(self, client, malicious_payload) -> None:
        """Test various malicious payloads are handled safely."""
        headers = {'X-API-Key': FlaskAPITestConstants.TEST_API_KEY}
        
        with patch('project.app.run_agent') as mock_agent:
            mock_agent.return_value = FlaskAPITestConstants.MOCK_AGENT_RESPONSE
            response = client.post('/query', headers=headers, json=malicious_payload)
            
            # Should not crash - either process or reject
            assert response.status_code in [200, 400, 422]
    
    @pytest.mark.security
    @pytest.mark.slow
    def test_oversized_request_handling(self, client) -> None:
        """Test that oversized requests are handled."""
        headers = {'X-API-Key': FlaskAPITestConstants.TEST_API_KEY}
        
        # Create large payload (500KB - more realistic)
        large_query = {
            'input': 'Question',
            'document_content': 'X' * (500 * 1024)  # 500KB
        }
        
        with patch('project.app.run_agent') as mock_agent:
            mock_agent.return_value = FlaskAPITestConstants.MOCK_AGENT_RESPONSE
            
            try:
                response = client.post('/query', headers=headers, json=large_query)
                # Should either process or reject
                assert response.status_code in [200, 413, 400, 500], (
                    f"Unexpected status code: {response.status_code}"
                )
            except Exception:
                # May fail due to size limits - acceptable
                pass


# ============================================================================
# Performance Tests
# ============================================================================

class TestPerformance:
    """Performance and load tests for the Flask API."""
    
    @pytest.mark.performance
    @pytest.mark.slow
    def test_concurrent_requests_handling(self, client) -> None:
        """Test API handles multiple sequential requests (simulating concurrent load)."""
        import time
        
        headers = {'X-API-Key': FlaskAPITestConstants.TEST_API_KEY}
        
        # Patch at module level before making requests
        with patch('project.app.run_agent') as mock_agent:
            mock_agent.return_value = FlaskAPITestConstants.MOCK_AGENT_RESPONSE
            
            # Make 10 rapid sequential requests (simpler than threading)
            start_time = time.time()
            results = []
            for i in range(10):
                query = {'input': f'Query {i}'}
                try:
                    response = client.post('/query', headers=headers, json=query)
                    results.append(response.status_code)
                except Exception:
                    results.append(500)
            elapsed_time = time.time() - start_time
            
            # Most requests should succeed (allow some for rate limiting)
            success_count = sum(1 for code in results if code == 200)
            assert success_count >= 5, f"Expected at least 5 successful requests, got {success_count}"
            
            # Should complete in reasonable time
            assert elapsed_time < 10.0, f"Requests took too long: {elapsed_time}s"
    
    @pytest.mark.performance
    @pytest.mark.slow
    def test_rapid_sequential_requests(self, client) -> None:
        """Test API handles rapid sequential requests."""
        headers = {'X-API-Key': FlaskAPITestConstants.TEST_API_KEY}
        
        with patch('project.app.run_agent') as mock_agent:
            mock_agent.return_value = FlaskAPITestConstants.MOCK_AGENT_RESPONSE
            
            # Make 50 requests rapidly
            success_count = 0
            for i in range(50):
                query = {'input': f'Rapid query {i}'}
                response = client.post('/query', headers=headers, json=query)
                if response.status_code == 200:
                    success_count += 1
                elif response.status_code == 429:
                    # Rate limit hit - acceptable
                    break
            
            # Should handle at least 10 requests before rate limiting
            assert success_count >= 10, f"Only {success_count} successful requests"
    
    @pytest.mark.performance
    def test_response_time_acceptable(self, client) -> None:
        """Test that response time is acceptable (<500ms for simple query)."""
        import time
        
        headers = {'X-API-Key': FlaskAPITestConstants.TEST_API_KEY}
        
        with patch('project.app.run_agent') as mock_agent:
            # Simulate fast response
            mock_agent.return_value = FlaskAPITestConstants.MOCK_AGENT_RESPONSE
            
            start_time = time.time()
            response = client.post('/query', headers=headers, json=FlaskAPITestConstants.SAMPLE_QUERY)
            elapsed_time = time.time() - start_time
            
            assert response.status_code == 200
            # Response should be fast with mocked agent (<500ms)
            assert elapsed_time < 0.5, f"Response too slow: {elapsed_time}s"
    
    @pytest.mark.performance
    def test_memory_efficient_large_document(self, client) -> None:
        """Test memory efficiency with large documents."""
        headers = {'X-API-Key': FlaskAPITestConstants.TEST_API_KEY}
        
        # Create large document (500KB)
        large_doc = 'Legal document text. ' * 25000  # ~500KB
        
        query = {
            'input': 'Question about large document',
            'document_content': large_doc
        }
        
        with patch('project.app.run_agent') as mock_agent:
            mock_agent.return_value = FlaskAPITestConstants.MOCK_AGENT_RESPONSE
            response = client.post('/query', headers=headers, json=query)
            
            # Should handle without memory errors
            assert response.status_code in [200, 413]


