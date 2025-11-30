"""
Comprehensive Test Runner for Expat Legal Advisory Agent

This script runs all test suites and provides a unified summary report.
It can be run directly or imported for programmatic test execution.

Usage:
    python project/tests/run_all_tests.py
    python project/tests/run_all_tests.py --verbose
    python project/tests/run_all_tests.py --coverage
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import List, Tuple
import time


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


class TestRunner:
    """Orchestrates execution of all test suites."""
    
    def __init__(self, verbose: bool = False, coverage: bool = False):
        self.verbose = verbose
        self.coverage = coverage
        self.project_root = Path(__file__).parent.parent.parent
        self.test_dir = self.project_root / 'project' / 'tests'
        self.results = []
        self.python_exe = sys.executable
    
    def print_header(self):
        """Print test runner header."""
        print(f"\n{Colors.BOLD}{'=' * 70}")
        print("🧪 Expat Legal Advisory Agent - Test Suite Runner")
        print(f"{'=' * 70}{Colors.END}\n")
        print(f"Python: {self.python_exe}")
        print(f"Working Directory: {self.project_root}")
        print(f"Test Directory: {self.test_dir}\n")
    
    def run_smoke_tests(self) -> Tuple[bool, str]:
        """Run smoke tests."""
        print(f"\n{Colors.BLUE}{Colors.BOLD}► Running Smoke Tests...{Colors.END}")
        
        env = os.environ.copy()
        env['PYTHONPATH'] = str(self.project_root)
        
        try:
            result = subprocess.run(
                [self.python_exe, str(self.test_dir / 'smoke_test.py')],
                capture_output=True,
                text=True,
                env=env,
                timeout=60
            )
            
            success = result.returncode == 0
            output = result.stdout if success else result.stderr
            
            return success, output
        except subprocess.TimeoutExpired:
            return False, "Smoke tests timed out after 60 seconds"
        except Exception as e:
            return False, f"Error running smoke tests: {str(e)}"
    
    def run_pytest_suite(self, test_file: str, suite_name: str) -> Tuple[bool, str]:
        """
        Run a pytest test suite.
        
        Args:
            test_file: Name of the test file (e.g., 'test_unit.py')
            suite_name: Human-readable suite name
            
        Returns:
            Tuple of (success, output)
        """
        print(f"\n{Colors.BLUE}{Colors.BOLD}► Running {suite_name}...{Colors.END}")
        
        test_path = self.test_dir / test_file
        
        if not test_path.exists():
            return False, f"Test file not found: {test_path}"
        
        cmd = [self.python_exe, '-m', 'pytest', str(test_path), '-v']
        
        if self.coverage:
            cmd.extend(['--cov=project', '--cov-report=term-missing'])
        
        env = os.environ.copy()
        env['PYTHONPATH'] = str(self.project_root)
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=env,
                timeout=120,
                cwd=str(self.project_root)
            )
            
            success = result.returncode == 0
            output = result.stdout + ("\n" + result.stderr if result.stderr else "")
            
            return success, output
        except subprocess.TimeoutExpired:
            return False, f"{suite_name} timed out after 120 seconds"
        except Exception as e:
            return False, f"Error running {suite_name}: {str(e)}"
    
    def run_all_tests(self):
        """Execute all test suites in sequence."""
        start_time = time.time()
        
        self.print_header()
        
        # Define test suites
        test_suites = [
            ('smoke_tests', 'Smoke Tests', self.run_smoke_tests),
            ('test_unit.py', 'Unit Tests', lambda: self.run_pytest_suite('test_unit.py', 'Unit Tests')),
            ('test_integration.py', 'Integration Tests', lambda: self.run_pytest_suite('test_integration.py', 'Integration Tests')),
            ('test_app.py', 'Flask API Tests', lambda: self.run_pytest_suite('test_app.py', 'Flask API Tests')),
            ('test_e2e.py', 'End-to-End Tests', lambda: self.run_pytest_suite('test_e2e.py', 'End-to-End Tests')),
        ]
        
        # Run each test suite
        for suite_id, suite_name, runner_func in test_suites:
            success, output = runner_func()
            self.results.append((suite_name, success, output))
            
            # Print summary for this suite
            if success:
                print(f"{Colors.GREEN}✅ {suite_name} PASSED{Colors.END}")
            else:
                print(f"{Colors.RED}❌ {suite_name} FAILED{Colors.END}")
            
            # Print output if verbose or if failed
            if self.verbose or not success:
                print(f"\n{Colors.BOLD}Output:{Colors.END}")
                print(output[:2000])  # Limit output to avoid overflow
                if len(output) > 2000:
                    print(f"\n... (output truncated, {len(output)} total characters)")
        
        # Print final summary
        elapsed_time = time.time() - start_time
        self.print_summary(elapsed_time)
    
    def print_summary(self, elapsed_time: float):
        """Print final test summary."""
        print(f"\n{Colors.BOLD}{'=' * 70}")
        print("📊 Test Execution Summary")
        print(f"{'=' * 70}{Colors.END}\n")
        
        passed = sum(1 for _, success, _ in self.results if success)
        total = len(self.results)
        
        for suite_name, success, _ in self.results:
            status = f"{Colors.GREEN}✅ PASS{Colors.END}" if success else f"{Colors.RED}❌ FAIL{Colors.END}"
            print(f"  {status}: {suite_name}")
        
        print(f"\n{Colors.BOLD}{'-' * 70}{Colors.END}")
        print(f"  Total Suites: {total}")
        print(f"  Passed: {Colors.GREEN}{passed}{Colors.END}")
        print(f"  Failed: {Colors.RED}{total - passed}{Colors.END}")
        print(f"  Time Elapsed: {elapsed_time:.2f}s")
        print(f"{Colors.BOLD}{'=' * 70}{Colors.END}\n")
        
        if passed == total:
            print(f"{Colors.GREEN}{Colors.BOLD}🎉 All test suites passed!{Colors.END}\n")
            return 0
        else:
            print(f"{Colors.RED}{Colors.BOLD}⚠️  {total - passed} test suite(s) failed.{Colors.END}\n")
            return 1


def main():
    """Main entry point for the test runner."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Run all test suites for the Expat Legal Advisory Agent'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show detailed output for all tests'
    )
    parser.add_argument(
        '--coverage', '-c',
        action='store_true',
        help='Generate code coverage report'
    )
    
    args = parser.parse_args()
    
    # Set PYTHONPATH
    project_root = Path(__file__).parent.parent.parent
    os.environ['PYTHONPATH'] = str(project_root)
    
    runner = TestRunner(verbose=args.verbose, coverage=args.coverage)
    exit_code = runner.run_all_tests()
    
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
