# Session Log Archive - 2026-W32

---

## 2026-08-04 - Telegram bot proxy recovery

Status: GREEN; bot restored without learner-facing messages.

- Docker reports `egementor-bot-1` in a persistent `Restarting (1)` loop.
- Logs show startup failure at Telegram `setMyCommands`: configured SOCKS proxy
  `45.153.162.248:50100` refuses connections.
- Independent TCP probe to that proxy failed; direct host access to
  `api.telegram.org:443` is also blocked.
- The system proxy had already been changed to `http://50.114.27.115:50100`, but the old
  Docker container retained its creation-time proxy environment.
- Recreated only the `bot` service. Across two health intervals it remains
  `Up (healthy)`, `restarts=0`; the healthcheck is Telegram `getMe`.
- Host-side proxy probes were blocked while the Docker runtime path works; runtime health
  is the authoritative signal here. No learner-facing message was sent.

Open tail: none for this outage; monitor normal polling/delivery.
