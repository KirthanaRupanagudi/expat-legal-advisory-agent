# project/main_agent.py
from project.agents.planner import Planner
from project.agents.worker import Worker
from project.agents.evaluator import Evaluator
from project.core.context_engineering import PRIVACY_DISCLAIMER
from project.core.observability import Observability
from project.core.a2a_protocol import create_message
from project.memory.session_memory import SessionMemory

class MainAgent:
    def __init__(self):
        self.planner = Planner()
        self.worker = Worker()
        self.evaluator = Evaluator()
        self.memory = SessionMemory()

    def handle_message(self, user_input, document_content=None, document_language='auto', preferred_language='en'):
        Observability.log('start', {'input_len': len(str(user_input))}, contains_pii=True)
        plan = self.planner.plan(user_input, document_content, document_language, preferred_language)
        task = plan["tasks"][0]
        msg = create_message('planner', 'worker', task)
        Observability.log('a2a_msg', {'id': msg['task_id'], 'from': msg['sender'], 'to': msg['receiver']})
        result = self.worker.execute(task)
        msg2 = create_message('worker', 'evaluator', {'result_preview': str(result)[:60]})
        Observability.log('a2a_msg', {'id': msg2['task_id'], 'from': msg2['sender'], 'to': msg2['receiver']})
        eval_result = self.evaluator.evaluate(result)
        eval_result['response'] = f"{eval_result.get('response','')}\n\n{PRIVACY_DISCLAIMER}"
        self.memory.store('last_question', user_input)
        self.memory.store('last_response', eval_result['response'])
        Observability.log('end', {'confidence': eval_result['confidence']})
        return eval_result

def run_agent(user_input, document_content=None, document_language='auto', preferred_language='en'):
    return MainAgent().handle_message(user_input, document_content, document_language, preferred_language)
