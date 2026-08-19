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

    MODELS = ["gemini-1.5-flash", "gemini-1.5-pro"]

    def __init__(self):
        if not settings.gemini_api_key:
            raise ValueError(
                "GEMINI_API_KEY is not set. "
                "Add it to your .env file to use Gemini."
            )
        import google.generativeai as genai
        genai.configure(api_key=settings.gemini_api_key)
        
        raw_models = []
        try:
            raw_models = [m.name.replace("models/", "") for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            logger.info(f"Available Gemini models: {raw_models}")
        except Exception as e:
            logger.warning(f"Could not list Gemini models: {e}")

        # Choose the first model in our preferred list that is available, or default to the first one
        selected_model = self.MODELS[0]
        if raw_models:
            for m in self.MODELS:
                if m in raw_models or f"models/{m}" in raw_models:
                    selected_model = m
                    break
        
        logger.info(f"Selected Gemini model: {selected_model}")
        
        self._genai = genai
        self._model = genai.GenerativeModel(
            model_name=selected_model,
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
            error_msg = str(e)
            if "429" in error_msg or "quota" in error_msg.lower():
                msg = "Gemini API quota exceeded. Please try again later or check your billing/tier limits."
                logger.error(msg)
                raise RuntimeError(msg) from e
            logger.error(f"Gemini API error: {e}")
            raise RuntimeError(f"Gemini API error: {e}") from e

    def get_embedding(self, text: str, task_type: str = "retrieval_document") -> list[float]:
        """Get text embedding via Gemini Embedding API (768 dimensions)."""
        try:
            result = self._genai.embed_content(
                model="models/text-embedding-004",
                content=text[:2048],
                task_type=task_type,
            )
            return result["embedding"]
        except Exception as e:
            err_str = str(e).lower()
            if "429" in str(e) or "quota" in err_str or "resource_exhausted" in err_str:
                raise RuntimeError("Gemini embedding quota exhausted.") from e
            raise RuntimeError(f"Gemini embedding error: {e}") from e

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
