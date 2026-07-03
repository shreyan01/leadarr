# LeadForge — Architecture Document

## 1. Purpose & Guardrails

LeadForge discovers local businesses, performs **passive-only** analysis of their
public websites (performance, security *hygiene*, accessibility, SEO, visual
design), scores them as sales leads, generates AI audit reports, drafts
outreach emails, and tracks the resulting campaign in a lightweight CRM.

Hard constraint, enforced at the architecture level, not just by convention:

- No module may issue a request that could be construed as an attack:
  no injection payloads, no auth-bypass attempts, no brute force, no fuzzing,
  no SSRF probes against internal ranges.
- The `security` service is a **header/config/cert/metadata reader**, never a
  scanner. Its HTTP client is wrapped so that only `GET`/`HEAD` on the
  target's own declared origin (+ same-site static assets) are permitted, and
  request bodies/query mutation are disallowed by the client itself — this is
  a code-level control, not just a policy note, so a future contributor
  cannot casually turn it into a scanner.

## 2. Clean Architecture Layers

```
API (FastAPI routers)         <- HTTP/DTO concerns only
  -> Services                  <- business logic, orchestration
     -> Repositories            <- persistence, one per aggregate
        -> Models (SQLAlchemy)  <- ORM only, no logic
     -> AI Providers (interfaces) <- ChatProvider / VisionProvider / EmbeddingProvider
     -> Adapters                 <- external systems (Places APIs, SMTP, Lighthouse CLI, Playwright)
  -> Workers (Celery tasks)     <- thin wrappers that call Services
Core                            <- config, security, logging, DI container
```

Rules:
- Routers never touch the DB session directly beyond passing it through DI; no query building in routers.
- Services depend on repository **interfaces** (ABCs / Protocols), not concrete classes — enables test doubles.
- Providers (AI, discovery, email) are pluggable via a `ProviderRegistry` resolved from `.env` — adding a provider means writing one adapter class + one registry entry, zero call-site changes.

## 3. Directory Structure

```
leadforge/
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env.example
├── README.md
├── docs/
│   ├── ARCHITECTURE.md
│   ├── DATABASE_SCHEMA.md
│   ├── API_SPEC.md
│   └── ROADMAP.md
├── backend/
│   ├── pyproject.toml / requirements.txt
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/
│   │   │   ├── config.py            # Pydantic Settings
│   │   │   ├── security.py          # JWT, password hashing, RBAC deps
│   │   │   ├── logging.py           # structured logging
│   │   │   ├── di.py                # dependency-injection wiring
│   │   │   └── exceptions.py
│   │   ├── db/
│   │   │   ├── base.py              # declarative base, session factory
│   │   │   └── session.py
│   │   ├── models/                  # SQLAlchemy ORM models (1 file per aggregate)
│   │   ├── schemas/                 # Pydantic request/response DTOs
│   │   ├── repositories/            # interfaces + SQLAlchemy implementations
│   │   ├── services/
│   │   │   ├── discovery/
│   │   │   ├── validation/
│   │   │   ├── crawl/
│   │   │   ├── lighthouse/
│   │   │   ├── security_audit/      # passive-only, guarded HTTP client
│   │   │   ├── accessibility/
│   │   │   ├── vision/
│   │   │   ├── reporting/
│   │   │   ├── scoring/
│   │   │   ├── outreach/
│   │   │   └── crm/
│   │   ├── ai/
│   │   │   ├── interfaces.py        # ChatProvider, VisionProvider, EmbeddingProvider (Protocols)
│   │   │   ├── registry.py
│   │   │   └── providers/
│   │   │       ├── openai_provider.py
│   │   │       ├── anthropic_provider.py
│   │   │       ├── gemini_provider.py
│   │   │       ├── ollama_provider.py
│   │   │       ├── openrouter_provider.py
│   │   │       └── qwen_vl_provider.py
│   │   ├── adapters/
│   │   │   ├── discovery/            # Places-provider adapters
│   │   │   ├── email/                # SMTP / Resend / SendGrid / SES
│   │   │   └── lighthouse_cli.py
│   │   ├── workers/
│   │   │   ├── celery_app.py
│   │   │   └── tasks/                # one task module per pipeline stage
│   │   ├── api/v1/
│   │   │   ├── router.py
│   │   │   └── endpoints/            # businesses, audits, leads, emails, campaigns, auth, health
│   │   └── utils/
│   └── tests/
│       ├── unit/
│       └── integration/
├── frontend/                         # Next.js 14 app router, TS, Tailwind, shadcn/ui
│   └── src/
│       ├── app/
│       ├── components/
│       ├── lib/
│       └── hooks/
└── infra/
    ├── nginx/
    └── docker/
```

## 4. Pipeline (Celery Chain per Audit)

`discover → validate → crawl → lighthouse → accessibility → security_audit → vision → ai_report → lead_score → email_draft → finished`

Each stage is its own Celery task, chained with `celery.chain`, each task:
- reads/writes only its own DB tables via its Service + Repository,
- is idempotent (safe to retry — checks for existing output before recompute),
- writes a `JobEvent` row (duration, status, retries, tokens/cost if AI) for observability,
- on unrecoverable failure marks the parent `AuditJob` `failed` with the stage name, and the chain stops without silently continuing (a failed crawl should not produce a fabricated report).

## 5. AI Abstraction

```python
class ChatProvider(Protocol):
    async def complete(self, messages: list[Message], *, model: str, temperature: float = 0.3) -> ChatResult: ...

class VisionProvider(Protocol):
    async def analyze_image(self, image: bytes, prompt: str, *, model: str) -> VisionResult: ...

class EmbeddingProvider(Protocol):
    async def embed(self, texts: list[str], *, model: str) -> list[list[float]]: ...
```

`ProviderRegistry` resolves the active provider per capability from settings
(`AI_CHAT_PROVIDER=anthropic`, `AI_VISION_PROVIDER=qwen_vl`, etc.), so services
depend only on the Protocol, never a concrete SDK.

## 6. Security Model

- JWT access + refresh tokens, argon2 password hashing.
- RBAC: `owner`, `admin`, `analyst`, `viewer` roles, enforced via FastAPI dependency (`require_role(...)`).
- Rate limiting via Redis token bucket on auth + audit-trigger endpoints.
- All outbound audit HTTP requests go through a single `PassiveHttpClient` wrapper: GET/HEAD only, no credentials injected, respects `robots.txt` for crawl paths, timeouts + size caps to avoid abuse of target sites.
- Secrets never logged; `.env` only, Pydantic `SecretStr` for credentials.

## 7. Multi-tenancy readiness

Even in v1 (single-tenant), every table carries `organization_id` (nullable now,
enforced later) so multi-tenancy and white-label mode are additive, not a rewrite.

## 8. Observability

Structured JSON logs (stage, duration_ms, retries, tokens, cost, model) shipped
to stdout (container log driver picks it up). `/health`, `/health/workers`,
`/health/queue` endpoints for infra monitoring.
