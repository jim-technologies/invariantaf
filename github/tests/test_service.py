"""Unit tests — every GitHubService RPC method, mocked HTTP."""

import pytest
from unittest.mock import MagicMock

from github_mcp.gen.github.v1 import github_pb2 as pb
from tests.conftest import (
    FAKE_ISSUE,
    FAKE_ISSUES,
    FAKE_LANGUAGES,
    FAKE_PULL,
    FAKE_PULLS,
    FAKE_RATE_LIMIT,
    FAKE_REPO,
    FAKE_SEARCH_REPOS,
    FAKE_SEARCH_USERS,
    FAKE_USER,
)


class TestSearchRepos:
    def test_returns_repos(self, service):
        resp = service.SearchRepos(pb.SearchReposRequest(query="linux"))
        assert resp.total_count == 2
        assert len(resp.items) == 2

    def test_first_repo_fields(self, service):
        resp = service.SearchRepos(pb.SearchReposRequest(query="linux"))
        repo = resp.items[0]
        assert repo.full_name == "torvalds/linux"
        assert repo.name == "linux"
        assert repo.owner_login == "torvalds"
        assert repo.description == "Linux kernel source tree"
        assert repo.language == "C"
        assert repo.stargazers_count == 180000
        assert repo.forks_count == 55000

    def test_second_repo(self, service):
        resp = service.SearchRepos(pb.SearchReposRequest(query="rust"))
        repo = resp.items[1]
        assert repo.full_name == "rust-lang/rust"
        assert repo.language == "Rust"
        assert repo.license_name == "MIT"

    def test_topics(self, service):
        resp = service.SearchRepos(pb.SearchReposRequest(query="linux"))
        assert "linux" in resp.items[0].topics
        assert "kernel" in resp.items[0].topics

    def test_optional_params_passed(self, service, mock_http):
        service.SearchRepos(pb.SearchReposRequest(
            query="test", sort="stars", order="asc", per_page=10, page=2,
        ))
        call_args = mock_http.get.call_args
        params = call_args[1].get("params", {})
        assert params.get("sort") == "stars"
        assert params.get("order") == "asc"
        assert params.get("per_page") == 10
        assert params.get("page") == 2

    def test_empty_response(self, service, mock_http):
        mock_http.get.side_effect = lambda url, params=None: MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"total_count": 0, "items": []}),
        )
        resp = service.SearchRepos(pb.SearchReposRequest(query="nonexistent"))
        assert resp.total_count == 0
        assert len(resp.items) == 0


class TestSearchUsers:
    def test_returns_users(self, service):
        resp = service.SearchUsers(pb.SearchUsersRequest(query="torvalds"))
        assert resp.total_count == 1
        assert len(resp.items) == 1

    def test_user_fields(self, service):
        resp = service.SearchUsers(pb.SearchUsersRequest(query="torvalds"))
        user = resp.items[0]
        assert user.login == "torvalds"
        assert user.type == "User"
        assert user.id == 1024025

    def test_optional_params(self, service, mock_http):
        service.SearchUsers(pb.SearchUsersRequest(
            query="test", sort="followers", order="desc", per_page=5, page=1,
        ))
        call_args = mock_http.get.call_args
        params = call_args[1].get("params", {})
        assert params.get("sort") == "followers"


class TestGetUser:
    def test_basic_fields(self, service):
        resp = service.GetUser(pb.GetUserRequest(username="torvalds"))
        user = resp.user
        assert user.login == "torvalds"
        assert user.name == "Linus Torvalds"
        assert user.type == "User"
        assert user.id == 1024025

    def test_bio_and_company(self, service):
        resp = service.GetUser(pb.GetUserRequest(username="torvalds"))
        user = resp.user
        assert user.bio == "Creator of Linux and Git"
        assert user.company == "Linux Foundation"
        assert user.location == "Portland, OR"

    def test_follower_counts(self, service):
        resp = service.GetUser(pb.GetUserRequest(username="torvalds"))
        user = resp.user
        assert user.followers == 220000
        assert user.following == 0
        assert user.public_repos == 7

    def test_created_at(self, service):
        resp = service.GetUser(pb.GetUserRequest(username="torvalds"))
        assert resp.user.created_at == "2011-09-03T15:26:22Z"


class TestGetRepo:
    def test_basic_fields(self, service):
        resp = service.GetRepo(pb.GetRepoRequest(owner="torvalds", repo="linux"))
        repo = resp.repo
        assert repo.full_name == "torvalds/linux"
        assert repo.name == "linux"
        assert repo.owner_login == "torvalds"
        assert repo.language == "C"

    def test_counts(self, service):
        resp = service.GetRepo(pb.GetRepoRequest(owner="torvalds", repo="linux"))
        repo = resp.repo
        assert repo.stargazers_count == 180000
        assert repo.forks_count == 55000
        assert repo.open_issues_count == 300

    def test_metadata(self, service):
        resp = service.GetRepo(pb.GetRepoRequest(owner="torvalds", repo="linux"))
        repo = resp.repo
        assert repo.default_branch == "master"
        assert repo.license_name == "GPL-2.0"
        assert repo.fork is False
        assert repo.archived is False

    def test_topics(self, service):
        resp = service.GetRepo(pb.GetRepoRequest(owner="torvalds", repo="linux"))
        assert "linux" in resp.repo.topics
        assert "kernel" in resp.repo.topics


