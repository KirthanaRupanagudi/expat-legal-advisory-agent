import subprocess, sys, os

def test_e2e(monkeypatch):
    env = os.environ.copy()
    env['GOOGLE_API_KEY'] = 'fake_key_for_e2e'
    env['E2E_TEST_MODE'] = 'true'
    p = subprocess.run([sys.executable, 'project/run_demo.py'], capture_output=True, text=True, env=env)
    stdout = p.stdout # Use raw stdout for assertion
    # Check for specific debug messages and the mocked response
    assert "E2E_TEST_MODE is ON. Initializing mocked LLM." in stdout
    assert "Running agent..." in stdout
    assert "Mocked LLM response for Hello! This is a demo." in stdout
    assert "Agent run finished." in stdout
    assert p.returncode == 0, f"Subprocess failed with error: {p.stderr}"
