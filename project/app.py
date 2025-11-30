from flask import Flask, request, jsonify
from flask_httpauth import HTTPBasicAuth
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
import logging
from project.main_agent import run_agent
from project.core.context_engineering import PRIVACY_DISCLAIMER

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app():
    app = Flask(__name__)
    auth = HTTPBasicAuth()
    limiter = Limiter(app=app, key_func=get_remote_address, storage_uri='memory:///')

    @auth.verify_password
    def verify_password(username, password):
        api_key = request.headers.get('X-API-Key') or password
        if api_key and api_key == os.getenv('FLASK_API_KEY'):
            return username
        return None

    @app.route('/query', methods=['POST'])
    @auth.login_required
    @limiter.limit('10 per minute')
    def query():
        try:
            # Validate request data
            data = request.json
            if not data:
                return jsonify({
                    'error': 'Invalid request',
                    'detail': 'Request body must be JSON'
                }), 400
            
            user_input = data.get('input', '').strip()
            if not user_input:
                return jsonify({
                    'error': 'Invalid input',
                    'detail': 'User input cannot be empty'
                }), 400
            
            if len(user_input) > 10000:
                return jsonify({
                    'error': 'Input too long',
                    'detail': 'User input must be less than 10,000 characters'
                }), 400
            
            # Validate language parameters
            valid_languages = {'en', 'es', 'fr', 'nl', 'de', 'auto'}
            doc_lang = data.get('document_language', 'auto')
            pref_lang = data.get('preferred_language', 'en')
            
            if doc_lang not in valid_languages:
                return jsonify({
                    'error': 'Invalid language',
                    'detail': f'document_language must be one of: {valid_languages}'
                }), 400
            
            if pref_lang not in {'en', 'es', 'fr', 'nl', 'de'}:
                return jsonify({
                    'error': 'Invalid language',
                    'detail': 'preferred_language must be one of: en, es, fr, nl, de'
                }), 400
            
            # Process request
            agent_response = run_agent(
                user_input=user_input,
                document_content=data.get('document_content'),
                document_language=doc_lang,
                preferred_language=pref_lang
            )
            
            # Validate response
            if not agent_response or not isinstance(agent_response, dict):
                logger.error(f"Invalid agent response: {type(agent_response)}")
                return jsonify({
                    'error': 'Processing failed',
                    'detail': 'Agent returned invalid response'
                }), 500
            
            return jsonify({'response': agent_response, 'privacy': PRIVACY_DISCLAIMER})
            
        except ValueError as e:
            logger.warning(f"Validation error: {e}")
            return jsonify({
                'error': 'Invalid input',
                'detail': str(e)
            }), 400
        except KeyError as e:
            logger.warning(f"Missing required field: {e}")
            return jsonify({
                'error': 'Missing field',
                'detail': f'Required field missing: {e}'
            }), 400
        except TimeoutError as e:
            logger.error(f"Request timeout: {e}")
            return jsonify({
                'error': 'Request timeout',
                'detail': 'Processing took too long. Please try with a smaller document.'
            }), 504
        except Exception as e:
            logger.error(f"Unexpected error in /query: {e}", exc_info=True)
            return jsonify({
                'error': 'Internal server error',
                'detail': 'An unexpected error occurred. Please try again later.'
            }), 500

    @app.errorhandler(429)
    def ratelimit_handler(e):
        return jsonify({'code': 429, 'name': 'Rate Limit Exceeded', 'description': 'You have exceeded your rate limit.'}), 429

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000)
