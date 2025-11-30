from project.core.context_engineering import sanitize_input
class Planner:
    def plan(self, user_input, document_content=None, document_language='auto', preferred_language='en'):
        return {
            "tasks": [{
                "action": "process",
                "details": {
                    "user_input": sanitize_input(user_input),
                    "document": sanitize_input(document_content) if document_content else None,
                    "document_language": document_language,
                    "preferred_language": preferred_language
                }
            }]
        }
