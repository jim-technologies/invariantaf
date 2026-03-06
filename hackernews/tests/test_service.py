"""Unit tests — every HackerNewsService RPC method, mocked HTTP."""

import pytest
from unittest.mock import MagicMock

from hackernews_mcp.gen.hackernews.v1 import hackernews_pb2 as pb
from tests.conftest import (
    FAKE_COMMENT_1,
    FAKE_COMMENT_2,
    FAKE_COMMENT_3,
    FAKE_JOB,
    FAKE_MAX_ITEM,
    FAKE_NESTED_COMMENT_1,
    FAKE_NESTED_COMMENT_2,
    FAKE_STORY_1,
    FAKE_STORY_2,
    FAKE_STORY_3,
    FAKE_USER,
)


class TestGetTopStories:
    def test_returns_stories(self, service):
        resp = service.GetTopStories(pb.GetStoriesRequest(limit=3))
        assert len(resp.items) == 3

    def test_default_limit(self, service):
        resp = service.GetTopStories(pb.GetStoriesRequest())
        # Our fake data only has 3 stories, so we get 3 even though default is 10
        assert len(resp.items) == 3

    def test_first_story_fields(self, service):
        resp = service.GetTopStories(pb.GetStoriesRequest(limit=1))
        item = resp.items[0]
        assert item.id == FAKE_STORY_1["id"]
        assert item.type == "story"
        assert item.by == "pg"
        assert item.title == "Hacking the attention economy"
        assert item.url == "https://example.com/hacking-attention"
        assert item.score == 342
        assert item.descendants == 187
        assert item.time == 1700000000

    def test_limit_respected(self, service):
        resp = service.GetTopStories(pb.GetStoriesRequest(limit=2))
        assert len(resp.items) == 2

    def test_kids_included(self, service):
        resp = service.GetTopStories(pb.GetStoriesRequest(limit=1))
        assert len(resp.items[0].kids) == 3


class TestGetNewStories:
    def test_returns_stories(self, service):
        resp = service.GetNewStories(pb.GetStoriesRequest(limit=3))
        assert len(resp.items) == 3

    def test_order_matches_api(self, service):
        resp = service.GetNewStories(pb.GetStoriesRequest(limit=3))
        # New stories are in reverse chronological order
        assert resp.items[0].id == FAKE_STORY_3["id"]
        assert resp.items[1].id == FAKE_STORY_2["id"]
        assert resp.items[2].id == FAKE_STORY_1["id"]


class TestGetBestStories:
    def test_returns_stories(self, service):
        resp = service.GetBestStories(pb.GetStoriesRequest(limit=3))
        assert len(resp.items) == 3

    def test_first_is_highest_scored(self, service):
        resp = service.GetBestStories(pb.GetStoriesRequest(limit=1))
        assert resp.items[0].id == FAKE_STORY_1["id"]
        assert resp.items[0].score == 342


class TestGetAskStories:
    def test_returns_ask_stories(self, service):
        resp = service.GetAskStories(pb.GetStoriesRequest(limit=10))
        assert len(resp.items) == 1
        assert resp.items[0].title.startswith("Ask HN:")

    def test_ask_story_has_text(self, service):
        resp = service.GetAskStories(pb.GetStoriesRequest(limit=1))
        assert resp.items[0].text != ""


class TestGetShowStories:
    def test_returns_show_stories(self, service):
        resp = service.GetShowStories(pb.GetStoriesRequest(limit=10))
        assert len(resp.items) == 1
        assert resp.items[0].title.startswith("Show HN:")


class TestGetJobStories:
    def test_returns_job_stories(self, service):
        resp = service.GetJobStories(pb.GetStoriesRequest(limit=10))
        assert len(resp.items) == 1

    def test_job_fields(self, service):
        resp = service.GetJobStories(pb.GetStoriesRequest(limit=1))
        item = resp.items[0]
        assert item.type == "job"
        assert item.by == "ycombinator"
        assert item.title == "YC is hiring a software engineer"
        assert item.url == "https://ycombinator.com/careers"


