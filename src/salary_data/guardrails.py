import re
import litellm
from typing import Tuple

class InputValidator:
    """
    Handles security and relevance filtering for user prompts.
    """
    def __init__(self, relevance_model: str = "ollama/llama3.2:1b"):
        self.relevance_model = relevance_model
        
        # Patterns for common prompt injection attempts
        self.injection_patterns = [
            r"ignore previous instructions",
            r"ignore all previous",
            r"forget everything",
            r"system prompt",
            r"new rules",
            r"you are now a",
            r"bypass",
            r"dan mode",
            r"jailbreak"
        ]

    def check_injection(self, text: str) -> bool:
        """Returns True if a potential prompt injection is detected."""
        text_lower = text.lower()
        for pattern in self.injection_patterns:
            if re.search(pattern, text_lower):
                return True
        return False

    def is_relevant(self, text: str) -> Tuple[bool, str]:
        """
        Uses a small local model to determine if the query is relevant 
        to Argentinian economics, salaries, or the dashboard.
        """
        clean_text = text.strip().lower()
        if len(clean_text) < 15 and any(word in clean_text for word in ["hello", "hola", "hi", "quien sos", "who are you"]):
            return True, "Greeting"

        prompt = f"""
        Determine if the user query is about Argentine teacher salaries, inflation, poverty, or provincial economic comparisons.
        
        VALID TOPICS (RELEVANT):
        - Salaries in specific provinces (e.g., "What is Chaco's salary?")
        - Purchasing power or inflation (e.g., "loss in Buenos Aires", "IPC growth")
        - Rankings (e.g., "top paying province")
        - Poverty or cost of living (CBT, CBA)
        
        INVALID TOPICS (IRRELEVANT):
        - Asking for songs, poems, or jokes.
        - General knowledge not about Argentina's economy.
        - Coding or math problems unrelated to the data.

        USER QUERY: "{text}"

        Respond with only one word: RELEVANT or IRRELEVANT.
        """
        
        try:
            response = litellm.completion(
                model=self.relevance_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=10 # Allow slight verbosity if needed
            )
            prediction = response.choices[0].message.content.strip().upper()
            
            # More robust check for the word RELEVANT
            if "RELEVANT" in prediction and "IRRELEVANT" not in prediction:
                return True, "RELEVANT"
            if "IRRELEVANT" in prediction:
                return False, "IRRELEVANT"
            
            # Default to True if the small model output is ambiguous but not explicitly IRRELEVANT
            return True, f"AMBIGUOUS_RECOVERY: {prediction}"
            
        except Exception as e:
            print(f"[GUARDRAILS ERROR] Relevance check failed: {e}")
            return True, "ERROR_FALLBACK"

    def validate(self, text: str) -> Tuple[bool, str]:
        """
        Full validation pipeline. Returns (is_valid, error_message).
        """
        if self.check_injection(text):
            return False, "⚠️ **Security alert:** Potential prompt injection detected. Please rephrase your question."
        
        relevant, reason = self.is_relevant(text)
        if not relevant:
            return False, "I'm sorry, I can only answer questions related to Argentinian teacher salaries and economic data."
            
        return True, ""
