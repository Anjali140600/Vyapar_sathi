import os
import re

from dotenv import load_dotenv
from langchain_ollama import OllamaLLM

load_dotenv()


class TinyLlamaClient:
    def __init__(self):
        self.primary_model_name = os.getenv("PRIMARY_LLM_MODEL", "tinyllama")

        self.llm = OllamaLLM(
            model=self.primary_model_name,
            temperature=0.0
        )

    def _clean_output(self, text: str) -> str:
        """
        Clean output while allowing multi-line responses.
        """
        clean = str(text).strip()

        # Remove common local model prefixes
        prefixes = ["answer:", "response:", "assistant:"]
        for p in prefixes:
            if clean.lower().startswith(p):
                clean = clean[len(p):].strip()

        return clean

    def _enforce_limits(self, text: str, max_lines: int = 1, max_words: int = 30) -> str:
        clean = " ".join((text or "").strip().split())
        if not clean:
            return ""

        words = clean.split()
        if len(words) > max_words:
            clean = " ".join(words[:max_words]).rstrip(",;:") + "."

        if max_lines <= 1:
            return clean

        sentences = [part.strip() for part in clean.replace("\n", " ").split(".") if part.strip()]
        limited = sentences[:max_lines]
        return "\n".join(f"{sentence}." for sentence in limited)

    def _looks_weak(self, text: str) -> bool:
        clean = " ".join((text or "").strip().split())
        if not clean:
            return True

        lower = clean.lower()
        weak_patterns = [
            r"\bi do not know\b",
            r"\bi don't know\b",
            r"\bnot sure\b",
            r"\bcannot answer\b",
            r"\bcan't answer\b",
            r"\bno idea\b",
            r"\bas an ai\b",
            r"\bi am just\b",
            r"\bsorry\b",
            r"\bunknown\b",
            r"\bn/a\b",
            r"^\.\\.?$",
        ]
        if any(re.search(pattern, lower) for pattern in weak_patterns):
            return True

        words = clean.split()
        if len(words) <= 2:
            return True

        if len(set(word.lower() for word in words)) == 1 and len(words) > 1:
            return True

        return False

    def _invoke(self, prompt: str) -> str:
        """Invoke TinyLlama via Ollama and return cleaned output."""
        try:
            return self._clean_output(self.llm.invoke(prompt))
        except Exception:
            return ""

    def generate(self, prompt: str, max_lines: int = 3, max_words: int = 60) -> str:
        """
        Used by RAG module.
        """
        clean = self._invoke(prompt)
        return self._enforce_limits(clean, max_lines=max_lines, max_words=max_words)

    def generate_response(self, system_instruction: str, user_prompt: str, max_lines: int = 1, max_words: int = 30) -> str:
        """
        Used by DB and CALC modules.
        """
        full_prompt = f"""
{system_instruction}

User Input:
{user_prompt}

Return ONLY {max_lines} short line(s). Keep it factual and concise.
"""
        clean = self._invoke(full_prompt)
        return self._enforce_limits(clean, max_lines=max_lines, max_words=max_words)

    def generate_general_response(self, user_prompt: str, max_lines: int = 3, max_words: int = 60) -> str:
        """
        Used for open-ended general questions.
        """
        prompt = f"""
You are a helpful assistant.

Answer the user's question directly in simple, practical language.
Keep the answer factual and concise.
Return at most {max_lines} short line(s).

User Question:
{user_prompt}
"""
        clean = self._invoke(prompt)
        return self._enforce_limits(clean, max_lines=max_lines, max_words=max_words)
