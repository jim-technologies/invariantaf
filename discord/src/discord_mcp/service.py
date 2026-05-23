"""Discord REST API service implementation -- Invariant Protocol async servicer.

Proxies https://discord.com/developers/docs/reference. Auth uses a bot token
sent as `Authorization: Bot <token>`. Responses are wrapped in
google.protobuf.Struct to preserve the upstream JSON shape.
"""

from __future__ import annotations

import os
import urllib.parse
from typing import Any

import httpx
from google.protobuf import json_format, struct_pb2

DEFAULT_BASE_URL = "https://discord.com/api/v10"


class DiscordService:
    """Discord REST API servicer (async)."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        token: str | None = None,
        timeout: float = 15.0,
    ):
        env_base = os.getenv("DISCORD_BASE_URL") or DEFAULT_BASE_URL
        self._base_url = (base_url or env_base).rstrip("/")
        self._token = token if token is not None else os.getenv("DISCORD_BOT_TOKEN", "")
        self._client = httpx.AsyncClient(timeout=timeout)

    async def aclose(self) -> None:
        await self._client.aclose()

    # -- core HTTP --

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        body: Any = None,
        reason: str = "",
        require_auth: bool = True,
    ) -> Any:
        if require_auth and not self._token:
            raise RuntimeError("DISCORD_BOT_TOKEN is not set")
        headers = {
            "Accept": "application/json",
            "User-Agent": "invariantaf-discord/0.1",
        }
        if require_auth:
            headers["Authorization"] = f"Bot {self._token}"
        if reason:
            headers["X-Audit-Log-Reason"] = reason
        if body is not None:
            headers["Content-Type"] = "application/json"
        url = self._base_url + path
        cleaned_params = _cleanup_query(params or {})
        r = await self._client.request(
            method, url, params=cleaned_params or None, json=body, headers=headers
        )
        if r.status_code >= 400:
            raise RuntimeError(f"discord {method} {path} returned {r.status_code}: {r.text}")
        if r.status_code == 204 or not r.content:
            return {"status": r.status_code}
        return r.json()

    @staticmethod
    def _wrap(data: Any) -> struct_pb2.Struct:
        if isinstance(data, list):
            data = {"items": data}
        if not isinstance(data, dict):
            data = {"value": data}
        s = struct_pb2.Struct()
        s.update(data)
        return s

    @staticmethod
    def _body(struct_field: Any) -> dict[str, Any]:
        if struct_field is None:
            return {}
        try:
            raw = json_format.MessageToJson(struct_field, preserving_proto_field_name=True)
        except Exception:
            return {}
        import json as _json

        return _json.loads(raw) if raw else {}

    @staticmethod
    def _encode_emoji(emoji: str) -> str:
        return urllib.parse.quote(emoji, safe="")

    # -- users --

    async def GetCurrentUser(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._wrap(await self._request("GET", "/users/@me"))

    async def GetUser(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._wrap(await self._request("GET", f"/users/{request.user_id}"))

    async def GetCurrentUserGuilds(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        params = {
            "before": request.before,
            "after": request.after,
            "limit": request.limit,
            "with_counts": request.with_counts,
        }
        return self._wrap(await self._request("GET", "/users/@me/guilds", params=params))

    async def LeaveGuild(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._wrap(await self._request("DELETE", f"/users/@me/guilds/{request.guild_id}"))

    async def CreateDM(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._wrap(
            await self._request("POST", "/users/@me/channels", body={"recipient_id": request.recipient_id})
        )

    # -- guilds --

    async def GetGuild(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        params = {"with_counts": request.with_counts}
        return self._wrap(await self._request("GET", f"/guilds/{request.guild_id}", params=params))

    async def GetGuildPreview(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._wrap(await self._request("GET", f"/guilds/{request.guild_id}/preview"))

    async def ModifyGuild(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._wrap(
            await self._request(
                "PATCH",
                f"/guilds/{request.guild_id}",
                body=self._body(request.body),
                reason=request.reason,
            )
        )

    async def GetGuildChannels(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._wrap(await self._request("GET", f"/guilds/{request.guild_id}/channels"))

    async def CreateGuildChannel(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._wrap(
            await self._request(
                "POST",
                f"/guilds/{request.guild_id}/channels",
                body=self._body(request.body),
                reason=request.reason,
            )
        )

    async def ListGuildMembers(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        params = {"limit": request.limit, "after": request.after}
        return self._wrap(await self._request("GET", f"/guilds/{request.guild_id}/members", params=params))

    async def SearchGuildMembers(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        params = {"query": request.query, "limit": request.limit}
        return self._wrap(
            await self._request("GET", f"/guilds/{request.guild_id}/members/search", params=params)
        )

    async def GetGuildMember(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._wrap(
            await self._request("GET", f"/guilds/{request.guild_id}/members/{request.user_id}")
        )

    async def ModifyGuildMember(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._wrap(
            await self._request(
                "PATCH",
                f"/guilds/{request.guild_id}/members/{request.user_id}",
                body=self._body(request.body),
                reason=request.reason,
            )
        )

    async def RemoveGuildMember(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._wrap(
            await self._request(
                "DELETE",
                f"/guilds/{request.guild_id}/members/{request.user_id}",
                reason=request.reason,
            )
        )

    async def CreateGuildBan(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        body: dict[str, Any] = {}
        if request.delete_message_seconds:
            body["delete_message_seconds"] = int(request.delete_message_seconds)
        return self._wrap(
            await self._request(
                "PUT",
                f"/guilds/{request.guild_id}/bans/{request.user_id}",
                body=body,
                reason=request.reason,
            )
        )

    async def RemoveGuildBan(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._wrap(
            await self._request(
                "DELETE",
                f"/guilds/{request.guild_id}/bans/{request.user_id}",
                reason=request.reason,
            )
        )

    async def GetGuildBans(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        params = {
            "limit": request.limit,
            "before": request.before,
            "after": request.after,
        }
        return self._wrap(await self._request("GET", f"/guilds/{request.guild_id}/bans", params=params))

    async def GetGuildRoles(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._wrap(await self._request("GET", f"/guilds/{request.guild_id}/roles"))

    async def CreateGuildRole(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._wrap(
            await self._request(
                "POST",
                f"/guilds/{request.guild_id}/roles",
                body=self._body(request.body),
                reason=request.reason,
            )
        )

    async def ModifyGuildRole(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._wrap(
            await self._request(
                "PATCH",
                f"/guilds/{request.guild_id}/roles/{request.role_id}",
                body=self._body(request.body),
                reason=request.reason,
            )
        )

    async def DeleteGuildRole(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._wrap(
            await self._request(
                "DELETE",
                f"/guilds/{request.guild_id}/roles/{request.role_id}",
                reason=request.reason,
            )
        )

    async def AddGuildMemberRole(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._wrap(
            await self._request(
                "PUT",
                f"/guilds/{request.guild_id}/members/{request.user_id}/roles/{request.role_id}",
                reason=request.reason,
            )
        )

    async def RemoveGuildMemberRole(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._wrap(
            await self._request(
                "DELETE",
                f"/guilds/{request.guild_id}/members/{request.user_id}/roles/{request.role_id}",
                reason=request.reason,
            )
        )

    async def GetGuildInvites(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._wrap(await self._request("GET", f"/guilds/{request.guild_id}/invites"))

    async def ListGuildEmojis(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._wrap(await self._request("GET", f"/guilds/{request.guild_id}/emojis"))

    async def GetGuildAuditLog(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        params = {
            "user_id": request.user_id,
            "action_type": request.action_type,
            "before": request.before,
            "limit": request.limit,
        }
        return self._wrap(
            await self._request("GET", f"/guilds/{request.guild_id}/audit-logs", params=params)
        )

    # -- channels & messages --

    async def GetChannel(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._wrap(await self._request("GET", f"/channels/{request.channel_id}"))

    async def ModifyChannel(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._wrap(
            await self._request(
                "PATCH",
                f"/channels/{request.channel_id}",
                body=self._body(request.body),
                reason=request.reason,
            )
        )

    async def DeleteChannel(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._wrap(
            await self._request("DELETE", f"/channels/{request.channel_id}", reason=request.reason)
        )

    async def GetChannelMessages(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        params = {
            "around": request.around,
            "before": request.before,
            "after": request.after,
            "limit": request.limit,
        }
        return self._wrap(
            await self._request("GET", f"/channels/{request.channel_id}/messages", params=params)
        )

    async def GetChannelMessage(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._wrap(
            await self._request(
                "GET", f"/channels/{request.channel_id}/messages/{request.message_id}"
            )
        )

    async def CreateMessage(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._wrap(
            await self._request(
                "POST",
                f"/channels/{request.channel_id}/messages",
                body=self._body(request.body),
            )
        )

    async def EditMessage(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._wrap(
            await self._request(
                "PATCH",
                f"/channels/{request.channel_id}/messages/{request.message_id}",
                body=self._body(request.body),
            )
        )

    async def DeleteMessage(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._wrap(
            await self._request(
                "DELETE",
                f"/channels/{request.channel_id}/messages/{request.message_id}",
                reason=request.reason,
            )
        )

    async def CrosspostMessage(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._wrap(
            await self._request(
                "POST",
                f"/channels/{request.channel_id}/messages/{request.message_id}/crosspost",
            )
        )

    async def BulkDeleteMessages(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        ids = list(request.message_ids)
        body = {"messages": ids}
        return self._wrap(
            await self._request(
                "POST",
                f"/channels/{request.channel_id}/messages/bulk-delete",
                body=body,
                reason=request.reason,
            )
        )

    async def CreateReaction(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        path = (
            f"/channels/{request.channel_id}/messages/{request.message_id}"
            f"/reactions/{self._encode_emoji(request.emoji)}/@me"
        )
        return self._wrap(await self._request("PUT", path))

    async def DeleteOwnReaction(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        path = (
            f"/channels/{request.channel_id}/messages/{request.message_id}"
            f"/reactions/{self._encode_emoji(request.emoji)}/@me"
        )
        return self._wrap(await self._request("DELETE", path))

    async def DeleteUserReaction(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        path = (
            f"/channels/{request.channel_id}/messages/{request.message_id}"
            f"/reactions/{self._encode_emoji(request.emoji)}/{request.user_id}"
        )
        return self._wrap(await self._request("DELETE", path))

    async def GetReactions(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        params = {"after": request.after, "limit": request.limit}
        path = (
            f"/channels/{request.channel_id}/messages/{request.message_id}"
            f"/reactions/{self._encode_emoji(request.emoji)}"
        )
        return self._wrap(await self._request("GET", path, params=params))

    async def DeleteAllReactions(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        path = f"/channels/{request.channel_id}/messages/{request.message_id}/reactions"
        if request.emoji:
            path += f"/{self._encode_emoji(request.emoji)}"
        return self._wrap(await self._request("DELETE", path))

    async def TriggerTypingIndicator(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._wrap(await self._request("POST", f"/channels/{request.channel_id}/typing"))

    async def GetPinnedMessages(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._wrap(await self._request("GET", f"/channels/{request.channel_id}/pins"))

    async def PinMessage(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._wrap(
            await self._request(
                "PUT",
                f"/channels/{request.channel_id}/pins/{request.message_id}",
                reason=request.reason,
            )
        )

    async def UnpinMessage(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._wrap(
            await self._request(
                "DELETE",
                f"/channels/{request.channel_id}/pins/{request.message_id}",
                reason=request.reason,
            )
        )

    async def CreateChannelInvite(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._wrap(
            await self._request(
                "POST",
                f"/channels/{request.channel_id}/invites",
                body=self._body(request.body),
                reason=request.reason,
            )
        )

    async def GetChannelInvites(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._wrap(await self._request("GET", f"/channels/{request.channel_id}/invites"))

    async def StartThread(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._wrap(
            await self._request(
                "POST",
                f"/channels/{request.channel_id}/threads",
                body=self._body(request.body),
                reason=request.reason,
            )
        )

    async def JoinThread(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._wrap(await self._request("PUT", f"/channels/{request.channel_id}/thread-members/@me"))

    async def LeaveThread(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._wrap(
            await self._request("DELETE", f"/channels/{request.channel_id}/thread-members/@me")
        )

    async def ListThreadMembers(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        params = {
            "with_member": request.with_member,
            "after": request.after,
            "limit": request.limit,
        }
        return self._wrap(
            await self._request("GET", f"/channels/{request.channel_id}/thread-members", params=params)
        )

    async def ExecuteWebhook(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        params = {"wait": request.wait, "thread_id": request.thread_id}
        return self._wrap(
            await self._request(
                "POST",
                f"/webhooks/{request.webhook_id}/{request.webhook_token}",
                params=params,
                body=self._body(request.body),
                require_auth=False,
            )
        )

    async def DeleteInvite(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._wrap(
            await self._request("DELETE", f"/invites/{request.invite_code}", reason=request.reason)
        )

    async def GetGateway(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._wrap(await self._request("GET", "/gateway", require_auth=False))

    async def GetGatewayBot(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._wrap(await self._request("GET", "/gateway/bot"))


def _cleanup_query(params: dict[str, Any]) -> dict[str, Any]:
    """Drop empty strings, zero ints, and False bools — mimic Go side."""
    out: dict[str, Any] = {}
    for k, v in params.items():
        if v is None:
            continue
        if isinstance(v, str) and v == "":
            continue
        if isinstance(v, bool):
            if v:
                out[k] = "true"
            continue
        if isinstance(v, (int, float)) and v == 0:
            continue
        out[k] = v
    return out
