# slack-mcp

Slack Web API as an Invariant-protocol-powered MCP/CLI/HTTP/gRPC server.

## Coverage

Roughly 45 RPCs across the most-used surface:

- **auth.test, team.info, emoji.list** — identity & workspace metadata
- **chat.\*** — postMessage, postEphemeral, update, delete, scheduleMessage, deleteScheduledMessage, getPermalink
- **conversations.\*** — list, history, replies, info, create, join/leave, invite/kick, archive/unarchive, rename, setTopic/setPurpose, members, open
- **users.\*** — list, info, lookupByEmail, profile.get, getPresence
- **reactions.\*** — add, remove, get
- **pins.\*** — add, remove, list
- **search.\*** — messages, files (user token only)
- **files.\*** — list, info, delete (upload is intentionally omitted — it requires multipart and is better suited to a dedicated tool)
- **bookmarks.\*** — list, add, remove
- **views.\*** — open, publish (modals + Home tab)

## Auth

Set `SLACK_BOT_TOKEN` to a bot user OAuth token (`xoxb-...`). For search.\* you
need a user token (`xoxp-...`).

`SLACK_BASE_URL` can override the API host (default `https://slack.com/api`),
useful for local mocks.

## Quick start

```bash
# Python (async)
export SLACK_BOT_TOKEN=xoxb-...
uv run python main.py            # MCP stdio
uv run python main.py --http 8080
uv run python main.py --cli SlackService.AuthTest

# Go
go run . --http 8080
go run . --cli SlackService.ConversationsList -r '{"limit": 5}'
```

## Regenerate

```bash
make generate    # buf generate + descriptor
make test        # go + python
```

## Notes

- Responses are returned as `google.protobuf.Struct` so the Slack JSON shape
  is preserved 1:1 — useful since the surface is large and the field
  population varies per RPC.
- `files.upload` is omitted because it's the only multipart endpoint; add a
  dedicated upload helper if needed.
- Some RPCs (`search.*`, certain admin endpoints) require user tokens and are
  not invocable with a bot token alone — they're still wired so a user-token
  build can reach them.

## Source

- [Slack Web API methods](https://api.slack.com/methods)
- Auth: <https://api.slack.com/authentication/token-types>
