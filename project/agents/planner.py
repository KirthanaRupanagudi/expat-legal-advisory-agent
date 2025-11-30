from typing import Dict, List, Any, Optional
from project.core.context_engineering import sanitize_input


class Planner:
    """Plans tasks for the agent workflow."""
    
    def plan(
        self,
        user_input: str,
        document_content: Optional[str] = None,
        document_language: str = 'auto',
        preferred_language: str = 'en'
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Create a task plan for processing user input.
        
        Args:
            user_input: User's question or input text
            document_content: Optional document content to analyze
            document_language: Language of the document ('auto' for detection)
            preferred_language: Language for response
            
        Returns:
            Dictionary containing list of tasks with action and details
        """
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
