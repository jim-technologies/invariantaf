"""Telegram Bot API service implementation -- Invariant Protocol async servicer.

Proxies https://core.telegram.org/bots/api. Auth is via the bot token embedded
in the path (https://api.telegram.org/bot<TOKEN>/<method>). Responses are
unwrapped from the `{ok, result}` envelope and returned as
google.protobuf.Struct.
"""

from __future__ import annotations

import json
import os
from typing import Any

import httpx
from google.protobuf import json_format, struct_pb2

DEFAULT_BASE_URL = "https://api.telegram.org"


class TelegramService:
    """Telegram Bot API servicer (async)."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        token: str | None = None,
        timeout: float = 30.0,
    ):
        env_base = os.getenv("TELEGRAM_BASE_URL") or DEFAULT_BASE_URL
        self._base_url = (base_url or env_base).rstrip("/")
        self._token = token if token is not None else os.getenv("TELEGRAM_BOT_TOKEN", "")
        self._client = httpx.AsyncClient(timeout=timeout)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _call(self, method: str, body: dict[str, Any] | None = None) -> Any:
        if not self._token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")
        url = f"{self._base_url}/bot{self._token}/{method}"
        clean = _drop_zero(body or {})
        r = await self._client.post(
            url,
            json=clean if clean else None,
            headers={"Accept": "application/json"},
        )
        if r.status_code >= 400:
            raise RuntimeError(f"telegram {method} returned {r.status_code}: {r.text}")
        env = r.json()
        if not env.get("ok"):
            desc = env.get("description") or "unknown error"
            raise RuntimeError(f"telegram {method}: {desc}")
        return env.get("result", env)

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
    def _struct(field: Any) -> Any:
        """Convert a Struct field to a dict (or unwrap items list)."""
        if field is None:
            return None
        try:
            raw = json_format.MessageToJson(field, preserving_proto_field_name=True)
        except Exception:
            return None
        if not raw:
            return None
        v = json.loads(raw)
        if isinstance(v, dict) and "items" in v and len(v) == 1:
            return v["items"]
        return v if v else None

    # -- handlers --

    async def GetMe(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._wrap(await self._call("getMe"))

    async def LogOut(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._wrap(await self._call("logOut"))

    async def Close(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._wrap(await self._call("close"))

    async def SendMessage(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        body: dict[str, Any] = {
            "chat_id": request.chat_id,
            "text": request.text,
            "parse_mode": request.parse_mode,
            "disable_web_page_preview": request.disable_web_page_preview,
            "disable_notification": request.disable_notification,
            "protect_content": request.protect_content,
            "reply_to_message_id": request.reply_to_message_id,
            "allow_sending_without_reply": request.allow_sending_without_reply,
            "message_thread_id": request.message_thread_id,
            "business_connection_id": request.business_connection_id,
        }
        if (v := self._struct(request.entities)) is not None:
            body["entities"] = v
        if (v := self._struct(request.reply_markup)) is not None:
            body["reply_markup"] = v
        return self._wrap(await self._call("sendMessage", body))

    async def ForwardMessage(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        body = {
            "chat_id": request.chat_id,
            "from_chat_id": request.from_chat_id,
            "message_id": request.message_id,
            "disable_notification": request.disable_notification,
            "protect_content": request.protect_content,
            "message_thread_id": request.message_thread_id,
        }
        return self._wrap(await self._call("forwardMessage", body))

    async def CopyMessage(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        body: dict[str, Any] = {
            "chat_id": request.chat_id,
            "from_chat_id": request.from_chat_id,
            "message_id": request.message_id,
            "caption": request.caption,
            "parse_mode": request.parse_mode,
            "disable_notification": request.disable_notification,
            "protect_content": request.protect_content,
            "reply_to_message_id": request.reply_to_message_id,
        }
        if (v := self._struct(request.reply_markup)) is not None:
            body["reply_markup"] = v
        return self._wrap(await self._call("copyMessage", body))

    async def _send_media(
        self,
        method: str,
        request: Any,
        *,
        primary_field: str,
        primary_value: str,
        extra: dict[str, Any] | None = None,
    ) -> struct_pb2.Struct:
        body: dict[str, Any] = {
            "chat_id": request.chat_id,
            primary_field: primary_value,
            "caption": getattr(request, "caption", ""),
            "parse_mode": getattr(request, "parse_mode", ""),
            "disable_notification": request.disable_notification,
            "protect_content": request.protect_content,
            "reply_to_message_id": request.reply_to_message_id,
        }
        if extra:
            body.update(extra)
        if (v := self._struct(getattr(request, "reply_markup", None))) is not None:
            body["reply_markup"] = v
        return self._wrap(await self._call(method, body))

    async def SendPhoto(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return await self._send_media(
            "sendPhoto", request,
            primary_field="photo", primary_value=request.photo,
            extra={"has_spoiler": request.has_spoiler},
        )

    async def SendAudio(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return await self._send_media(
            "sendAudio", request,
            primary_field="audio", primary_value=request.audio,
            extra={
                "duration": request.duration,
                "performer": request.performer,
                "title": request.title,
            },
        )

    async def SendDocument(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return await self._send_media(
            "sendDocument", request,
            primary_field="document", primary_value=request.document,
            extra={"disable_content_type_detection": request.disable_content_type_detection},
        )

    async def SendVideo(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return await self._send_media(
            "sendVideo", request,
            primary_field="video", primary_value=request.video,
            extra={
                "duration": request.duration,
                "width": request.width,
                "height": request.height,
                "has_spoiler": request.has_spoiler,
                "supports_streaming": request.supports_streaming,
            },
        )

    async def SendAnimation(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return await self._send_media(
            "sendAnimation", request,
            primary_field="animation", primary_value=request.animation,
            extra={
                "duration": request.duration,
                "width": request.width,
                "height": request.height,
                "has_spoiler": request.has_spoiler,
            },
        )

    async def SendVoice(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return await self._send_media(
            "sendVoice", request,
            primary_field="voice", primary_value=request.voice,
            extra={"duration": request.duration},
        )

    async def SendVideoNote(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return await self._send_media(
            "sendVideoNote", request,
            primary_field="video_note", primary_value=request.video_note,
            extra={"duration": request.duration, "length": request.length},
        )

    async def SendLocation(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        body: dict[str, Any] = {
            "chat_id": request.chat_id,
            "latitude": request.latitude,
            "longitude": request.longitude,
            "horizontal_accuracy": request.horizontal_accuracy,
            "live_period": request.live_period,
            "heading": request.heading,
            "proximity_alert_radius": request.proximity_alert_radius,
            "disable_notification": request.disable_notification,
            "protect_content": request.protect_content,
            "reply_to_message_id": request.reply_to_message_id,
        }
        if (v := self._struct(request.reply_markup)) is not None:
            body["reply_markup"] = v
        return self._wrap(await self._call("sendLocation", body))

    async def SendVenue(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        body: dict[str, Any] = {
            "chat_id": request.chat_id,
            "latitude": request.latitude,
            "longitude": request.longitude,
            "title": request.title,
            "address": request.address,
            "foursquare_id": request.foursquare_id,
            "foursquare_type": request.foursquare_type,
            "google_place_id": request.google_place_id,
            "google_place_type": request.google_place_type,
            "disable_notification": request.disable_notification,
            "protect_content": request.protect_content,
            "reply_to_message_id": request.reply_to_message_id,
        }
        if (v := self._struct(request.reply_markup)) is not None:
            body["reply_markup"] = v
        return self._wrap(await self._call("sendVenue", body))

    async def SendContact(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        body: dict[str, Any] = {
            "chat_id": request.chat_id,
            "phone_number": request.phone_number,
            "first_name": request.first_name,
            "last_name": request.last_name,
            "vcard": request.vcard,
            "disable_notification": request.disable_notification,
            "protect_content": request.protect_content,
            "reply_to_message_id": request.reply_to_message_id,
        }
        if (v := self._struct(request.reply_markup)) is not None:
            body["reply_markup"] = v
        return self._wrap(await self._call("sendContact", body))

    async def SendPoll(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        body: dict[str, Any] = {
            "chat_id": request.chat_id,
            "question": request.question,
            "is_anonymous": request.is_anonymous,
            "type": request.type,
            "allows_multiple_answers": request.allows_multiple_answers,
            "correct_option_id": request.correct_option_id,
            "explanation": request.explanation,
            "open_period": request.open_period,
            "close_date": request.close_date,
            "is_closed": request.is_closed,
            "disable_notification": request.disable_notification,
            "protect_content": request.protect_content,
            "reply_to_message_id": request.reply_to_message_id,
        }
        if (v := self._struct(request.options)) is not None:
            body["options"] = v
        if (v := self._struct(request.reply_markup)) is not None:
            body["reply_markup"] = v
        return self._wrap(await self._call("sendPoll", body))

    async def SendDice(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        body: dict[str, Any] = {
            "chat_id": request.chat_id,
            "emoji": request.emoji,
            "disable_notification": request.disable_notification,
            "protect_content": request.protect_content,
            "reply_to_message_id": request.reply_to_message_id,
        }
        if (v := self._struct(request.reply_markup)) is not None:
            body["reply_markup"] = v
        return self._wrap(await self._call("sendDice", body))

    async def SendChatAction(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        body = {
            "chat_id": request.chat_id,
            "action": request.action,
            "message_thread_id": request.message_thread_id,
        }
        return self._wrap(await self._call("sendChatAction", body))

    async def EditMessageText(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        body: dict[str, Any] = {
            "chat_id": request.chat_id,
            "message_id": request.message_id,
            "inline_message_id": request.inline_message_id,
            "text": request.text,
            "parse_mode": request.parse_mode,
            "disable_web_page_preview": request.disable_web_page_preview,
        }
        if (v := self._struct(request.reply_markup)) is not None:
            body["reply_markup"] = v
        return self._wrap(await self._call("editMessageText", body))

    async def EditMessageCaption(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        body: dict[str, Any] = {
            "chat_id": request.chat_id,
            "message_id": request.message_id,
            "inline_message_id": request.inline_message_id,
            "caption": request.caption,
            "parse_mode": request.parse_mode,
        }
        if (v := self._struct(request.reply_markup)) is not None:
            body["reply_markup"] = v
        return self._wrap(await self._call("editMessageCaption", body))

    async def EditMessageReplyMarkup(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        body: dict[str, Any] = {
            "chat_id": request.chat_id,
            "message_id": request.message_id,
            "inline_message_id": request.inline_message_id,
        }
        if (v := self._struct(request.reply_markup)) is not None:
            body["reply_markup"] = v
        return self._wrap(await self._call("editMessageReplyMarkup", body))

    async def DeleteMessage(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        body = {"chat_id": request.chat_id, "message_id": request.message_id}
        return self._wrap(await self._call("deleteMessage", body))

    async def DeleteMessages(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        body = {
            "chat_id": request.chat_id,
            "message_ids": list(request.message_ids),
        }
        return self._wrap(await self._call("deleteMessages", body))

    async def GetChat(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._wrap(await self._call("getChat", {"chat_id": request.chat_id}))

    async def GetChatAdministrators(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._wrap(await self._call("getChatAdministrators", {"chat_id": request.chat_id}))

    async def GetChatMemberCount(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._wrap(await self._call("getChatMemberCount", {"chat_id": request.chat_id}))

    async def GetChatMember(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        body = {"chat_id": request.chat_id, "user_id": request.user_id}
        return self._wrap(await self._call("getChatMember", body))

    async def BanChatMember(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        body = {
            "chat_id": request.chat_id,
            "user_id": request.user_id,
            "until_date": request.until_date,
            "revoke_messages": request.revoke_messages,
        }
        return self._wrap(await self._call("banChatMember", body))

    async def UnbanChatMember(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        body = {
            "chat_id": request.chat_id,
            "user_id": request.user_id,
            "only_if_banned": request.only_if_banned,
        }
        return self._wrap(await self._call("unbanChatMember", body))

    async def RestrictChatMember(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        body: dict[str, Any] = {
            "chat_id": request.chat_id,
            "user_id": request.user_id,
            "use_independent_chat_permissions": request.use_independent_chat_permissions,
            "until_date": request.until_date,
        }
        if (v := self._struct(request.permissions)) is not None:
            body["permissions"] = v
        return self._wrap(await self._call("restrictChatMember", body))

    async def PromoteChatMember(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        body: dict[str, Any] = {
            "chat_id": request.chat_id,
            "user_id": request.user_id,
        }
        for k in (
            "is_anonymous", "can_manage_chat", "can_post_messages", "can_edit_messages",
            "can_delete_messages", "can_manage_video_chats", "can_restrict_members",
            "can_promote_members", "can_change_info", "can_invite_users",
            "can_pin_messages", "can_manage_topics", "can_post_stories",
            "can_edit_stories", "can_delete_stories",
        ):
            body[k] = getattr(request, k)
        return self._wrap(await self._call("promoteChatMember", body))

    async def SetChatTitle(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        body = {"chat_id": request.chat_id, "title": request.title}
        return self._wrap(await self._call("setChatTitle", body))

    async def SetChatDescription(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        body = {"chat_id": request.chat_id, "description": request.description}
        return self._wrap(await self._call("setChatDescription", body))

    async def PinChatMessage(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        body = {
            "chat_id": request.chat_id,
            "message_id": request.message_id,
            "disable_notification": request.disable_notification,
            "business_connection_id": request.business_connection_id,
        }
        return self._wrap(await self._call("pinChatMessage", body))

    async def UnpinChatMessage(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        body = {
            "chat_id": request.chat_id,
            "message_id": request.message_id,
            "business_connection_id": request.business_connection_id,
        }
        return self._wrap(await self._call("unpinChatMessage", body))

    async def UnpinAllChatMessages(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._wrap(await self._call("unpinAllChatMessages", {"chat_id": request.chat_id}))

    async def LeaveChat(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._wrap(await self._call("leaveChat", {"chat_id": request.chat_id}))

    async def GetUpdates(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        body: dict[str, Any] = {
            "offset": request.offset,
            "limit": request.limit,
            "timeout": request.timeout,
        }
        if (v := self._struct(request.allowed_updates)) is not None:
            body["allowed_updates"] = v
        return self._wrap(await self._call("getUpdates", body))

    async def SetWebhook(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        body: dict[str, Any] = {
            "url": request.url,
            "certificate": request.certificate,
            "ip_address": request.ip_address,
            "max_connections": request.max_connections,
            "drop_pending_updates": request.drop_pending_updates,
            "secret_token": request.secret_token,
        }
        if (v := self._struct(request.allowed_updates)) is not None:
            body["allowed_updates"] = v
        return self._wrap(await self._call("setWebhook", body))

    async def DeleteWebhook(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        body = {"drop_pending_updates": request.drop_pending_updates}
        return self._wrap(await self._call("deleteWebhook", body))

    async def GetWebhookInfo(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._wrap(await self._call("getWebhookInfo"))

    async def GetFile(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._wrap(await self._call("getFile", {"file_id": request.file_id}))

    async def AnswerCallbackQuery(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        body = {
            "callback_query_id": request.callback_query_id,
            "text": request.text,
            "show_alert": request.show_alert,
            "url": request.url,
            "cache_time": request.cache_time,
        }
        return self._wrap(await self._call("answerCallbackQuery", body))

    async def SetMyCommands(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        body: dict[str, Any] = {"language_code": request.language_code}
        if (v := self._struct(request.commands)) is not None:
            body["commands"] = v
        if (v := self._struct(request.scope)) is not None:
            body["scope"] = v
        return self._wrap(await self._call("setMyCommands", body))

    async def GetMyCommands(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        body: dict[str, Any] = {"language_code": request.language_code}
        if (v := self._struct(request.scope)) is not None:
            body["scope"] = v
        return self._wrap(await self._call("getMyCommands", body))

    async def DeleteMyCommands(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        body: dict[str, Any] = {"language_code": request.language_code}
        if (v := self._struct(request.scope)) is not None:
            body["scope"] = v
        return self._wrap(await self._call("deleteMyCommands", body))

    async def SetMyDescription(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        body = {
            "description": request.description,
            "language_code": request.language_code,
        }
        return self._wrap(await self._call("setMyDescription", body))

    async def SetMyShortDescription(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        body = {
            "short_description": request.short_description,
            "language_code": request.language_code,
        }
        return self._wrap(await self._call("setMyShortDescription", body))

    async def SendInvoice(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        body: dict[str, Any] = {
            "chat_id": request.chat_id,
            "title": request.title,
            "description": request.description,
            "payload": request.payload,
            "provider_token": request.provider_token,
            "currency": request.currency,
            "max_tip_amount": request.max_tip_amount,
            "start_parameter": request.start_parameter,
            "provider_data": request.provider_data,
            "photo_url": request.photo_url,
            "photo_size": request.photo_size,
            "photo_width": request.photo_width,
            "photo_height": request.photo_height,
            "need_name": request.need_name,
            "need_phone_number": request.need_phone_number,
            "need_email": request.need_email,
            "need_shipping_address": request.need_shipping_address,
            "send_phone_number_to_provider": request.send_phone_number_to_provider,
            "send_email_to_provider": request.send_email_to_provider,
            "is_flexible": request.is_flexible,
            "disable_notification": request.disable_notification,
            "protect_content": request.protect_content,
            "reply_to_message_id": request.reply_to_message_id,
        }
        if (v := self._struct(request.prices)) is not None:
            body["prices"] = v
        if (v := self._struct(request.suggested_tip_amounts)) is not None:
            body["suggested_tip_amounts"] = v
        if (v := self._struct(request.reply_markup)) is not None:
            body["reply_markup"] = v
        return self._wrap(await self._call("sendInvoice", body))

    async def ExportChatInviteLink(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._wrap(await self._call("exportChatInviteLink", {"chat_id": request.chat_id}))

    async def CreateChatInviteLink(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        body = {
            "chat_id": request.chat_id,
            "name": request.name,
            "expire_date": request.expire_date,
            "member_limit": request.member_limit,
            "creates_join_request": request.creates_join_request,
        }
        return self._wrap(await self._call("createChatInviteLink", body))


def _drop_zero(d: dict[str, Any]) -> dict[str, Any]:
    """Telegram expects optional params to be absent rather than zero-valued."""
    out: dict[str, Any] = {}
    for k, v in d.items():
        if v is None:
            continue
        if isinstance(v, str) and v == "":
            continue
        if isinstance(v, bool):
            if v:
                out[k] = True
            continue
        if isinstance(v, (int, float)) and v == 0:
            continue
        if isinstance(v, (list, dict)) and len(v) == 0:
            continue
        out[k] = v
    return out
