"""Slack Web API service implementation -- Invariant Protocol async servicer.

Proxies https://api.slack.com/methods via x-www-form-urlencoded for read-style
endpoints and application/json for write-style endpoints. Returns the raw
response as a google.protobuf.Struct so the upstream JSON shape is preserved.
"""

from __future__ import annotations

import json
import os
from typing import Any

import httpx
from google.protobuf import struct_pb2

DEFAULT_BASE_URL = "https://slack.com/api"


class SlackService:
    """Slack Web API servicer (async)."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        token: str | None = None,
        timeout: float = 15.0,
    ):
        env_base = os.getenv("SLACK_BASE_URL") or DEFAULT_BASE_URL
        self._base_url = (base_url or env_base).rstrip("/")
        self._token = token if token is not None else os.getenv("SLACK_BOT_TOKEN", "")
        self._client = httpx.AsyncClient(timeout=timeout)

    async def aclose(self) -> None:
        await self._client.aclose()

    # -- helpers --

    def _require_token(self) -> str:
        if not self._token:
            raise RuntimeError("SLACK_BOT_TOKEN is not set")
        return self._token

    async def _call_form(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        token = self._require_token()
        endpoint = f"{self._base_url}/{method}"
        # Drop empty values (mimics Go side).
        form = {k: _form_value(v) for k, v in params.items() if _present(v)}
        r = await self._client.post(
            endpoint,
            data=form,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            },
        )
        r.raise_for_status()
        return r.json()

    async def _call_json(self, method: str, body: dict[str, Any]) -> dict[str, Any]:
        token = self._require_token()
        endpoint = f"{self._base_url}/{method}"
        clean = {k: v for k, v in body.items() if _present(v)}
        r = await self._client.post(
            endpoint,
            json=clean,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            },
        )
        r.raise_for_status()
        return r.json()

    @staticmethod
    def _wrap(data: dict[str, Any]) -> struct_pb2.Struct:
        s = struct_pb2.Struct()
        s.update(_jsonable(data))
        return s

    @staticmethod
    def _struct_to_dict(s: Any) -> dict[str, Any]:
        """Convert an incoming Struct field to a plain dict."""
        if s is None:
            return {}
        # protobuf Struct objects support iteration over fields.
        try:
            return json.loads(_struct_to_json(s))
        except Exception:
            return {}

    # -- RPC handlers --

    async def AuthTest(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._wrap(await self._call_form("auth.test", {}))

    async def ChatPostMessage(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        body: dict[str, Any] = {
            "channel": request.channel,
            "text": request.text,
            "thread_ts": request.thread_ts,
            "reply_broadcast": request.reply_broadcast,
            "username": request.username,
            "icon_url": request.icon_url,
            "icon_emoji": request.icon_emoji,
            "parse": request.parse,
            "mrkdwn": request.mrkdwn,
            "unfurl_links": request.unfurl_links,
            "unfurl_media": request.unfurl_media,
        }
        blocks = self._struct_to_dict(request.blocks)
        if blocks:
            body["blocks"] = blocks.get("items", blocks)
        attachments = self._struct_to_dict(request.attachments)
        if attachments:
            body["attachments"] = attachments.get("items", attachments)
        metadata = self._struct_to_dict(request.metadata)
        if metadata:
            body["metadata"] = metadata
        return self._wrap(await self._call_json("chat.postMessage", body))

    async def ChatPostEphemeral(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        body: dict[str, Any] = {
            "channel": request.channel,
            "user": request.user,
            "text": request.text,
            "thread_ts": request.thread_ts,
            "parse": request.parse,
        }
        blocks = self._struct_to_dict(request.blocks)
        if blocks:
            body["blocks"] = blocks.get("items", blocks)
        attachments = self._struct_to_dict(request.attachments)
        if attachments:
            body["attachments"] = attachments.get("items", attachments)
        return self._wrap(await self._call_json("chat.postEphemeral", body))

    async def ChatUpdate(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        body: dict[str, Any] = {
            "channel": request.channel,
            "ts": request.ts,
            "text": request.text,
            "parse": request.parse,
        }
        blocks = self._struct_to_dict(request.blocks)
        if blocks:
            body["blocks"] = blocks.get("items", blocks)
        attachments = self._struct_to_dict(request.attachments)
        if attachments:
            body["attachments"] = attachments.get("items", attachments)
        return self._wrap(await self._call_json("chat.update", body))

    async def ChatDelete(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        body = {
            "channel": request.channel,
            "ts": request.ts,
            "as_user": request.as_user,
        }
        return self._wrap(await self._call_json("chat.delete", body))

    async def ChatScheduleMessage(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        body: dict[str, Any] = {
            "channel": request.channel,
            "post_at": int(request.post_at),
            "text": request.text,
            "thread_ts": request.thread_ts,
            "reply_broadcast": request.reply_broadcast,
        }
        blocks = self._struct_to_dict(request.blocks)
        if blocks:
            body["blocks"] = blocks.get("items", blocks)
        attachments = self._struct_to_dict(request.attachments)
        if attachments:
            body["attachments"] = attachments.get("items", attachments)
        return self._wrap(await self._call_json("chat.scheduleMessage", body))

    async def ChatDeleteScheduledMessage(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        params = {
            "channel": request.channel,
            "scheduled_message_id": request.scheduled_message_id,
        }
        return self._wrap(await self._call_form("chat.deleteScheduledMessage", params))

    async def ChatGetPermalink(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        params = {
            "channel": request.channel,
            "message_ts": request.message_ts,
        }
        return self._wrap(await self._call_form("chat.getPermalink", params))

    async def ConversationsList(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        params = {
            "types": request.types,
            "exclude_archived": request.exclude_archived,
            "limit": request.limit,
            "cursor": request.cursor,
        }
        return self._wrap(await self._call_form("conversations.list", params))

    async def ConversationsHistory(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        params = {
            "channel": request.channel,
            "limit": request.limit,
            "cursor": request.cursor,
            "oldest": request.oldest,
            "latest": request.latest,
            "inclusive": request.inclusive,
        }
        return self._wrap(await self._call_form("conversations.history", params))

    async def ConversationsReplies(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        params = {
            "channel": request.channel,
            "ts": request.ts,
            "limit": request.limit,
            "cursor": request.cursor,
            "oldest": request.oldest,
            "latest": request.latest,
            "inclusive": request.inclusive,
        }
        return self._wrap(await self._call_form("conversations.replies", params))

    async def ConversationsInfo(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        params = {
            "channel": request.channel,
            "include_locale": request.include_locale,
            "include_num_members": request.include_num_members,
        }
        return self._wrap(await self._call_form("conversations.info", params))

    async def ConversationsCreate(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        body = {
            "name": request.name,
            "is_private": request.is_private,
            "team_id": request.team_id,
        }
        return self._wrap(await self._call_json("conversations.create", body))

    async def ConversationsJoin(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._wrap(await self._call_form("conversations.join", {"channel": request.channel}))

    async def ConversationsLeave(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._wrap(await self._call_form("conversations.leave", {"channel": request.channel}))

    async def ConversationsInvite(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        body = {
            "channel": request.channel,
            "users": request.users,
            "force": request.force,
        }
        return self._wrap(await self._call_json("conversations.invite", body))

    async def ConversationsKick(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        params = {"channel": request.channel, "user": request.user}
        return self._wrap(await self._call_form("conversations.kick", params))

    async def ConversationsArchive(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._wrap(await self._call_form("conversations.archive", {"channel": request.channel}))

    async def ConversationsUnarchive(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._wrap(await self._call_form("conversations.unarchive", {"channel": request.channel}))

    async def ConversationsRename(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        params = {"channel": request.channel, "name": request.name}
        return self._wrap(await self._call_form("conversations.rename", params))

    async def ConversationsSetTopic(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        body = {"channel": request.channel, "topic": request.topic}
        return self._wrap(await self._call_json("conversations.setTopic", body))

    async def ConversationsSetPurpose(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        body = {"channel": request.channel, "purpose": request.purpose}
        return self._wrap(await self._call_json("conversations.setPurpose", body))

    async def ConversationsMembers(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        params = {
            "channel": request.channel,
            "limit": request.limit,
            "cursor": request.cursor,
        }
        return self._wrap(await self._call_form("conversations.members", params))

    async def ConversationsOpen(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        body = {
            "users": request.users,
            "channel": request.channel,
            "return_im": request.return_im,
        }
        return self._wrap(await self._call_json("conversations.open", body))

    async def UsersList(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        params = {
            "limit": request.limit,
            "cursor": request.cursor,
            "include_locale": request.include_locale,
        }
        return self._wrap(await self._call_form("users.list", params))

    async def UsersInfo(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        params = {"user": request.user, "include_locale": request.include_locale}
        return self._wrap(await self._call_form("users.info", params))

    async def UsersLookupByEmail(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._wrap(await self._call_form("users.lookupByEmail", {"email": request.email}))

    async def UsersProfileGet(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        params = {"user": request.user, "include_labels": request.include_labels}
        return self._wrap(await self._call_form("users.profile.get", params))

    async def UsersGetPresence(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._wrap(await self._call_form("users.getPresence", {"user": request.user}))

    async def ReactionsAdd(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        params = {
            "name": request.name,
            "channel": request.channel,
            "timestamp": request.timestamp,
        }
        return self._wrap(await self._call_form("reactions.add", params))

    async def ReactionsRemove(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        params = {
            "name": request.name,
            "channel": request.channel,
            "timestamp": request.timestamp,
        }
        return self._wrap(await self._call_form("reactions.remove", params))

    async def ReactionsGet(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        params = {
            "channel": request.channel,
            "timestamp": request.timestamp,
            "full": request.full,
        }
        return self._wrap(await self._call_form("reactions.get", params))

    async def PinsAdd(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        params = {"channel": request.channel, "timestamp": request.timestamp}
        return self._wrap(await self._call_form("pins.add", params))

    async def PinsRemove(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        params = {"channel": request.channel, "timestamp": request.timestamp}
        return self._wrap(await self._call_form("pins.remove", params))

    async def PinsList(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._wrap(await self._call_form("pins.list", {"channel": request.channel}))

    async def SearchMessages(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        params = {
            "query": request.query,
            "sort": request.sort,
            "sort_dir": request.sort_dir,
            "count": request.count,
            "page": request.page,
            "highlight": request.highlight,
        }
        return self._wrap(await self._call_form("search.messages", params))

    async def SearchFiles(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        params = {
            "query": request.query,
            "sort": request.sort,
            "sort_dir": request.sort_dir,
            "count": request.count,
            "page": request.page,
        }
        return self._wrap(await self._call_form("search.files", params))

    async def FilesList(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        params = {
            "user": request.user,
            "channel": request.channel,
            "types": request.types,
            "ts_from": request.ts_from,
            "ts_to": request.ts_to,
            "count": request.count,
            "page": request.page,
        }
        return self._wrap(await self._call_form("files.list", params))

    async def FilesInfo(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        params = {"file": request.file, "count": request.count, "page": request.page}
        return self._wrap(await self._call_form("files.info", params))

    async def FilesDelete(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._wrap(await self._call_form("files.delete", {"file": request.file}))

    async def BookmarksList(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._wrap(await self._call_form("bookmarks.list", {"channel_id": request.channel_id}))

    async def BookmarksAdd(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        body = {
            "channel_id": request.channel_id,
            "title": request.title,
            "type": request.type,
            "link": request.link,
            "emoji": request.emoji,
            "entity_id": request.entity_id,
        }
        return self._wrap(await self._call_json("bookmarks.add", body))

    async def BookmarksRemove(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        body = {
            "channel_id": request.channel_id,
            "bookmark_id": request.bookmark_id,
        }
        return self._wrap(await self._call_json("bookmarks.remove", body))

    async def TeamInfo(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._wrap(await self._call_form("team.info", {"team": request.team}))

    async def EmojiList(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._wrap(
            await self._call_form("emoji.list", {"include_categories": request.include_categories})
        )

    async def ViewsOpen(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        body: dict[str, Any] = {"trigger_id": request.trigger_id}
        view = self._struct_to_dict(request.view)
        if view:
            body["view"] = view
        return self._wrap(await self._call_json("views.open", body))

    async def ViewsPublish(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        body: dict[str, Any] = {"user_id": request.user_id, "hash": request.hash}
        view = self._struct_to_dict(request.view)
        if view:
            body["view"] = view
        return self._wrap(await self._call_json("views.publish", body))


# ---------- helpers -----------------------------------------------------------


def _present(v: Any) -> bool:
    """Return True if the value should be sent to Slack (drop empty/zero)."""
    if v is None:
        return False
    if isinstance(v, str):
        return v != ""
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v != 0
    if isinstance(v, (dict, list)):
        return len(v) > 0
    return True


def _form_value(v: Any) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    return str(v)


def _jsonable(value: Any) -> Any:
    """Coerce non-JSON-safe values (e.g. proto Timestamp) so Struct.update accepts them."""
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    return value


def _struct_to_json(s: Any) -> str:
    """Render a google.protobuf.Struct to JSON for round-trip into a dict."""
    from google.protobuf import json_format

    return json_format.MessageToJson(s, preserving_proto_field_name=True)
