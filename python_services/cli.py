import sys
from python_services.routing.intent_router import IntentRouter, Intent
from python_services.rag.rag_processor import RAGModule
from python_services.database_humanizer.db_processor import DBHumanizerModule
from python_services.calculator_humanizer.calc_processor import CalcHumanizerModule

class AssistantPipeline:
    def __init__(self):
        self.router = IntentRouter()
        # Initialize modules conditionally if needed, or eagerly
        self.rag_module = RAGModule()
        self.db_module = DBHumanizerModule()
        self.calc_module = CalcHumanizerModule()

    def handle_query(self, user_input: str) -> str:
        intent = self.router.route(user_input)
        
        if intent == Intent.RAG_QUERY:
            return self.rag_module.process(user_input)
        elif intent == Intent.DB_RESULT:
            return self.db_module.process(user_input)
        elif intent == Intent.CALC_RESULT:
            return self.calc_module.process(user_input)
        else:
            return "Error: Unknown intent router returned."

if __name__ == "__main__":
    assistant = AssistantPipeline()
    print("--- AI Financial Assistant Pipeline (3-Modules) ---")
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        print(f"\nResult: {assistant.handle_query(query)}")
    else:
        while True:
            try:
                user_input = input("\nEnter comma-separated keywords (or 'exit' to quit):\n> ")
                if user_input.lower() in ['quit', 'exit']:
                    print("Exiting...")
                    break
                if not user_input.strip():
                    continue
                print(f"Result: {assistant.handle_query(user_input)}")
            except KeyboardInterrupt:
                print("\nExiting...")
                break
##http://127.0.0.1:8000