class TestGetItem:
    def test_returns_story(self, service):
        resp = service.GetItem(pb.GetItemRequest(id=41881548))
        assert resp.item.id == 41881548
        assert resp.item.type == "story"
        assert resp.item.title == "Hacking the attention economy"

    def test_returns_comment(self, service):
        resp = service.GetItem(pb.GetItemRequest(id=41881600))
        assert resp.item.id == 41881600
        assert resp.item.type == "comment"
        assert resp.item.by == "jsmith"
        assert "insightful" in resp.item.text
        assert resp.item.parent == 41881548

    def test_returns_job(self, service):
        resp = service.GetItem(pb.GetItemRequest(id=41881551))
        assert resp.item.type == "job"
        assert resp.item.by == "ycombinator"

    def test_nonexistent_item(self, service, mock_http):
        # Override to return empty for unknown ID
        original_side_effect = mock_http.get.side_effect

        def patched_get(url, params=None):
            if "/item/99999999.json" in url:
                resp = MagicMock()
                resp.raise_for_status = MagicMock()
                resp.json.return_value = {}
                return resp
            return original_side_effect(url, params)

        mock_http.get.side_effect = patched_get
        resp = service.GetItem(pb.GetItemRequest(id=99999999))
        # Empty response when item doesn't exist
        assert resp.item.id == 0


class TestGetUser:
    def test_returns_user(self, service):
        resp = service.GetUser(pb.GetUserRequest(id="pg"))
        assert resp.user.id == "pg"
        assert resp.user.karma == 157236
        assert resp.user.about == "Bug fixer."
        assert resp.user.created == 1160418111

    def test_submitted_list(self, service):
        resp = service.GetUser(pb.GetUserRequest(id="pg"))
        assert len(resp.user.submitted) == 5
        assert 41881548 in resp.user.submitted


class TestGetComments:
    def test_returns_direct_comments(self, service):
        resp = service.GetComments(pb.GetCommentsRequest(story_id=41881548, depth=1))
        assert len(resp.comments) == 3
        comment_ids = [c.id for c in resp.comments]
        assert 41881600 in comment_ids
        assert 41881601 in comment_ids
        assert 41881602 in comment_ids

    def test_comment_fields(self, service):
        resp = service.GetComments(pb.GetCommentsRequest(story_id=41881548, depth=1))
        c = [c for c in resp.comments if c.id == 41881600][0]
        assert c.type == "comment"
        assert c.by == "jsmith"
        assert "insightful" in c.text
        assert c.parent == 41881548

    def test_nested_comments_depth_2(self, service):
        resp = service.GetComments(pb.GetCommentsRequest(story_id=41881548, depth=2))
        comment_ids = [c.id for c in resp.comments]
        # Should include direct comments AND their children
        assert 41881600 in comment_ids  # direct
        assert 41881601 in comment_ids  # direct
        assert 41881602 in comment_ids  # direct
        assert 41881610 in comment_ids  # nested under 41881600
        assert 41881611 in comment_ids  # nested under 41881600

    def test_depth_1_excludes_nested(self, service):
        resp = service.GetComments(pb.GetCommentsRequest(story_id=41881548, depth=1))
        comment_ids = [c.id for c in resp.comments]
        # Nested comments should NOT be included at depth 1
        assert 41881610 not in comment_ids
        assert 41881611 not in comment_ids

    def test_limit_respected(self, service):
        resp = service.GetComments(pb.GetCommentsRequest(
            story_id=41881548, depth=2, limit=2
        ))
        assert len(resp.comments) <= 2

    def test_default_depth(self, service):
        resp = service.GetComments(pb.GetCommentsRequest(story_id=41881548))
        # Default depth=1, should get 3 direct comments
        assert len(resp.comments) == 3


class TestGetMaxItem:
    def test_returns_max_id(self, service):
        resp = service.GetMaxItem(pb.GetMaxItemRequest())
        assert resp.max_id == FAKE_MAX_ITEM
        assert resp.max_id == 41882000
