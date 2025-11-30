import os
import sys
from unittest.mock import patch

print("DEBUG: Starting run_demo.py script", flush=True)

if __name__ == '__main__':
    print("DEBUG: Inside __main__ block.", flush=True)
    if os.getenv('E2E_TEST_MODE') == 'true':
        print("DEBUG: E2E_TEST_MODE is ON. Applying mock.", flush=True)
        try:
            # The patch needs to wrap the execution of run_agent
            with patch('project.tools.tools.GeminiLLM') as MockGeminiLLM: # Patch the actual class used by Worker
                mock = MockGeminiLLM.return_value
                mock.generate_response.return_value = 'Mocked LLM response for Hello! This is a demo.'
                print("DEBUG: GeminiLLM mocked.", flush=True)
                from project.main_agent import run_agent # Import here to ensure it uses the patched GeminiLLM when instantiated
                print("Running agent...", flush=True)
                result = run_agent('Hello! This is a demo.')
                print("DEBUG: Agent run completed.", flush=True)
                print(result.get('response', 'Error: No response key in agent output.'), flush=True)
                print("Agent run finished.", flush=True)
        except Exception as e:
            print(f"ERROR DURING MOCKED AGENT EXECUTION: {e}", file=sys.stderr, flush=True)
            sys.exit(1)
    else:
        print("DEBUG: E2E_TEST_MODE is OFF. Running real agent.", flush=True)
        from project.main_agent import run_agent
        print("Running agent...", flush=True)
        try:
            result = run_agent('Hello! This is a demo.')
            print("DEBUG: Agent run completed.", flush=True)
            print(result.get('response', 'Error: No response key in agent output.'), flush=True)
            print("Agent run finished.", flush=True)
        except Exception as e:
            print(f"ERROR DURING REAL AGENT EXECUTION: {e}", file=sys.stderr, flush=True)
            sys.exit(1)

print("DEBUG: End of run_demo.py script.", flush=True)
