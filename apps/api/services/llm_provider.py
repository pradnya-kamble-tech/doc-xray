"""
LLM Provider abstraction for Doc-XRay.

Abstract base class: LLMProvider
Concrete implementations:
  - GeminiProvider (default)
  - OpenAIProvider (fallback)

Selected by LLM_PROVIDER environment variable.
"""
from __future__ import annotations
import logging
from abc import ABC, abstractmethod
from typing import Optional

from config import settings

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Abstract base class for all LLM providers."""

    @abstractmethod
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        """
        Send a prompt to the LLM and return the text response.
        Raises ValueError if API key is missing.
        Raises RuntimeError on API errors.
        """
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...


class GeminiProvider(LLMProvider):
    """Google Gemini API provider."""

    MODEL = "gemini-1.5-flash"

    def __init__(self):
        if not settings.gemini_api_key:
            raise ValueError(
                "GEMINI_API_KEY is not set. "
                "Add it to your .env file to use Gemini."
            )
        import google.generativeai as genai
        genai.configure(api_key=settings.gemini_api_key)
        self._model = genai.GenerativeModel(
            model_name=self.MODEL,
            safety_settings=[
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]
        )

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        try:
            response = self._model.generate_content(full_prompt)
            return response.text
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise RuntimeError(f"Gemini API error: {e}") from e

    @property
    def provider_name(self) -> str:
        return "gemini"


class OpenAIProvider(LLMProvider):
    """OpenAI API provider (fallback)."""

    MODEL = "gpt-4o-mini"

    def __init__(self):
        if not settings.openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY is not set. "
                "Add it to your .env file to use OpenAI."
            )
        from openai import OpenAI
        self._client = OpenAI(api_key=settings.openai_api_key)

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        try:
            response = self._client.chat.completions.create(
                model=self.MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=1024,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise RuntimeError(f"OpenAI API error: {e}") from e

    @property
    def provider_name(self) -> str:
        return "openai"


def get_llm_provider() -> LLMProvider:
    """Factory: select provider based on LLM_PROVIDER env var."""
    provider = settings.llm_provider.lower().strip()
    if provider == "gemini":
        return GeminiProvider()
    elif provider == "openai":
        return OpenAIProvider()
    else:
        # Default to Gemini
        return GeminiProvider()
