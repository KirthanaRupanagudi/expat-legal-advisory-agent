# project/agents/evaluator.py
import re
from typing import Dict, Union


class Evaluator:
    """Evaluates and polishes agent responses."""
    
    def _estimate_confidence(self, text: Union[str, None]) -> float:
        """
        Estimate confidence score based on response characteristics.
        
        Args:
            text: Response text to evaluate
            
        Returns:
            Confidence score between 0 and 1
        """
        txt = str(text or '')
        if not txt.strip() or len(txt.strip()) < 20:
            return 0.55
        if len(txt) > 500:
            return 0.92
        if 'keyword' in txt.lower() or 'found' in txt.lower():
            return 0.88
        return 0.80

    def _polish_text(self, raw: Union[str, None]) -> str:
        """
        Polish and format raw response text.
        
        Args:
            raw: Raw response text from agent
            
        Returns:
            Polished, formatted response text
        """
        if not raw:
            return 'I could not generate a meaningful answer based on the provided information.'
        cleaned = re.sub(r'(?i)validated response: ?', '', str(raw)).strip()
        cleaned = cleaned.replace('Document processed.', 'After reviewing your document,')
        if not cleaned.lower().startswith(('here', 'after', 'based', 'i')):
            cleaned = "Here is my assessment: " + cleaned
        return cleaned

    def evaluate(self, result: Union[str, None]) -> Dict[str, Union[str, float]]:
        """
        Evaluate and polish the agent result.
        
        Args:
            result: Raw result from worker agent
            
        Returns:
            Dictionary with 'response' and 'confidence' keys
        """
        return {
            'response': self._polish_text(result),
            'confidence': round(self._estimate_confidence(result), 2)
        }
