from __future__ import annotations

import os
import re

import httpx

from ..providers import ProviderResult


class GrokProvider:
    name = "grok"

    def __init__(self) -> None:
        self._api_key: str | None = None

    @property
    def api_key(self) -> str:
        if self._api_key is None:
            self._api_key = os.environ.get("XAI_API_KEY", "")
        return self._api_key

    def search(self, query: str, **kwargs: object) -> ProviderResult:
        try:
            reframed = f"What are people saying on X/Twitter about: {query}"

            resp = httpx.post(
                "https://api.x.ai/v1/responses",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
                json={
                    "model": "grok-4-1-fast-non-reasoning",
                    "input": [{"role": "user", "content": reframed}],
                    "tools": [{"type": "x_search"}],
                },
                timeout=90.0,
            )
            resp.raise_for_status()
            data = resp.json()

            # Extract text from output items
            content = ""
            for item in data.get("output", []):
                if item.get("type") == "message":
                    for part in item.get("content", []):
                        if part.get("type") == "output_text":
                            content += part.get("text", "")

            # Extract x.com / twitter.com URLs from response text
            url_pattern = r"https?://(?:x\.com|twitter\.com)/[^\s\)\]\"'>]+"
            urls = re.findall(url_pattern, content)
            sources = [{"title": "X post", "url": url} for url in urls]

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