class TestListRepoIssues:
    def test_returns_issues(self, service):
        resp = service.ListRepoIssues(pb.ListRepoIssuesRequest(
            owner="torvalds", repo="linux",
        ))
        assert len(resp.issues) == 2

    def test_issue_fields(self, service):
        resp = service.ListRepoIssues(pb.ListRepoIssuesRequest(
            owner="torvalds", repo="linux",
        ))
        issue = resp.issues[0]
        assert issue.number == 42
        assert issue.title == "Bug in scheduler"
        assert issue.state == "open"
        assert issue.user_login == "contributor1"
        assert issue.comments == 5

    def test_labels(self, service):
        resp = service.ListRepoIssues(pb.ListRepoIssuesRequest(
            owner="torvalds", repo="linux",
        ))
        assert "bug" in resp.issues[0].labels

    def test_assignees(self, service):
        resp = service.ListRepoIssues(pb.ListRepoIssuesRequest(
            owner="torvalds", repo="linux",
        ))
        assert "torvalds" in resp.issues[0].assignees

    def test_is_pull_request_flag(self, service):
        resp = service.ListRepoIssues(pb.ListRepoIssuesRequest(
            owner="torvalds", repo="linux",
        ))
        assert resp.issues[0].is_pull_request is False
        assert resp.issues[1].is_pull_request is True

    def test_state_filter(self, service, mock_http):
        service.ListRepoIssues(pb.ListRepoIssuesRequest(
            owner="torvalds", repo="linux", state="closed",
        ))
        call_args = mock_http.get.call_args
        params = call_args[1].get("params", {})
        assert params.get("state") == "closed"


class TestGetIssue:
    def test_basic_fields(self, service):
        resp = service.GetIssue(pb.GetIssueRequest(
            owner="torvalds", repo="linux", issue_number=42,
        ))
        issue = resp.issue
        assert issue.number == 42
        assert issue.title == "Bug in scheduler"
        assert issue.body == "The scheduler has a race condition."
        assert issue.state == "open"

    def test_labels_and_assignees(self, service):
        resp = service.GetIssue(pb.GetIssueRequest(
            owner="torvalds", repo="linux", issue_number=42,
        ))
        assert "bug" in resp.issue.labels
        assert "torvalds" in resp.issue.assignees

    def test_timestamps(self, service):
        resp = service.GetIssue(pb.GetIssueRequest(
            owner="torvalds", repo="linux", issue_number=42,
        ))
        assert resp.issue.created_at == "2025-01-10T08:00:00Z"
        assert resp.issue.updated_at == "2025-01-14T12:00:00Z"


class TestListRepoPulls:
    def test_returns_pulls(self, service):
        resp = service.ListRepoPulls(pb.ListRepoPullsRequest(
            owner="torvalds", repo="linux",
        ))
        assert len(resp.pulls) == 1

    def test_pull_fields(self, service):
        resp = service.ListRepoPulls(pb.ListRepoPullsRequest(
            owner="torvalds", repo="linux",
        ))
        pr = resp.pulls[0]
        assert pr.number == 99
        assert pr.title == "Fix memory leak in driver"
        assert pr.state == "open"
        assert pr.user_login == "contributor3"
        assert pr.merged is False

    def test_refs(self, service):
        resp = service.ListRepoPulls(pb.ListRepoPullsRequest(
            owner="torvalds", repo="linux",
        ))
        pr = resp.pulls[0]
        assert pr.head_ref == "fix-memory-leak"
        assert pr.base_ref == "master"

    def test_labels(self, service):
        resp = service.ListRepoPulls(pb.ListRepoPullsRequest(
            owner="torvalds", repo="linux",
        ))
        assert "bugfix" in resp.pulls[0].labels


class TestGetPull:
    def test_basic_fields(self, service):
        resp = service.GetPull(pb.GetPullRequest(
            owner="torvalds", repo="linux", pull_number=99,
        ))
        pr = resp.pull
        assert pr.number == 99
        assert pr.title == "Fix memory leak in driver"
        assert pr.state == "open"

    def test_diff_stats(self, service):
        resp = service.GetPull(pb.GetPullRequest(
            owner="torvalds", repo="linux", pull_number=99,
        ))
        pr = resp.pull
        assert pr.additions == 150
        assert pr.deletions == 30
        assert pr.changed_files == 5
        assert pr.commits == 3
        assert pr.comments == 7

    def test_refs(self, service):
        resp = service.GetPull(pb.GetPullRequest(
            owner="torvalds", repo="linux", pull_number=99,
        ))
        assert resp.pull.head_ref == "fix-memory-leak"
        assert resp.pull.base_ref == "master"

    def test_merge_status(self, service):
        resp = service.GetPull(pb.GetPullRequest(
            owner="torvalds", repo="linux", pull_number=99,
        ))
        assert resp.pull.merged is False
        assert resp.pull.merged_at == ""


class TestListRepoLanguages:
    def test_returns_languages(self, service):
        resp = service.ListRepoLanguages(pb.ListRepoLanguagesRequest(
            owner="torvalds", repo="linux",
        ))
        assert "C" in resp.languages
        assert "Assembly" in resp.languages
        assert "Python" in resp.languages

    def test_language_values(self, service):
        resp = service.ListRepoLanguages(pb.ListRepoLanguagesRequest(
            owner="torvalds", repo="linux",
        ))
        assert resp.languages["C"] == 900000000
        assert resp.languages["Assembly"] == 50000000

    def test_language_count(self, service):
        resp = service.ListRepoLanguages(pb.ListRepoLanguagesRequest(
            owner="torvalds", repo="linux",
        ))
        assert len(resp.languages) == 5


class TestGetRateLimit:
    def test_rate_limit_fields(self, service):
        resp = service.GetRateLimit(pb.GetRateLimitRequest())
        assert resp.limit == 60
        assert resp.remaining == 55
        assert resp.reset == 1700003600
        assert resp.used == 5
