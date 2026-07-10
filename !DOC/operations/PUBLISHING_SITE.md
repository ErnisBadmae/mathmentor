# Publishing The Student Site

Goal: let the student open the web UI and visualizations while keeping Postgres,
Qwen, Telegram bot, and MCP inside the local/private network.

The Docker `web` service already serves the SPA and proxies `/api/*` to the
local `api` service. Publish only `http://127.0.0.1:8088` / `web:80`; do not
publish Postgres, Qwen, bot, or MCP.

## Recommended No-Domain Path: Tailscale Serve

Use this when the student's device can be added to the family tailnet. It does
not need a purchased domain and is not public Internet access. Tailscale Serve
routes traffic from other devices in the tailnet to a local service and applies
tailnet ACLs.

1. Install/login Tailscale on the host and the student's device.
2. Start the local stack:

```powershell
docker compose up -d api web bot
```

3. Publish the local web port inside the tailnet:

```powershell
tailscale serve 8088
```

4. Copy the printed `https://<machine>.<tailnet>.ts.net` URL.
5. In `.env`, set:

```text
PUBLIC_FRONTEND_BASE_URL=https://<machine>.<tailnet>.ts.net
VITE_OPERATOR_MODE_AVAILABLE=false
```

6. Rebuild the student-facing web bundle and bot text source:

```powershell
docker compose up -d --build web bot
```

7. Verify:

```powershell
docker compose exec -T -e PUBLIC_API_BASE_URL=http://api:8001 bot python scripts/release_smoke.py
```

## Simpler Tailnet Fallback: Direct Tailscale IP

If Serve is unavailable or hangs in the local Windows environment, use the
machine's Tailscale IP directly. This is still private tailnet access, not public
Internet access.

1. Check the host Tailscale IP:

```powershell
& "C:\Program Files\Tailscale\tailscale.exe" status
```

2. Keep only the web service published on host port `8088`.
3. In `.env`, set:

```text
PUBLIC_FRONTEND_BASE_URL=http://<tailscale-ip>:8088
VITE_OPERATOR_MODE_AVAILABLE=false
```

4. Rebuild web once after changing `VITE_OPERATOR_MODE_AVAILABLE`, then restart
   bot after changing `PUBLIC_FRONTEND_BASE_URL`:

```powershell
docker compose up -d --build web
docker compose up -d bot
```

5. Verify from the host and from the student's tailnet device:

```powershell
curl.exe http://<tailscale-ip>:8088/api/health
```

Current local pilot example after the 2026-07-09 publish attempt:

```text
PUBLIC_FRONTEND_BASE_URL=http://100.113.226.52:8088
```

## Temporary No-Domain Public Link: Cloudflare Quick Tunnel

Use this only for a short test session when installing Tailscale on the student
device is inconvenient. Cloudflare Quick Tunnels create a random
`trycloudflare.com` hostname and are documented by Cloudflare as testing and
development only, not production.

1. Set `.env` before rebuilding:

```text
VITE_OPERATOR_MODE_AVAILABLE=false
```

2. Rebuild web:

```powershell
docker compose up -d --build web
```

3. Run:

```powershell
cloudflared tunnel --url http://localhost:8088
```

4. Copy the printed `https://*.trycloudflare.com` URL and set:

```text
PUBLIC_FRONTEND_BASE_URL=https://<random>.trycloudflare.com
```

5. Rebuild only the bot if Telegram should send this URL:

```powershell
docker compose up -d --build bot
```

6. Stop the tunnel when the session ends.

## Domain Path Later: Cloudflare Tunnel + Access

When we want a stable family URL without installing Tailscale on every device,
use a real domain with Cloudflare Tunnel + Cloudflare Access. Access should sit
in front of the same `web` origin and restrict users by email. This is the
cleanest stable path, but it does require a domain.

## Security Rules

- Never expose Qwen / llama.cpp / vLLM ports.
- Never expose Postgres.
- Never expose MCP.
- Publish one origin only: the `web` service on port `8088`.
- Keep `api` and `postgres` host bindings on `127.0.0.1` only; `web` reaches
  `api` through the Docker network.
- Keep `VITE_OPERATOR_MODE_AVAILABLE=false` for student/public links.
- Treat Quick Tunnel and Funnel-style public URLs as visible to anyone who has
  the link unless an authentication layer is in front.
