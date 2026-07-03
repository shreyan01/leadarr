# LeadForge

Automated local-business discovery, passive website auditing, AI-generated
lead scoring, and outreach — for agencies. See `docs/` for the full design:

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — layering, pipeline, guardrails
- [`docs/DATABASE_SCHEMA.md`](docs/DATABASE_SCHEMA.md) — full Postgres schema
- [`docs/API_SPEC.md`](docs/API_SPEC.md) — REST API surface
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — phased build plan
- [`docs/SELF_HOSTING.md`](docs/SELF_HOSTING.md) — running this on your own
  hardware, hardware sizing, and exposing it beyond your LAN

## What ships in this delivery (Phases 1–9)

- Repo scaffold following the clean-architecture layout in the architecture doc.
- Docker Compose: Postgres, Redis, backend, Celery worker, Next.js frontend,
  and a **locally hosted Qwen2.5-VL** vision server (vLLM,
  OpenAI-compatible `/v1/chat/completions` with image input) — vision never
  calls a hosted API; model weights are pulled once into a named volume.
  A separate `docker-compose.prod.yml` overlay adds gunicorn, a built
  frontend, and an Nginx TLS-terminating reverse proxy for production.
- Full SQLAlchemy model set matching `DATABASE_SCHEMA.md`, wired for Alembic
  autogenerate.
- JWT auth (access + refresh) with argon2 password hashing and RBAC
  (`owner/admin/analyst/viewer`), register/login/refresh/me endpoints,
  Redis-backed rate limiting on auth and audit/discovery-trigger endpoints.
- AI provider abstraction (`ChatProvider` / `VisionProvider` / `EmbeddingProvider`
  Protocols) with working Anthropic and OpenAI-compatible chat adapters and a
  working local Qwen2.5-VL vision adapter, resolved via a registry from `.env`.
- The full audit pipeline, chained in Celery: **discover → validate → crawl
  → Lighthouse → accessibility → security → vision → lead scoring → AI
  report → outreach email draft**. `PassiveHttpClient` is the single
  chokepoint the security-audit module uses — GET/HEAD only, no
  request-body method exists, so the passive-only constraint is enforced by
  the type system, not just policy.
- Email sending behind one interface with working SMTP, Resend, SendGrid,
  and AWS SES adapters, plus a lightweight CRM (campaign kanban, notes,
  follow-up dates).
- A Next.js 14 dashboard: auth, business list/detail (full audit report
  viewer), lead board, campaign kanban, dark mode by default.
- Health/monitoring endpoints (`/health`, `/health/db`, `/health/workers`,
  `/health/queue`, `/monitoring/stats`) and structured JSON logging with a
  request-ID on every response.
- Security-headers middleware on our own API (the same hygiene the audit
  module checks for on target sites, applied to ourselves).
- Test coverage: 85 unit tests (pure logic — scoring, parsing, header
  analysis, contrast math, etc.) plus 11 integration tests exercising the
  real FastAPI app end-to-end against fake in-memory repositories (no DB
  needed) — 96 tests total, all passing.
- A Locust load-test script for the dashboard's read-heavy endpoints
  (`infra/load-test/locustfile.py`).

Not yet implemented (see `docs/ROADMAP.md`): multi-tenancy enforcement,
white-label mode, public API, browser extension, redesign-mockup generation.

## Local setup

### Backend

```bash
cp .env.example .env
python -c "import secrets; print(secrets.token_hex(32))"   # paste into JWT_SECRET_KEY
# add ANTHROPIC_API_KEY (or another AI_CHAT_PROVIDER's key) to .env

docker compose up -d postgres redis
cd backend
pip install -r requirements.txt
alembic revision --autogenerate -m "init schema"
alembic upgrade head
cd ..

docker compose up --build
```

Backend: http://localhost:8000/docs

### Frontend

```bash
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
```

Dashboard: http://localhost:3000 — register a workspace, then discover
businesses from the Businesses page to get started.

### Running the vision model locally

The `qwen-vl` service in `docker-compose.yml` runs vLLM serving
`Qwen/Qwen2.5-VL-7B-Instruct` and requires an NVIDIA GPU + the NVIDIA
Container Toolkit. On `docker compose up`, weights download once into the
`qwen_model_cache` volume — no API key, no external vision call. If you don't
have a GPU, swap that service for Ollama (commented alternative is in the
compose file) and pull `qwen2.5vl:7b` instead.

### Tests

```bash
cd backend
pytest --cov=app tests/            # unit + integration (no DB required for integration tests)
```

### Load testing

```bash
pip install locust
locust -f infra/load-test/locustfile.py --host http://localhost:8000
# open http://localhost:8089 to configure and start
```

### Production deployment

```bash
cp infra/nginx/certs.example/README.md infra/nginx/certs/README.md  # see that file for cert setup
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

This overlay swaps `uvicorn --reload` for gunicorn+uvicorn workers, builds
the frontend instead of running its dev server, removes bind mounts and
exposed DB/Redis ports, and fronts everything with Nginx terminating TLS.
Set `ENVIRONMENT=production` in `.env` too (disables `/docs`).

## Guardrails (read before extending `services/security_audit`)

This system performs **passive analysis only** — headers, certs, robots.txt,
sitemap, public config/source-map exposure, technology fingerprinting. It
must never send injection payloads, brute-force credentials, fuzz paths, or
attempt SSRF/auth-bypass. That boundary is enforced in code via
`PassiveHttpClient` (`backend/app/services/security_audit/passive_http_client.py`),
which only exposes `GET`/`HEAD` — there's no method to attach a request body
or send anything that acts on the target rather than reads from it. Any
future contribution to that module should go through this client, not a raw
`httpx`/`requests` call.

## Design system (frontend)

Deliberately not the generic AI-dashboard defaults (cream+terracotta, or
near-black+acid-green). Deep slate-navy surfaces (`#0B0E14` canvas /
`#12161F` cards), a warm brass/amber accent (`#C99A44`) standing for
"opportunity found," and a consistent priority color scale
(critical=red, high=orange, medium=blue, low=gray) used everywhere a lead
priority appears. Type: Space Grotesk for display, Inter for body copy,
JetBrains Mono for scores/metrics. The signature element is the circular
`ScoreGauge` — the same 0–100 opportunity-score ring appears on business
cards, the lead board, and the detail page so "score" always reads the
same way. Tokens live in `frontend/tailwind.config.js`.

## Next steps

Tell me which phase to build next — Phase 9 (hardening: rate limiting, full
test coverage, load testing, production Compose/Nginx TLS) is the natural
continuation now that the full product surface exists — and I'll implement
it to the same production bar.
