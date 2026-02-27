from __future__ import annotations

import os

from ..providers import ProviderResult


class GeminiProvider:
    name = "gemini"

    def __init__(self) -> None:
        self._client = None

    @property
    def client(self):
        """Lazy initialization of Gemini client."""
        if self._client is None:
            from google import genai

            api_key = os.environ.get("GEMINI_API_KEY", "")
            self._client = genai.Client(api_key=api_key)
        return self._client

    def search(self, query: str, **kwargs: object) -> ProviderResult:
        try:
            from google.genai.types import GenerateContentConfig, GoogleSearch, Tool

            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=query,
                config=GenerateContentConfig(
                    tools=[Tool(google_search=GoogleSearch())],
                ),
            )

            content = ""
            sources: list[dict] = []

            if response.candidates and len(response.candidates) > 0:
                candidate = response.candidates[0]
                if candidate.content and candidate.content.parts:
                    content = "".join(
                        part.text for part in candidate.content.parts if part.text
                    )

                metadata = getattr(candidate, "grounding_metadata", None)
                if metadata:
                    chunks = getattr(metadata, "grounding_chunks", None) or []
                    for chunk in chunks:
                        web = getattr(chunk, "web", None)
                        if web:
                            sources.append(
                                {
                                    "title": getattr(web, "title", ""),
                                    "url": getattr(web, "uri", ""),
                                }
                            )

            return ProviderResult(
                provider=self.name,
                query=query,
                content=content,
                sources=sources,
            )
        except Exception as e:
            return ProviderResult(
                provider=self.name,
                query=query,
                content="",
                error=str(e),
            )
