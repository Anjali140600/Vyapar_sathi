"""Backward-compatible import for code that still uses the old client name."""

from python_services.llm.model_client import ModelClient


TinyLlamaClient = ModelClient
