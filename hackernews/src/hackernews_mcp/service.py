"""HackerNewsService — wraps the HN Firebase API into proto RPCs."""

from __future__ import annotations

from typing import Any

import httpx

from hackernews_mcp.gen.hackernews.v1 import hackernews_pb2 as pb

_BASE_URL = "https://hacker-news.firebaseio.com/v0"


class HackerNewsService:
    """Implements HackerNewsService RPCs via the Hacker News Firebase API."""

    def __init__(self):
        self._http = httpx.Client(timeout=30)

    def _get(self, path: str) -> Any:
        resp = self._http.get(f"{_BASE_URL}{path}")
        resp.raise_for_status()
        return resp.json()

    def _fetch_item(self, item_id: int) -> dict:
        """Fetch a single item by ID and return the raw JSON dict."""
        return self._get(f"/item/{item_id}.json") or {}

    def _raw_to_item(self, raw: dict) -> pb.Item:
        """Convert a raw HN API item dict into a proto Item message."""
        return pb.Item(
            id=raw.get("id", 0),
            deleted=raw.get("deleted", False),
            type=raw.get("type", ""),
            by=raw.get("by", ""),
            time=raw.get("time", 0),
            text=raw.get("text", ""),
            dead=raw.get("dead", False),
            parent=raw.get("parent", 0),
            poll=raw.get("poll", 0),
            kids=raw.get("kids", []),
            url=raw.get("url", ""),
            score=raw.get("score", 0),
            title=raw.get("title", ""),
            parts=raw.get("parts", []),
            descendants=raw.get("descendants", 0),
        )

    def _fetch_stories(self, endpoint: str, limit: int) -> pb.GetStoriesResponse:
        """Shared logic for all story-list endpoints."""
        ids = self._get(f"/{endpoint}.json") or []
        ids = ids[:limit]
        resp = pb.GetStoriesResponse()
        for item_id in ids:
            raw = self._fetch_item(item_id)
            if raw:
                resp.items.append(self._raw_to_item(raw))
        return resp

    def GetTopStories(self, request: Any, context: Any = None) -> pb.GetStoriesResponse:
        limit = request.limit or 10
        return self._fetch_stories("topstories", limit)

    def GetNewStories(self, request: Any, context: Any = None) -> pb.GetStoriesResponse:
        limit = request.limit or 10
        return self._fetch_stories("newstories", limit)

    def GetBestStories(self, request: Any, context: Any = None) -> pb.GetStoriesResponse:
        limit = request.limit or 10
        return self._fetch_stories("beststories", limit)

    def GetAskStories(self, request: Any, context: Any = None) -> pb.GetStoriesResponse:
        limit = request.limit or 10
        return self._fetch_stories("askstories", limit)

    def GetShowStories(self, request: Any, context: Any = None) -> pb.GetStoriesResponse:
        limit = request.limit or 10
        return self._fetch_stories("showstories", limit)

    def GetJobStories(self, request: Any, context: Any = None) -> pb.GetStoriesResponse:
        limit = request.limit or 10
        return self._fetch_stories("jobstories", limit)

    def GetItem(self, request: Any, context: Any = None) -> pb.GetItemResponse:
        raw = self._fetch_item(request.id)
        resp = pb.GetItemResponse()
        if raw:
            resp.item.CopyFrom(self._raw_to_item(raw))
        return resp

    def GetUser(self, request: Any, context: Any = None) -> pb.GetUserResponse:
        raw = self._get(f"/user/{request.id}.json") or {}
        resp = pb.GetUserResponse()
        if raw:
            resp.user.CopyFrom(pb.User(
                id=raw.get("id", ""),
                created=raw.get("created", 0),
                karma=raw.get("karma", 0),
                about=raw.get("about", ""),
                submitted=raw.get("submitted", []),
            ))
        return resp

    def GetComments(self, request: Any, context: Any = None) -> pb.GetCommentsResponse:
        depth = request.depth or 1
        limit = request.limit or 30

        story = self._fetch_item(request.story_id)
        if not story:
            return pb.GetCommentsResponse()

        kid_ids = story.get("kids", [])
        comments = []
        self._fetch_comments_recursive(kid_ids, depth, limit, comments)

        resp = pb.GetCommentsResponse()
        for raw in comments:
            resp.comments.append(self._raw_to_item(raw))
        return resp

    def _fetch_comments_recursive(
        self, kid_ids: list[int], depth: int, limit: int, out: list[dict]
    ):
        """Recursively fetch comments up to `depth` levels, appending to `out`."""
        if depth <= 0 or len(out) >= limit:
            return
        for kid_id in kid_ids:
            if len(out) >= limit:
                break
            raw = self._fetch_item(kid_id)
            if not raw or raw.get("deleted") or raw.get("dead"):
                continue
            out.append(raw)
            if depth > 1:
                child_kids = raw.get("kids", [])
                self._fetch_comments_recursive(child_kids, depth - 1, limit, out)

    def GetMaxItem(self, request: Any, context: Any = None) -> pb.GetMaxItemResponse:
        max_id = self._get("/maxitem.json") or 0
        return pb.GetMaxItemResponse(max_id=max_id)
