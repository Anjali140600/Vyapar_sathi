from llm.tinyllama_client import TinyLlamaClient


class CalcHumanizerModule:
    def __init__(self):
        self.llm = TinyLlamaClient()

    def process(self, query: str) -> str:
        parts = [p.strip() for p in query.split(",") if p.strip()]

        if len(parts) < 2:
            return "Invalid input format."

        value = parts[-1]
        metric = " ".join(parts[:-1])

        system_instruction = """
You are a formatter.

Return ONLY one sentence.

Format:
The <metric> is <value>.

Do not explain anything.
Do not add extra text.
"""

        user_prompt = f"{metric},{value}"

        response = self.llm.generate_response(system_instruction, user_prompt)

        clean = " ".join(str(response).strip().split())

        # 🔥 HARD FILTER (critical)
        if len(clean.split()) > 12 or "rule" in clean.lower():
            clean = f"The {metric} is {format_number(value)}."

        return clean


def format_number(value):
    try:
        return f"{int(value):,}"
    except:
        return value