import json
from typing import Any

from agno.tools import Toolkit

from src.clients.http import DevToClient

_BODY_CHAR_LIMIT = 8_000


class DevToTools(Toolkit):
    """Agno tools for discovering hands-on tutorials on dev.to."""

    def __init__(self, client: DevToClient | None = None, **kwargs: Any) -> None:
        self._client = client or DevToClient()
        super().__init__(
            name="devto",
            tools=[self.search_articles, self.get_article],
            **kwargs,
        )

    async def search_articles(self, tag: str, top_days: int = 30, per_page: int = 10) -> str:
        """Find the most popular dev.to articles for a topic tag.

        Use this first when hunting for written tutorials. Results are the
        highest-reaction articles of roughly the past year (evergreen bias),
        which favors proven tutorials over this week's hot takes. Tags are
        lowercase without spaces, e.g. "python", "fastapi", "machinelearning".

        Args:
            tag: dev.to topic tag, e.g. "postgres".
            top_days: Look-back window in days for the popularity ranking.
            per_page: Maximum number of articles to return.

        Returns:
            A JSON string {"tag": ..., "articles": [...]} where each article
            has id, title, url, description, tags, reactions, comments,
            published and reading_minutes, or {"error": ...} on failure.
        """
        try:
            articles = await self._client.searchArticles(tag, top_days, per_page)
            return json.dumps({"tag": tag, "articles": [a.model_dump() for a in articles]})
        except Exception as exc:
            return json.dumps({"error": f"dev.to search failed: {exc}"})

    async def get_article(self, article_id: int) -> str:
        """Fetch the full markdown body of one dev.to article by numeric id.

        Use this on at most 1-2 of the best candidates from search_articles
        to verify an article is genuinely hands-on (code blocks, step-by-step
        instructions) before recommending it. Bodies longer than ~8,000
        characters are truncated and flagged.

        Args:
            article_id: The numeric "id" field returned by search_articles.

        Returns:
            A JSON string with title, url, tags, reactions, body_markdown and
            body_truncated, or {"error": ...} on failure.
        """
        try:
            article = await self._client.getArticle(article_id)
            body = article.body_markdown
            return json.dumps(
                {
                    "title": article.title,
                    "url": article.url,
                    "tags": article.tags,
                    "reactions": article.reactions,
                    "body_markdown": body[:_BODY_CHAR_LIMIT],
                    "body_truncated": len(body) > _BODY_CHAR_LIMIT,
                }
            )
        except Exception as exc:
            return json.dumps({"error": f"dev.to article fetch failed: {exc}"})
