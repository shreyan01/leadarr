# LeadForge — Implementation Roadmap

Given the scope of this system, it's built in phases, each independently
runnable and demoable. **This response delivers Phase 1.** Say which phase to
tackle next and it'll be built with the same production-quality bar.

- **Phase 1 — Foundation** *(this delivery)*: repo scaffold, Docker Compose
  (Postgres, Redis, backend, worker, frontend, nginx), Pydantic Settings,
  SQLAlchemy models for the full schema, Alembic migration, JWT auth +
  RBAC, health endpoints, base FastAPI app wiring, AI provider interfaces
  + Anthropic/OpenAI adapters, repository pattern skeleton.
- **Phase 2 — Discovery & Validation**: Places-provider adapter(s), business
  repository/service, URL validation, tech/CMS fingerprinting, discovery
  Celery task + API.
- **Phase 3 — Crawl & Lighthouse**: Playwright crawler, asset/metadata
  collection, screenshot capture (desktop/tablet/mobile), Lighthouse CLI
  adapter + parsing.
- **Phase 4 — Passive Security & Accessibility audits**: guarded
  `PassiveHttpClient`, header/cert/config checks, secret-pattern scanning of
  public files only, automated accessibility checks (axe-core via
  Playwright).
- **Phase 5 — Vision AI**: Qwen2.5-VL adapter (local), screenshot-based
  structured scoring, provider-agnostic vision pipeline.
- **Phase 6 — AI Reports & Lead Scoring**: report generation prompts +
  markdown/HTML rendering, weighted scoring engine, priority banding.
- **Phase 7 — Outreach & CRM**: email generation templates, SMTP/Resend/
  SendGrid/SES adapters, campaign kanban, follow-up reminders.
- **Phase 8 — Dashboard (Next.js)** *(shipped)*: JWT auth (login/register),
  business list/detail with the full audit report viewer (Lighthouse,
  security, accessibility, screenshots, AI report, outreach emails), lead
  board with priority filtering, campaign kanban, dark mode, a distinctive
  design system (see below).
- **Phase 9 — Hardening** *(shipped)*: Redis-backed rate limiting on
  auth/discovery/audit-trigger endpoints, security-headers + request-ID
  middleware on our own API, `/health/workers` (Celery inspect) and
  `/monitoring/stats` (failure rate, avg audit duration, avg lead score, AI
  token/cost usage), integration tests against the real FastAPI app via
  fake repositories, a Locust load-test script, and a production Docker
  Compose overlay (gunicorn, built frontend, Nginx TLS termination,
  non-root containers).
- **Phase 10 — Future features**: mockup/landing-page generation,
  multi-tenancy enforcement, white-label mode, public API, browser
  extension.
