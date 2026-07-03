# TLS certificates for Nginx

`docker-compose.prod.yml` mounts `./infra/nginx/certs` into the nginx
container read-only, expecting two files:

```
infra/nginx/certs/fullchain.pem
infra/nginx/certs/privkey.pem
```

## Option A — real domain (recommended): Let's Encrypt via certbot

```bash
sudo apt install certbot
sudo certbot certonly --standalone -d your-domain.example
sudo cp /etc/letsencrypt/live/your-domain.example/fullchain.pem infra/nginx/certs/
sudo cp /etc/letsencrypt/live/your-domain.example/privkey.pem infra/nginx/certs/
```

Renews every ~60 days — add a cron job or systemd timer running `certbot
renew` followed by re-copying the two files and `docker compose restart nginx`.

## Option B — no public domain (LAN-only / homelab): self-signed cert

```bash
mkdir -p infra/nginx/certs
openssl req -x509 -nodes -days 825 -newkey rsa:2048 \
  -keyout infra/nginx/certs/privkey.pem \
  -out infra/nginx/certs/fullchain.pem \
  -subj "/CN=leadforge.local"
```

Browsers will warn about the self-signed cert on first visit — that's
expected for LAN-only access; click through once per device, or import the
cert into your OS/browser trust store to silence the warning.

## Option C — Cloudflare Tunnel / Tailscale (no port-forwarding needed)

If you don't want to open ports on your router at all, run this stack
behind a Cloudflare Tunnel or Tailscale Funnel instead — both terminate TLS
for you, so you can skip this certs setup entirely and point nginx's
`listen` directive at plain HTTP on a private interface. See the
"Self-hosting" section of the main README for the tradeoffs.
