"""RedditService — wraps the Reddit JSON API into proto RPCs."""

from __future__ import annotations

from typing import Any

import httpx

from reddit_mcp.gen.reddit.v1 import reddit_pb2 as pb

_BASE_URL = "https://www.reddit.com"
_HEADERS = {"User-Agent": "InvariantMCP/0.1"}


class RedditService:
    """Implements RedditService RPCs via the Reddit public JSON API."""

    def __init__(self):
        self._http = httpx.Client(timeout=30, headers=_HEADERS, follow_redirects=True)

    def _get(self, path: str, params: dict | None = None) -> Any:
        resp = self._http.get(f"{_BASE_URL}{path}", params=params or {})
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def _parse_post(data: dict) -> pb.Post:
        return pb.Post(
            id=data.get("id", ""),
            title=data.get("title", ""),
            selftext=data.get("selftext", ""),
            author=data.get("author", ""),
            subreddit=data.get("subreddit", ""),
            score=data.get("score", 0),
            num_comments=data.get("num_comments", 0),
            url=data.get("url", ""),
            permalink=data.get("permalink", ""),
            created_utc=data.get("created_utc", 0.0),
            is_self=data.get("is_self", False),
            thumbnail=data.get("thumbnail", ""),
        )

    @staticmethod
    def _parse_comment(data: dict) -> pb.Comment:
        replies_raw = data.get("replies", "")
        replies = []
        if isinstance(replies_raw, dict):
            for child in replies_raw.get("data", {}).get("children", []):
                if child.get("kind") == "t1":
                    replies.append(RedditService._parse_comment(child.get("data", {})))
        return pb.Comment(
            id=data.get("id", ""),
            author=data.get("author", ""),
            body=data.get("body", ""),
            score=data.get("score", 0),
            created_utc=data.get("created_utc", 0.0),
            permalink=data.get("permalink", ""),
            replies=replies,
        )

    def _get_listing_posts(self, path: str, params: dict | None = None) -> list[pb.Post]:
        raw = self._get(path, params)
        posts = []
        for child in raw.get("data", {}).get("children", []):
            if child.get("kind") == "t3":
                posts.append(self._parse_post(child.get("data", {})))
        return posts

    def GetHot(self, request: Any, context: Any = None) -> pb.GetHotResponse:
        limit = request.limit or 25
        posts = self._get_listing_posts(
            f"/r/{request.subreddit}/hot.json",
            params={"limit": limit},
        )
        return pb.GetHotResponse(posts=posts)

    def GetTop(self, request: Any, context: Any = None) -> pb.GetTopResponse:
        limit = request.limit or 25
        time_filter = request.time_filter or "day"
        posts = self._get_listing_posts(
            f"/r/{request.subreddit}/top.json",
            params={"t": time_filter, "limit": limit},
        )
        return pb.GetTopResponse(posts=posts)

    def GetNew(self, request: Any, context: Any = None) -> pb.GetNewResponse:
        limit = request.limit or 25
        posts = self._get_listing_posts(
            f"/r/{request.subreddit}/new.json",
            params={"limit": limit},
        )
        return pb.GetNewResponse(posts=posts)

    def GetPost(self, request: Any, context: Any = None) -> pb.GetPostResponse:
        raw = self._get(f"/r/{request.subreddit}/comments/{request.post_id}.json")
        # Reddit returns an array of 2 listings: [post_listing, comments_listing]
        post = pb.Post()
        comments = []
        if len(raw) >= 1:
            post_children = raw[0].get("data", {}).get("children", [])
            if post_children:
                post = self._parse_post(post_children[0].get("data", {}))
        if len(raw) >= 2:
            for child in raw[1].get("data", {}).get("children", []):
                if child.get("kind") == "t1":
                    comments.append(self._parse_comment(child.get("data", {})))
        return pb.GetPostResponse(post=post, comments=comments)

    def SearchPosts(self, request: Any, context: Any = None) -> pb.SearchPostsResponse:
        limit = request.limit or 25
        posts = self._get_listing_posts(
            "/search.json",
            params={"q": request.query, "type": "link", "limit": limit},
        )
        return pb.SearchPostsResponse(posts=posts)

    def GetSubreddit(self, request: Any, context: Any = None) -> pb.GetSubredditResponse:
        raw = self._get(f"/r/{request.subreddit}/about.json")
        data = raw.get("data", {})
        return pb.GetSubredditResponse(
            subreddit=pb.SubredditInfo(
                name=data.get("name", ""),
                display_name=data.get("display_name", ""),
                title=data.get("title", ""),
                description=data.get("public_description", ""),
                subscribers=data.get("subscribers", 0),
                active_users=data.get("accounts_active", 0) or 0,
                created_utc=data.get("created_utc", 0.0),
                url=data.get("url", ""),
                over18=data.get("over18", False),
            ),
        )

    def GetUser(self, request: Any, context: Any = None) -> pb.GetUserResponse:
        raw = self._get(f"/user/{request.username}/about.json")
        data = raw.get("data", {})
        return pb.GetUserResponse(
            user=pb.UserInfo(
                name=data.get("name", ""),
                link_karma=data.get("link_karma", 0),
                comment_karma=data.get("comment_karma", 0),
                created_utc=data.get("created_utc", 0.0),
                description=data.get("subreddit", {}).get("public_description", "") if isinstance(data.get("subreddit"), dict) else "",
                is_gold=data.get("is_gold", False),
                verified=data.get("verified", False),
            ),
        )

    def GetUserPosts(self, request: Any, context: Any = None) -> pb.GetUserPostsResponse:
        limit = request.limit or 25
        posts = self._get_listing_posts(
            f"/user/{request.username}/submitted.json",
            params={"limit": limit},
        )
        return pb.GetUserPostsResponse(posts=posts)

    def GetPopularSubreddits(self, request: Any, context: Any = None) -> pb.GetPopularSubredditsResponse:
        limit = request.limit or 25
        raw = self._get("/subreddits/popular.json", params={"limit": limit})
        subreddits = []
        for child in raw.get("data", {}).get("children", []):
            data = child.get("data", {})
            subreddits.append(pb.SubredditInfo(
                name=data.get("name", ""),
                display_name=data.get("display_name", ""),
                title=data.get("title", ""),
                description=data.get("public_description", ""),
                subscribers=data.get("subscribers", 0),
                active_users=data.get("accounts_active", 0) or 0,
                created_utc=data.get("created_utc", 0.0),
                url=data.get("url", ""),
                over18=data.get("over18", False),
            ))
        return pb.GetPopularSubredditsResponse(subreddits=subreddits)

    def GetFrontPage(self, request: Any, context: Any = None) -> pb.GetFrontPageResponse:
        limit = request.limit or 25
        posts = self._get_listing_posts(
            "/.json",
            params={"limit": limit},
        )
        return pb.GetFrontPageResponse(posts=posts)
