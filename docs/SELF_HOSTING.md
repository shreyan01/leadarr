# Self-Hosting LeadForge on Your Own Computer

This covers running the whole stack — Postgres, Redis, backend, worker,
Qwen2.5-VL, frontend, Nginx — on a machine you own, and (optionally) making
it reachable from outside your home network.

## 1. Hardware reality check

| Component | Requirement | Notes |
|---|---|---|
| Postgres, Redis, backend, worker, frontend, Nginx | 4+ CPU cores, 8 GB RAM | Comfortable on almost any desktop from the last ~8 years |
| Qwen2.5-VL-7B (vision) | NVIDIA GPU with **≥16 GB VRAM** (e.g. RTX 4060 Ti 16GB, 4070 Ti Super, 3090, 4090) | This is the real constraint. 7B at fp16 needs ~14GB just for weights + KV cache headroom |
| Lighthouse / Playwright | Headless Chromium, +1-2GB RAM per concurrent audit | Runs fine on CPU |

**No GPU, or less than 16GB VRAM?** Two options, both already wired into
the compose file:
- Swap `qwen-vl` for **Ollama** running a quantized `qwen2.5vl:7b` (int4)
  — needs ~6-8GB VRAM or can run on CPU (slow: ~30-60s/screenshot instead
  of ~2-5s). The commented-out block in `docker-compose.yml`'s `qwen-vl`
  service shows the swap.
- Point `AI_VISION_PROVIDER` at a hosted API instead (`openai`, `gemini`)
  — you lose the "fully local" property but the rest of the stack is
  unaffected, since vision is behind the same Protocol as everything else.

A typical "run this on a spare desktop" build: any 6+ core CPU, 16-32GB
RAM, one consumer NVIDIA GPU with 16GB+ VRAM, an SSD (Playwright +
screenshots + Postgres do a lot of small writes). This is not a
resource-hungry SaaS — it's sized for an agency running dozens, not
thousands, of audits a day.

## 2. Run it locally first (no internet exposure)

```bash
git clone <your-repo>  # or unzip the delivered archive
cd leadforge
cp .env.example .env
python3 -c "import secrets; print(secrets.token_hex(32))"   # → JWT_SECRET_KEY in .env
# add ANTHROPIC_API_KEY (for chat/report generation) to .env
# GOOGLE_PLACES_API_KEY if you want automated discovery (optional — manual business entry works without it)

docker compose up -d postgres redis
cd backend && pip install -r requirements.txt
alembic revision --autogenerate -m "init schema" && alembic upgrade head
cd ..

docker compose up --build
```

Visit `http://localhost:3000`, register a workspace, and confirm the vision
container downloaded the model (`docker compose logs qwen-vl` — first boot
pulls ~15GB from Hugging Face into the `qwen_model_cache` volume, one-time).

At this point everything works on your LAN — any device on your home
Wi-Fi can reach it at `http://<your-machine's-LAN-IP>:3000`. If that's all
you need (you're the only user, or it's just your household), **you can
stop here** and skip exposing it to the internet at all.

## 3. Making it reachable from outside your home

Three real options, in order of how much I'd recommend them for this
specific app:

### Option A — Cloudflare Tunnel (recommended if you want a public URL)

Best fit here because LeadForge is a standard HTTPS web app (dashboard +
JSON API) with no other protocols to carry, and Cloudflare Tunnel is
built exactly for "expose a web app publicly without opening router
ports." `cloudflared` runs as a small agent that makes an *outbound*
connection to Cloudflare, so you don't touch port forwarding or NAT at
all, and it bypasses CGNAT if your ISP does that.

Tradeoff to know: Cloudflare terminates and can inspect your traffic at
their edge before re-encrypting to your server (that's how their WAF/bot
protection works). For a lead-gen dashboard with business audit data, not
banking data, that's a reasonable tradeoff for most people — but it's
worth knowing it's not literally end-to-end encrypted from browser to
your machine.

Setup:
```bash
# On your host, outside Docker:
brew install cloudflared   # or the Linux package for your distro
cloudflared tunnel login
cloudflared tunnel create leadforge
cloudflared tunnel route dns leadforge leadforge.yourdomain.com
```
Point the tunnel's ingress at `http://localhost:80` (your Nginx from
`docker-compose.prod.yml`), or skip Nginx/TLS entirely and point two
tunnel routes directly at `frontend:3000` and `backend:8000` — Cloudflare
handles the TLS cert for you either way, so `infra/nginx/certs/` becomes
unnecessary in this path. Needs a domain on Cloudflare DNS (cheap, ~$10/yr
if you don't have one).

### Option B — Tailscale (recommended if it's just you / your team, no public link needed)

If nobody outside your household or agency needs to open a public URL —
you just want to check the dashboard from your phone or laptop while
away — Tailscale is simpler and keeps everything private by default.
Install it on the host machine and on your other devices; they join a
private mesh network and reach the box at a stable `100.x.y.z` address or
`leadforge.your-tailnet.ts.net`, with no ports opened on your router at
all. No domain, no cert management (Tailscale can issue you one via
`tailscale cert` if you want, using Let's Encrypt under the hood).
Tailscale Funnel can also make a single service briefly public, but it's
capped (HTTPS-only, routes through their relay, a handful of funnels per
tailnet) — treat it as "share a link with one person," not "run a
public SaaS."

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```
Then just hit `http://<tailscale-ip>:3000` from any enrolled device.

### Option C — Traditional port forwarding + your own domain

Forward ports 80/443 on your router to the host, point DNS at your home
IP (or use a dynamic-DNS service if your ISP doesn't give you a static
one), and run `docker-compose.prod.yml` with real Let's Encrypt certs
(see `infra/nginx/certs.example/README.md`). This is the most "classic"
self-hosting setup and gives you the most control, but it's also the one
most exposed directly to internet scanners, and many residential ISPs
either block inbound 80/443 or sit you behind CGNAT so it doesn't work at
all without a workaround. I'd only reach for this if you specifically
want zero third-party involvement in your traffic path and your ISP
cooperates.

## 4. Production checklist before exposing anything publicly (A or C)

- `ENVIRONMENT=production` in `.env` (disables `/docs`)
- Real, unique `JWT_SECRET_KEY` (never the example value)
- `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build`
  — this is the overlay from Phase 9: gunicorn instead of the dev
  autoreloader, Postgres/Redis ports no longer published to the host,
  the frontend serves the production build instead of `next dev`
- Set a real `EMAIL_FROM_ADDRESS` and configure whichever `EMAIL_PROVIDER`
  you're actually using (SMTP/Resend/SendGrid/SES) — outreach emails will
  fail silently to a fake domain otherwise
- Back up the `postgres_data` volume on a schedule (`pg_dump` in a cron
  container, or just snapshot the volume) — this is business data, not
  disposable
- If you went with Option C, put the app behind Cloudflare's (free) proxy
  even without Tunnel — DNS-only or proxied, either gives you basic
  DDoS absorption in front of a home IP

## 5. Keeping it running

- `docker compose logs -f worker` to watch the audit pipeline process jobs
- `docker compose restart` after pulling code changes; rebuild
  (`--build`) after dependency changes
- Set the containers to restart on boot: `docker-compose.prod.yml`
  already sets `restart: unless-stopped`, so a machine reboot brings
  everything back as long as Docker itself starts on boot
  (`sudo systemctl enable docker` on Linux)
