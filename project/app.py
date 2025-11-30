from flask import Flask, request, jsonify
from flask_httpauth import HTTPBasicAuth
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
from project.main_agent import run_agent
from project.core.context_engineering import PRIVACY_DISCLAIMER


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
        data = request.json or {}
        agent_response = run_agent(data.get('input', ''), data.get('document_content'))
        return jsonify({'response': agent_response, 'privacy': PRIVACY_DISCLAIMER})

    @app.errorhandler(429)
    def ratelimit_handler(e):
        return jsonify({'code': 429, 'name': 'Rate Limit Exceeded', 'description': 'You have exceeded your rate limit.'}), 429

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000)
