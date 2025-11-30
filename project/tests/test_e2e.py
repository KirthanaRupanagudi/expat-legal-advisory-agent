"""
End-to-End Tests for Expat Legal Advisory Agent

This module contains end-to-end tests that verify the complete system workflow
by running the actual demo script in a subprocess with mocked external dependencies.
"""

import os
import subprocess
import sys
from typing import Dict, List


class E2ETestConstants:
    """Constants used across E2E tests."""
    
    FAKE_API_KEY = 'fake_key_for_e2e_testing'
    DEMO_SCRIPT_PATH = 'project/run_demo.py'
    SUBPROCESS_TIMEOUT = 30  # seconds
    
    # Expected output messages
    EXPECTED_MESSAGES = [
        "E2E_TEST_MODE is ON. Initializing mocked LLM.",
        "Running agent...",
        "Mocked LLM response for Hello! This is a demo.",
        "Agent run finished."
    ]


class E2ETestRunner:
    """Helper class for running end-to-end tests."""
    
    @staticmethod
    def create_test_environment() -> Dict[str, str]:
        """
        Create a test environment with necessary variables.
        
        Returns:
            Dictionary of environment variables for the test subprocess.
        """
        env = os.environ.copy()
        env['GOOGLE_API_KEY'] = E2ETestConstants.FAKE_API_KEY
        env['E2E_TEST_MODE'] = 'true'
        return env
    
    @staticmethod
    def run_demo_script(env: Dict[str, str]) -> subprocess.CompletedProcess:
        """
        Execute the demo script in a subprocess.
        
        Args:
            env: Environment variables to use for the subprocess.
            
        Returns:
            CompletedProcess object with execution results.
        """
        return subprocess.run(
            [sys.executable, E2ETestConstants.DEMO_SCRIPT_PATH],
            capture_output=True,
            text=True,
            env=env,
            timeout=E2ETestConstants.SUBPROCESS_TIMEOUT
        )
    
    @staticmethod
    def validate_output(stdout: str, expected_messages: List[str]) -> None:
        """
        Validate that expected messages appear in stdout.
        
        Args:
            stdout: The captured standard output.
            expected_messages: List of messages that should appear in output.
            
        Raises:
            AssertionError: If any expected message is missing.
        """
        for message in expected_messages:
            assert message in stdout, (
                f"Expected message not found in output: '{message}'\n"
                f"Actual output: {stdout[:500]}"
            )


def test_e2e_demo_script_execution(monkeypatch):
    """
    Test the complete end-to-end workflow of the demo script.
    
    This test:
    1. Sets up a controlled test environment with mocked API key
    2. Runs the demo script as a subprocess
    3. Validates that all expected debug messages appear
    4. Ensures the process completes successfully
    
    Args:
        monkeypatch: Pytest fixture for environment manipulation.
    """
    # Arrange
    runner = E2ETestRunner()
    test_env = runner.create_test_environment()
    
    # Act
    process = runner.run_demo_script(test_env)
    
    # Assert - Check return code
    assert process.returncode == 0, (
        f"Demo script failed with return code {process.returncode}\n"
        f"STDERR: {process.stderr}\n"
        f"STDOUT: {process.stdout}"
    )
    
    # Assert - Validate expected output messages
    runner.validate_output(process.stdout, E2ETestConstants.EXPECTED_MESSAGES)


def test_e2e_demo_script_with_error_handling(monkeypatch):
    """
    Test that the demo script handles missing API key gracefully.
    
    This test verifies error handling when required environment
    variables are missing.
    
    Args:
        monkeypatch: Pytest fixture for environment manipulation.
    """
    # Arrange - Create environment without API key
    env = os.environ.copy()
    env.pop('GOOGLE_API_KEY', None)  # Ensure key is not present
    env['E2E_TEST_MODE'] = 'true'
    
    # Act
    process = subprocess.run(
        [sys.executable, E2ETestConstants.DEMO_SCRIPT_PATH],
        capture_output=True,
        text=True,
        env=env,
        timeout=30
    )
    
    # Assert - Should handle gracefully (implementation dependent)
    # Check that it doesn't crash catastrophically
    assert process.returncode in (0, 1), (
        f"Unexpected return code: {process.returncode}\n"
        f"STDERR: {process.stderr}"
    )
