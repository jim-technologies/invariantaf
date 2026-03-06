"""GitHubService — wraps the GitHub REST API into proto RPCs."""

from __future__ import annotations

import os
from typing import Any

import httpx

from github_mcp.gen.github.v1 import github_pb2 as pb

_BASE_URL = "https://api.github.com"


class GitHubService:
    """Implements GitHubService RPCs via the GitHub REST API."""

    def __init__(self, *, token: str | None = None):
        self._token = token or os.environ.get("GITHUB_TOKEN")
        headers = {"Accept": "application/vnd.github+json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        self._http = httpx.Client(timeout=30, headers=headers)

    def _get(self, path: str, params: dict | None = None) -> Any:
        resp = self._http.get(f"{_BASE_URL}{path}", params=params)
        resp.raise_for_status()
        return resp.json()

    def SearchRepos(self, request: Any, context: Any = None) -> pb.SearchReposResponse:
        params: dict[str, Any] = {"q": request.query}
        if request.sort:
            params["sort"] = request.sort
        if request.order:
            params["order"] = request.order
        if request.per_page:
            params["per_page"] = request.per_page
        if request.page:
            params["page"] = request.page

        raw = self._get("/search/repositories", params)
        resp = pb.SearchReposResponse(total_count=raw.get("total_count", 0))
        for item in raw.get("items", []):
            resp.items.append(pb.Repository(
                id=item.get("id", 0),
                full_name=item.get("full_name", ""),
                name=item.get("name", ""),
                owner_login=(item.get("owner") or {}).get("login", ""),
                description=item.get("description") or "",
                html_url=item.get("html_url", ""),
                language=item.get("language") or "",
                stargazers_count=item.get("stargazers_count", 0),
                forks_count=item.get("forks_count", 0),
                watchers_count=item.get("watchers_count", 0),
                open_issues_count=item.get("open_issues_count", 0),
                default_branch=item.get("default_branch", ""),
                license_name=(item.get("license") or {}).get("name", ""),
                created_at=item.get("created_at") or "",
                updated_at=item.get("updated_at") or "",
                fork=item.get("fork", False),
                archived=item.get("archived", False),
                topics=item.get("topics") or [],
            ))
        return resp

    def SearchUsers(self, request: Any, context: Any = None) -> pb.SearchUsersResponse:
        params: dict[str, Any] = {"q": request.query}
        if request.sort:
            params["sort"] = request.sort
        if request.order:
            params["order"] = request.order
        if request.per_page:
            params["per_page"] = request.per_page
        if request.page:
            params["page"] = request.page

        raw = self._get("/search/users", params)
        resp = pb.SearchUsersResponse(total_count=raw.get("total_count", 0))
        for item in raw.get("items", []):
            resp.items.append(pb.User(
                id=item.get("id", 0),
                login=item.get("login", ""),
                avatar_url=item.get("avatar_url", ""),
                html_url=item.get("html_url", ""),
                type=item.get("type", ""),
            ))
        return resp

    def GetUser(self, request: Any, context: Any = None) -> pb.GetUserResponse:
        raw = self._get(f"/users/{request.username}")
        return pb.GetUserResponse(user=pb.User(
            id=raw.get("id", 0),
            login=raw.get("login", ""),
            avatar_url=raw.get("avatar_url", ""),
            html_url=raw.get("html_url", ""),
            type=raw.get("type", ""),
            name=raw.get("name") or "",
            bio=raw.get("bio") or "",
            company=raw.get("company") or "",
            location=raw.get("location") or "",
            email=raw.get("email") or "",
            public_repos=raw.get("public_repos", 0),
            public_gists=raw.get("public_gists", 0),
            followers=raw.get("followers", 0),
            following=raw.get("following", 0),
            created_at=raw.get("created_at") or "",
        ))

    def GetRepo(self, request: Any, context: Any = None) -> pb.GetRepoResponse:
        raw = self._get(f"/repos/{request.owner}/{request.repo}")
        return pb.GetRepoResponse(repo=pb.Repository(
            id=raw.get("id", 0),
            full_name=raw.get("full_name", ""),
            name=raw.get("name", ""),
            owner_login=(raw.get("owner") or {}).get("login", ""),
            description=raw.get("description") or "",
            html_url=raw.get("html_url", ""),
            language=raw.get("language") or "",
            stargazers_count=raw.get("stargazers_count", 0),
            forks_count=raw.get("forks_count", 0),
            watchers_count=raw.get("watchers_count", 0),
            open_issues_count=raw.get("open_issues_count", 0),
            default_branch=raw.get("default_branch", ""),
            license_name=(raw.get("license") or {}).get("name", ""),
            created_at=raw.get("created_at") or "",
            updated_at=raw.get("updated_at") or "",
            fork=raw.get("fork", False),
            archived=raw.get("archived", False),
            topics=raw.get("topics") or [],
        ))

    def ListRepoIssues(self, request: Any, context: Any = None) -> pb.ListRepoIssuesResponse:
        params: dict[str, Any] = {}
        if request.state:
            params["state"] = request.state
        if request.labels:
            params["labels"] = request.labels
        if request.per_page:
            params["per_page"] = request.per_page
        if request.page:
            params["page"] = request.page

        raw = self._get(f"/repos/{request.owner}/{request.repo}/issues", params)
        resp = pb.ListRepoIssuesResponse()
        for item in raw:
            resp.issues.append(pb.Issue(
                id=item.get("id", 0),
                number=item.get("number", 0),
                title=item.get("title", ""),
                body=item.get("body") or "",
                state=item.get("state", ""),
                html_url=item.get("html_url", ""),
                user_login=(item.get("user") or {}).get("login", ""),
                labels=[label.get("name", "") for label in (item.get("labels") or [])],
                assignees=[a.get("login", "") for a in (item.get("assignees") or [])],
                comments=item.get("comments", 0),
                created_at=item.get("created_at") or "",
                updated_at=item.get("updated_at") or "",
                closed_at=item.get("closed_at") or "",
                is_pull_request=bool(item.get("pull_request")),
            ))
        return resp

    def GetIssue(self, request: Any, context: Any = None) -> pb.GetIssueResponse:
        raw = self._get(f"/repos/{request.owner}/{request.repo}/issues/{request.issue_number}")
        return pb.GetIssueResponse(issue=pb.Issue(
            id=raw.get("id", 0),
            number=raw.get("number", 0),
            title=raw.get("title", ""),
            body=raw.get("body") or "",
            state=raw.get("state", ""),
            html_url=raw.get("html_url", ""),
            user_login=(raw.get("user") or {}).get("login", ""),
            labels=[label.get("name", "") for label in (raw.get("labels") or [])],
            assignees=[a.get("login", "") for a in (raw.get("assignees") or [])],
            comments=raw.get("comments", 0),
            created_at=raw.get("created_at") or "",
            updated_at=raw.get("updated_at") or "",
            closed_at=raw.get("closed_at") or "",
            is_pull_request=bool(raw.get("pull_request")),
        ))

    def ListRepoPulls(self, request: Any, context: Any = None) -> pb.ListRepoPullsResponse:
        params: dict[str, Any] = {}
        if request.state:
            params["state"] = request.state
        if request.per_page:
            params["per_page"] = request.per_page
        if request.page:
            params["page"] = request.page

        raw = self._get(f"/repos/{request.owner}/{request.repo}/pulls", params)
        resp = pb.ListRepoPullsResponse()
        for item in raw:
            resp.pulls.append(pb.PullRequest(
                id=item.get("id", 0),
                number=item.get("number", 0),
                title=item.get("title", ""),
                body=item.get("body") or "",
                state=item.get("state", ""),
                html_url=item.get("html_url", ""),
                user_login=(item.get("user") or {}).get("login", ""),
                merged=item.get("merged", False),
                merged_at=item.get("merged_at") or "",
                head_ref=(item.get("head") or {}).get("ref", ""),
                base_ref=(item.get("base") or {}).get("ref", ""),
                labels=[label.get("name", "") for label in (item.get("labels") or [])],
                assignees=[a.get("login", "") for a in (item.get("assignees") or [])],
                created_at=item.get("created_at") or "",
                updated_at=item.get("updated_at") or "",
            ))
        return resp

    def GetPull(self, request: Any, context: Any = None) -> pb.GetPullResponse:
        raw = self._get(f"/repos/{request.owner}/{request.repo}/pulls/{request.pull_number}")
        return pb.GetPullResponse(pull=pb.PullRequest(
            id=raw.get("id", 0),
            number=raw.get("number", 0),
            title=raw.get("title", ""),
            body=raw.get("body") or "",
            state=raw.get("state", ""),
            html_url=raw.get("html_url", ""),
            user_login=(raw.get("user") or {}).get("login", ""),
            merged=raw.get("merged", False),
            merged_at=raw.get("merged_at") or "",
            head_ref=(raw.get("head") or {}).get("ref", ""),
            base_ref=(raw.get("base") or {}).get("ref", ""),
            additions=raw.get("additions", 0),
            deletions=raw.get("deletions", 0),
            changed_files=raw.get("changed_files", 0),
            commits=raw.get("commits", 0),
            comments=raw.get("comments", 0),
            labels=[label.get("name", "") for label in (raw.get("labels") or [])],
            assignees=[a.get("login", "") for a in (raw.get("assignees") or [])],
            created_at=raw.get("created_at") or "",
            updated_at=raw.get("updated_at") or "",
        ))

    def ListRepoLanguages(self, request: Any, context: Any = None) -> pb.ListRepoLanguagesResponse:
        raw = self._get(f"/repos/{request.owner}/{request.repo}/languages")
        resp = pb.ListRepoLanguagesResponse()
        for lang, bytes_count in raw.items():
            resp.languages[lang] = bytes_count
        return resp

    def GetRateLimit(self, request: Any, context: Any = None) -> pb.GetRateLimitResponse:
        raw = self._get("/rate_limit")
        core = (raw.get("resources") or {}).get("core", {})
        return pb.GetRateLimitResponse(
            limit=core.get("limit", 0),
            remaining=core.get("remaining", 0),
            reset=core.get("reset", 0),
            used=core.get("used", 0),
        )
