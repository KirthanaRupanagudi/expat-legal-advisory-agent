import os
import sys
import logging
from unittest.mock import patch

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    logger.info("Starting run_demo.py")
    
    if os.getenv('E2E_TEST_MODE') == 'true':
        logger.info("E2E_TEST_MODE enabled - using mocked LLM")
        try:
            with patch('project.tools.tools.GeminiLLM') as MockGeminiLLM:
                mock = MockGeminiLLM.return_value
                mock.generate_response.return_value = 'Mocked LLM response for Hello! This is a demo.'
                
                from project.main_agent import run_agent
                logger.info("Running agent with mocked LLM...")
                result = run_agent('Hello! This is a demo.')
                logger.info("Agent execution completed successfully")
                
                print(result.get('response', 'Error: No response key in agent output.'), flush=True)
                print("Agent run finished.", flush=True)
        except Exception as e:
            logger.error(f"Error during mocked agent execution: {e}", exc_info=True)
            sys.exit(1)
    else:
        logger.info("Running agent in normal mode")
        try:
            from project.main_agent import run_agent
            logger.info("Executing agent...")
            result = run_agent('Hello! This is a demo.')
            logger.info("Agent execution completed successfully")
            
            print(result.get('response', 'Error: No response key in agent output.'), flush=True)
            print("Agent run finished.", flush=True)
        except Exception as e:
            logger.error(f"Error during agent execution: {e}", exc_info=True)
            sys.exit(1)
    
    logger.info("run_demo.py completed")
