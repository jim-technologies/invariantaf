# discord-mcp

Discord REST API as an Invariant-protocol-powered MCP/CLI/HTTP/gRPC server.

## Coverage

~50 RPCs across the core REST surface:

- **Users**: GetCurrentUser, GetUser, GetCurrentUserGuilds, LeaveGuild, CreateDM
- **Guilds**: GetGuild, GetGuildPreview, ModifyGuild, ListGuildEmojis, GetGuildAuditLog
- **Guild channels**: GetGuildChannels, CreateGuildChannel
- **Guild members**: ListGuildMembers, SearchGuildMembers, GetGuildMember, ModifyGuildMember, RemoveGuildMember, AddGuildMemberRole, RemoveGuildMemberRole
- **Guild bans/roles**: CreateGuildBan, RemoveGuildBan, GetGuildBans, GetGuildRoles, CreateGuildRole, ModifyGuildRole, DeleteGuildRole
- **Channels**: GetChannel, ModifyChannel, DeleteChannel, GetChannelInvites, CreateChannelInvite, TriggerTypingIndicator
- **Messages**: GetChannelMessages, GetChannelMessage, CreateMessage, EditMessage, DeleteMessage, CrosspostMessage, BulkDeleteMessages
- **Pins**: GetPinnedMessages, PinMessage, UnpinMessage
- **Reactions**: CreateReaction, DeleteOwnReaction, DeleteUserReaction, GetReactions, DeleteAllReactions
- **Threads**: StartThread, JoinThread, LeaveThread, ListThreadMembers
- **Webhooks**: ExecuteWebhook (unauthenticated)
- **Invites**: GetGuildInvites, DeleteInvite
- **Gateway**: GetGateway, GetGatewayBot

## Auth

Set `DISCORD_BOT_TOKEN` to your bot token (sent as `Authorization: Bot <token>`).
`DISCORD_BASE_URL` overrides the API host (default `https://discord.com/api/v10`).

`ExecuteWebhook` and `GetGateway` do not require auth.

Audit-log reasons: any RPC that takes a `reason` field forwards it as the
`X-Audit-Log-Reason` header.

## Quick start

```bash
export DISCORD_BOT_TOKEN=...
uv run python main.py            # MCP stdio
uv run python main.py --http 8080
uv run python main.py --cli DiscordService.GetCurrentUser

go run . --http 8080
go run . --cli DiscordService.GetChannelMessages -r '{"channel_id": "...", "limit": 10}'
```

## Regenerate

```bash
make generate
make test
```

## Notes

- Free-form bodies (e.g. `CreateMessage`, `ModifyGuild`) are passed through
  as `google.protobuf.Struct` so callers can use the full Discord schema
  without re-defining every field locally.
- File uploads aren't covered — Discord uses multipart for those, which is
  better served by a dedicated tool.

## Source

- [Discord REST API reference](https://discord.com/developers/docs/reference)
