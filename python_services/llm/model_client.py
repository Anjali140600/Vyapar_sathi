import json
import logging
import os
import re
from typing import Any

from dotenv import load_dotenv


load_dotenv()

logger = logging.getLogger(__name__)


class ModelClient:
    """LLM client whose provider is selected through environment configuration."""

    SUPPORTED_PROVIDERS = {"groq", "ollama"}

    def __init__(self):
        self.provider = os.getenv("LLM_PROVIDER", "groq").strip().lower()
        if self.provider not in self.SUPPORTED_PROVIDERS:
            supported = ", ".join(sorted(self.SUPPORTED_PROVIDERS))
            raise ValueError(
                f"Unsupported LLM_PROVIDER '{self.provider}'. Choose one of: {supported}."
            )

        self.model_name: str
        self.llm: Any

        if self.provider == "groq":
            self._configure_groq()
        else:
            self._configure_ollama()

    def _configure_groq(self) -> None:
        api_key = os.getenv("GROQ_API_KEY", "").strip()
        if not api_key or api_key == "your_groq_api_key_here":
            raise RuntimeError(
                "LLM_PROVIDER is set to 'groq', but GROQ_API_KEY is missing. "
                "Add GROQ_API_KEY to the .env file or your hosting provider's secrets."
            )

        from groq import Groq

        self.model_name = os.getenv(
            "GROQ_MODEL", "openai/gpt-oss-20b"
        ).strip()
        self.llm = Groq(api_key=api_key)

    def _configure_ollama(self) -> None:
        from langchain_ollama import OllamaLLM

        # PRIMARY_LLM_MODEL is retained as a fallback for older local .env files.
        self.model_name = os.getenv(
            "OLLAMA_MODEL", os.getenv("PRIMARY_LLM_MODEL", "tinyllama")
        ).strip()
        self.llm = OllamaLLM(model=self.model_name, temperature=0.0)

    def _clean_output(self, text: str) -> str:
        """Clean output while allowing multi-line responses."""
        clean = str(text or "").strip()

        prefixes = ["answer:", "response:", "assistant:"]
        for prefix in prefixes:
            if clean.lower().startswith(prefix):
                clean = clean[len(prefix):].strip()

        return clean

    def _enforce_limits(
        self, text: str, max_lines: int = 1, max_words: int = 30
    ) -> str:
        clean = " ".join((text or "").strip().split())
        if not clean:
            return ""

        words = clean.split()
        if len(words) > max_words:
            clean = " ".join(words[:max_words]).rstrip(",;:") + "."

        if max_lines <= 1:
            return clean

        sentences = [
            part.strip()
            for part in re.split(r"(?<=[.!?])\s+", clean.replace("\n", " "))
            if part.strip()
        ]
        limited = sentences[:max_lines]
        return "\n".join(
            sentence if sentence.endswith((".", "!", "?")) else f"{sentence}."
            for sentence in limited
        )

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
        try:
            if self.provider == "groq":
                completion = self.llm.chat.completions.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0,
                )
                content = completion.choices[0].message.content
            else:
                content = self.llm.invoke(prompt)

            return self._clean_output(content)
        except Exception as exc:
            logger.error("%s LLM request failed: %s", self.provider, exc)
            return ""

    def generate(
        self, prompt: str, max_lines: int = 3, max_words: int = 60
    ) -> str:
        """Generate an answer for the RAG module."""
        clean = self._invoke(prompt)
        return self._enforce_limits(
            clean, max_lines=max_lines, max_words=max_words
        )

    def generate_response(
        self,
        system_instruction: str,
        user_prompt: str,
        max_lines: int = 1,
        max_words: int = 30,
    ) -> str:
        """Generate a concise answer for the database and calculator modules."""
        full_prompt = f"""
{system_instruction}

User Input:
{user_prompt}

Return ONLY {max_lines} short line(s). Keep it factual and concise.
"""
        clean = self._invoke(full_prompt)
        return self._enforce_limits(
            clean, max_lines=max_lines, max_words=max_words
        )

    def generate_general_response(
        self, user_prompt: str, max_lines: int = 3, max_words: int = 60
    ) -> str:
        """Generate an answer for open-ended general questions."""
        prompt = f"""
You are a helpful assistant.

Answer the user's question directly in simple, practical language.
Keep the answer factual and concise.
Return at most {max_lines} short line(s).

User Question:
{user_prompt}
"""
        clean = self._invoke(prompt)
        return self._enforce_limits(
            clean, max_lines=max_lines, max_words=max_words
        )

    def generate_rag_response(
        self,
        user_question: str,
        context_chunks: list[str],
        max_lines: int = 3,
        max_words: int = 90,
    ) -> str:
        """Answer a question using only passages retrieved from the knowledge base."""
        context = "\n\n".join(
            f"Passage {index}: {chunk}"
            for index, chunk in enumerate(context_chunks, start=1)
            if chunk and chunk.strip()
        )
        if not context:
            return "I could not find a matching answer in the GST knowledge base."

        prompt = f"""
You are a GST knowledge-base assistant.

Answer the question using ONLY the retrieved passages below.
Do not use outside knowledge and do not guess a tax rate.
Distinguish goods from transport or other services.
Preserve important conditions such as fresh, UHT, pre-packaged, labelled, or exempt.
If the passages do not directly answer the question, reply exactly:
I could not find a matching answer in the GST knowledge base.
Return at most {max_lines} short lines.

Question:
{user_question}

Retrieved passages:
{context}
"""
        clean = self._invoke(prompt)
        return self._enforce_limits(
            clean, max_lines=max_lines, max_words=max_words
        )

    def generate_json(self, prompt: str) -> dict[str, Any] | None:
        """Generate and parse one JSON object, returning None on any failure."""
        raw = self._invoke(prompt)
        if not raw:
            return None

        clean = raw.strip()
        if clean.startswith("```"):
            clean = re.sub(r"^```(?:json)?\s*", "", clean, flags=re.IGNORECASE)
            clean = re.sub(r"\s*```$", "", clean)

        try:
            parsed = json.loads(clean)
        except (json.JSONDecodeError, TypeError):
            start = clean.find("{")
            end = clean.rfind("}")
            if start < 0 or end <= start:
                return None
            try:
                parsed = json.loads(clean[start : end + 1])
            except (json.JSONDecodeError, TypeError):
                return None

        return parsed if isinstance(parsed, dict) else None
