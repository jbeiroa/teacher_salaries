import re
import litellm
from typing import Tuple

class InputValidator:
    """
    Handles security and relevance filtering for user prompts.
    """
    def __init__(self, relevance_model: str = "openai/gpt-4o-mini"):
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
        Determines if the query is relevant using heuristics first, then a small LLM.
        """
        clean_text = text.strip().lower()
        
        # 1. Expanded Heuristic Pass (Greetings & Identity)
        greetings = ["hello", "hola", "hi", "hey", "buenos dias", "buenas tardes"]
        identity = ["quien sos", "quién sos", "who are you", "tu nombre", "your name", "what are you", "que sos", "qué sos"]
        if any(word in clean_text for word in greetings + identity):
            return True, "Greeting/Identity"

        # 2. Data Keyword "Fast Pass" (Spanish & English)
        # Includes all Argentinian provinces and key economic terms
        provinces = [
            "buenos aires", "caba", "catamarca", "chaco", "chubut", "cordoba", "corrientes", 
            "entre rios", "formosa", "jujuy", "la pampa", "la rioja", "mendoza", "misiones", 
            "neuquen", "rio negro", "salta", "san juan", "san luis", "santa cruz", "santa fe", 
            "santiago del estero", "tierra del fuego", "tucuman"
        ]
        keywords = [
            "salario", "sueldo", "cobran", "pagan", "ganan", "salary", "pay", "earn",
            "inflacion", "inflation", "ipc", "cpi", "canasta", "pobreza", "poverty",
            "ranking", "top", "bottom", "peores", "mejores", "loss", "perdimos", "ganamos",
            "poder adquisitivo", "purchasing power", "evolucion", "evolution"
        ]
        
        if any(prov in clean_text for prov in provinces) or any(key in clean_text for key in keywords):
            return True, "Heuristic_Match"

        # 3. LLM Fallback for ambiguous cases
        prompt = f"""
        Determine if the user query is about Argentine economy, teacher salaries, or provincial data.
        Relevant topics include: salaries, inflation, poverty, rankings, and economic comparisons in Argentina.
        User Query: "{text}"
        Respond with ONLY 'RELEVANT' or 'IRRELEVANT'.
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
