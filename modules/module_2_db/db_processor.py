from llm.tinyllama_client import TinyLlamaClient


class DBHumanizerModule:
    def __init__(self):
        self.llm = TinyLlamaClient()

    def process(self, db_input: str) -> str:
        """
        Supports inputs like:
        total amount,21000
        total,amount,invoice,monthly,21000
        """

        # Step 1: split input
        parts = [p.strip() for p in db_input.split(",") if p.strip()]

        if len(parts) < 2:
            return "Invalid input format. Use: field,value"

        # Step 2: last value = actual value
        value = parts[-1]

        # Step 3: remaining = field description (supports up to 5 parts)
        field = " ".join(parts[:-1])

        # Step 4: prompt
        system_instruction = """
You are a database result formatter.

Your task:
Convert the given field and value into one simple human-readable sentence.

RULES:
- One line only
- No extra explanation
- Do not repeat words
- Format numbers with commas
- Keep it clean and professional
"""

        user_prompt = f"""
Field: {field}
Value: {value}

Return ONLY the final sentence.

Example:
The total amount is 21,000.
"""

        # Step 5: generate response
        response = self.llm.generate_response(system_instruction, user_prompt)

        # Step 6: clean output
        clean_ans = " ".join(str(response).strip().split())

        # Step 7: enforce fallback (very important)
        if not clean_ans.lower().startswith("the"):
            clean_ans = f"The {field} is {format_number(value)}."

        return clean_ans


# Utility function for formatting numbers
def format_number(value):
    try:
        if "." in value:
            return f"{float(value):,.2f}"
        else:
            return f"{int(value):,}"
    except:
        return value