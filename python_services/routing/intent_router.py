from enum import Enum

class Intent(Enum):
    RAG_QUERY = 1
    DB_RESULT = 2
    CALC_RESULT = 3

class IntentRouter:
    def __init__(self):
        # We classify based on the rules provided in the prompt:
        self.db_keywords = ["total amount", "gst amount", "invoice count", "unpaid balance", "customer balance"]
        self.calc_keywords = ["profit", "loss", "margin", "tax total", "net profit"]

    def route(self, input_text: str) -> Intent:
        parts = [p.strip().lower() for p in input_text.split(",")]
        
        if not parts:
            return Intent.RAG_QUERY

        first_part = parts[0]
        
        # Check if it matches a DB label
        if any(db_kw in first_part for db_kw in self.db_keywords):
            return Intent.DB_RESULT
            
        # Check if it matches a Calculate Metric
        if any(calc_kw in first_part for calc_kw in self.calc_keywords):
            return Intent.CALC_RESULT
            
        # Default to RAG knowledge base
        return Intent.RAG_QUERY
