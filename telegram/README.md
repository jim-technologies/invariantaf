# telegram-mcp

Telegram Bot API as an Invariant-protocol-powered MCP/CLI/HTTP/gRPC server.

## Coverage

~50 RPCs across the core Bot API surface:

- **Identity**: GetMe, LogOut, Close
- **Messages**: SendMessage, ForwardMessage, CopyMessage, EditMessageText, EditMessageCaption, EditMessageReplyMarkup, DeleteMessage, DeleteMessages
- **Media**: SendPhoto, SendAudio, SendDocument, SendVideo, SendAnimation, SendVoice, SendVideoNote
- **Location/contact**: SendLocation, SendVenue, SendContact
- **Engagement**: SendPoll, SendDice, SendChatAction
- **Chats**: GetChat, GetChatAdministrators, GetChatMemberCount, GetChatMember, BanChatMember, UnbanChatMember, RestrictChatMember, PromoteChatMember, SetChatTitle, SetChatDescription, PinChatMessage, UnpinChatMessage, UnpinAllChatMessages, LeaveChat
- **Invites**: ExportChatInviteLink, CreateChatInviteLink
- **Updates / webhook**: GetUpdates, SetWebhook, DeleteWebhook, GetWebhookInfo
- **Misc**: GetFile, AnswerCallbackQuery, SetMyCommands, GetMyCommands, DeleteMyCommands, SetMyDescription, SetMyShortDescription, SendInvoice

## Auth

Set `TELEGRAM_BOT_TOKEN`. The token is sent in the path (`/bot<token>/<method>`).
`TELEGRAM_BASE_URL` overrides the API host (default `https://api.telegram.org`).

## Quick start

```bash
export TELEGRAM_BOT_TOKEN=...
uv run python main.py            # MCP stdio
uv run python main.py --http 8080
uv run python main.py --cli TelegramService.GetMe

go run . --http 8080
go run . --cli TelegramService.SendMessage -r '{"chat_id":"@channel","text":"hi"}'
```

## Regenerate

```bash
make generate
make test
```

## Notes

- File-uploads via multipart aren't covered. Pass URLs or `file_id`s for media.
- Optional zero-valued fields are dropped from the request body — Telegram
  expects "absent" rather than "empty"/"zero" for optionals.
- The `{ok, result}` envelope is unwrapped automatically; failures with
  `ok: false` raise the upstream `description` as an error.
- Reply markups, entities, poll options, and similar nested JSON objects are
  carried as `google.protobuf.Struct` so callers can use the full Telegram
  schema without re-defining every nested type here.

## Source

- [Telegram Bot API methods](https://core.telegram.org/bots/api)
