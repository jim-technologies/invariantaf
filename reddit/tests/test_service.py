"""Unit tests — every RedditService RPC method, mocked HTTP."""

import pytest
from unittest.mock import MagicMock

from reddit_mcp.gen.reddit.v1 import reddit_pb2 as pb
from tests.conftest import (
    FAKE_FRONT_PAGE,
    FAKE_LISTING_POSTS,
    FAKE_POPULAR_SUBREDDITS,
    FAKE_POST_DETAIL,
    FAKE_SEARCH_RESULTS,
    FAKE_SUBREDDIT_ABOUT,
    FAKE_USER_ABOUT,
    FAKE_USER_POSTS,
)


class TestGetHot:
    def test_returns_posts(self, service):
        resp = service.GetHot(pb.GetHotRequest(subreddit="python", limit=25))
        assert len(resp.posts) == 2

    def test_first_post_fields(self, service):
        resp = service.GetHot(pb.GetHotRequest(subreddit="python"))
        post = resp.posts[0]
        assert post.id == "abc123"
        assert post.title == "Test Post Title"
        assert post.selftext == "This is the body of the test post."
        assert post.author == "testuser"
        assert post.subreddit == "python"
        assert post.score == 1500
        assert post.num_comments == 200
        assert post.is_self is True

    def test_second_post_fields(self, service):
        resp = service.GetHot(pb.GetHotRequest(subreddit="python"))
        post = resp.posts[1]
        assert post.id == "def456"
        assert post.title == "Another Post"
        assert post.author == "otheruser"
        assert post.is_self is False

    def test_default_limit(self, service, mock_http):
        service.GetHot(pb.GetHotRequest(subreddit="python"))
        call_args = mock_http.get.call_args
        assert call_args[1].get("params", {}).get("limit") == 25

    def test_empty_response(self, service, mock_http):
        mock_http.get.side_effect = lambda url, params=None: MagicMock(
            raise_for_status=MagicMock(), json=MagicMock(return_value={})
        )
        resp = service.GetHot(pb.GetHotRequest(subreddit="nonexistent"))
        assert len(resp.posts) == 0


class TestGetTop:
    def test_returns_posts(self, service):
        resp = service.GetTop(pb.GetTopRequest(subreddit="python", time_filter="week"))
        assert len(resp.posts) == 2

    def test_time_filter_passed(self, service, mock_http):
        service.GetTop(pb.GetTopRequest(subreddit="python", time_filter="month"))
        call_args = mock_http.get.call_args
        assert call_args[1].get("params", {}).get("t") == "month"

    def test_default_time_filter(self, service, mock_http):
        service.GetTop(pb.GetTopRequest(subreddit="python"))
        call_args = mock_http.get.call_args
        assert call_args[1].get("params", {}).get("t") == "day"

    def test_post_score(self, service):
        resp = service.GetTop(pb.GetTopRequest(subreddit="python"))
        assert resp.posts[0].score == 1500


class TestGetNew:
    def test_returns_posts(self, service):
        resp = service.GetNew(pb.GetNewRequest(subreddit="python"))
        assert len(resp.posts) == 2

    def test_post_fields(self, service):
        resp = service.GetNew(pb.GetNewRequest(subreddit="python"))
        assert resp.posts[0].id == "abc123"
        assert resp.posts[0].created_utc == 1700000000.0

    def test_limit_passed(self, service, mock_http):
        service.GetNew(pb.GetNewRequest(subreddit="python", limit=10))
        call_args = mock_http.get.call_args
        assert call_args[1].get("params", {}).get("limit") == 10


class TestGetPost:
    def test_returns_post(self, service):
        resp = service.GetPost(pb.GetPostRequest(subreddit="python", post_id="abc123"))
        assert resp.post.id == "abc123"
        assert resp.post.title == "Test Post Title"
        assert resp.post.author == "testuser"

    def test_returns_comments(self, service):
        resp = service.GetPost(pb.GetPostRequest(subreddit="python", post_id="abc123"))
        assert len(resp.comments) == 2
        assert resp.comments[0].id == "cmt001"
        assert resp.comments[0].author == "commenter1"
        assert resp.comments[0].body == "Great post!"
        assert resp.comments[0].score == 100

    def test_nested_replies(self, service):
        resp = service.GetPost(pb.GetPostRequest(subreddit="python", post_id="abc123"))
        assert len(resp.comments[0].replies) == 1
        reply = resp.comments[0].replies[0]
        assert reply.id == "cmt002"
        assert reply.author == "replier1"
        assert reply.body == "Thanks!"

    def test_comment_without_replies(self, service):
        resp = service.GetPost(pb.GetPostRequest(subreddit="python", post_id="abc123"))
        assert len(resp.comments[1].replies) == 0
        assert resp.comments[1].body == "Interesting discussion."


class TestSearchPosts:
    def test_returns_results(self, service):
        resp = service.SearchPosts(pb.SearchPostsRequest(query="python tutorial"))
        assert len(resp.posts) == 1

    def test_result_fields(self, service):
        resp = service.SearchPosts(pb.SearchPostsRequest(query="python tutorial"))
        post = resp.posts[0]
        assert post.id == "srch01"
        assert post.title == "Python tutorial for beginners"
        assert post.author == "educator"
        assert post.subreddit == "learnpython"
        assert post.score == 3000

    def test_query_passed(self, service, mock_http):
        service.SearchPosts(pb.SearchPostsRequest(query="test query", limit=10))
        call_args = mock_http.get.call_args
        params = call_args[1].get("params", {})
        assert params.get("q") == "test query"
        assert params.get("type") == "link"
        assert params.get("limit") == 10


class TestGetSubreddit:
    def test_returns_subreddit_info(self, service):
        resp = service.GetSubreddit(pb.GetSubredditRequest(subreddit="python"))
        sr = resp.subreddit
        assert sr.display_name == "python"
        assert sr.title == "Python"
        assert sr.subscribers == 1500000
        assert sr.active_users == 5000

    def test_subreddit_description(self, service):
        resp = service.GetSubreddit(pb.GetSubredditRequest(subreddit="python"))
        assert "programming language Python" in resp.subreddit.description

    def test_subreddit_metadata(self, service):
        resp = service.GetSubreddit(pb.GetSubredditRequest(subreddit="python"))
        sr = resp.subreddit
        assert sr.created_utc == 1230000000.0
        assert sr.url == "/r/python/"
        assert sr.over18 is False


class TestGetUser:
    def test_returns_user_info(self, service):
        resp = service.GetUser(pb.GetUserRequest(username="testuser"))
        user = resp.user
        assert user.name == "testuser"
        assert user.link_karma == 10000
        assert user.comment_karma == 50000

    def test_user_metadata(self, service):
        resp = service.GetUser(pb.GetUserRequest(username="testuser"))
        user = resp.user
        assert user.created_utc == 1400000000.0
        assert user.is_gold is True
        assert user.verified is True

    def test_user_description(self, service):
        resp = service.GetUser(pb.GetUserRequest(username="testuser"))
        assert "Python" in resp.user.description


class TestGetUserPosts:
    def test_returns_posts(self, service):
        resp = service.GetUserPosts(pb.GetUserPostsRequest(username="testuser"))
        assert len(resp.posts) == 1

    def test_post_fields(self, service):
        resp = service.GetUserPosts(pb.GetUserPostsRequest(username="testuser"))
        post = resp.posts[0]
        assert post.id == "usr01"
        assert post.title == "My project update"
        assert post.author == "testuser"
        assert post.score == 800


class TestGetPopularSubreddits:
    def test_returns_subreddits(self, service):
        resp = service.GetPopularSubreddits(pb.GetPopularSubredditsRequest())
        assert len(resp.subreddits) == 2

    def test_first_subreddit(self, service):
        resp = service.GetPopularSubreddits(pb.GetPopularSubredditsRequest())
        sr = resp.subreddits[0]
        assert sr.display_name == "AskReddit"
        assert sr.subscribers == 45000000
        assert sr.active_users == 50000

    def test_second_subreddit(self, service):
        resp = service.GetPopularSubreddits(pb.GetPopularSubredditsRequest())
        sr = resp.subreddits[1]
        assert sr.display_name == "funny"
        assert sr.subscribers == 40000000

    def test_limit_passed(self, service, mock_http):
        service.GetPopularSubreddits(pb.GetPopularSubredditsRequest(limit=10))
        call_args = mock_http.get.call_args
        assert call_args[1].get("params", {}).get("limit") == 10


class TestGetFrontPage:
    def test_returns_posts(self, service):
        resp = service.GetFrontPage(pb.GetFrontPageRequest())
        assert len(resp.posts) == 1

    def test_post_fields(self, service):
        resp = service.GetFrontPage(pb.GetFrontPageRequest())
        post = resp.posts[0]
        assert post.id == "fp001"
        assert post.title == "Front page post"
        assert post.author == "frontpageuser"
        assert post.subreddit == "worldnews"
        assert post.score == 50000

    def test_default_limit(self, service, mock_http):
        service.GetFrontPage(pb.GetFrontPageRequest())
        call_args = mock_http.get.call_args
        assert call_args[1].get("params", {}).get("limit") == 25
