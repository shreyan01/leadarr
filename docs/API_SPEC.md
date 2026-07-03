# LeadForge — API Specification (v1)

Base path: `/api/v1`. Auth: `Authorization: Bearer <JWT>` except `/auth/*` and `/health`.

## Auth
| Method | Path | Description |
|---|---|---|
| POST | /auth/register | Create org + owner user |
| POST | /auth/login | Returns access + refresh token |
| POST | /auth/refresh | Rotate access token |
| GET  | /auth/me | Current user profile |

## Discovery
| Method | Path | Description |
|---|---|---|
| POST | /discovery/search | `{country, city, category}` → enqueues discovery job, returns `job_id` |
| GET  | /discovery/jobs/{job_id} | Status + discovered business count |

## Businesses
| Method | Path | Description |
|---|---|---|
| GET | /businesses | List, filter by city/category/status/score range, paginated |
| GET | /businesses/{id} | Detail incl. latest audit + lead score |
| POST | /businesses | Manually add a business |
| PATCH | /businesses/{id} | Update / archive |

## Audits
| Method | Path | Description |
|---|---|---|
| POST | /businesses/{id}/audits | Trigger full pipeline, returns `audit_job_id` |
| GET | /audits/{audit_job_id} | Full status incl. `current_stage`, per-stage `job_events` |
| GET | /audits/{audit_job_id}/lighthouse | Lighthouse report |
| GET | /audits/{audit_job_id}/security | Security hygiene findings |
| GET | /audits/{audit_job_id}/accessibility | Accessibility findings |
| GET | /audits/{audit_job_id}/vision | Vision analysis |
| GET | /audits/{audit_job_id}/report | AI report (markdown + html) |
| GET | /audits/{audit_job_id}/screenshots | Screenshot URLs (desktop/tablet/mobile) |

## Lead Scores
| Method | Path | Description |
|---|---|---|
| GET | /leads | List businesses ranked by `overall_score`, filterable by `priority` |
| GET | /leads/{business_id}/score | Latest score breakdown |

## Outreach
| Method | Path | Description |
|---|---|---|
| POST | /businesses/{id}/emails | Generate a draft (`template_key` optional) |
| GET | /businesses/{id}/emails | List drafts/sent |
| POST | /emails/{id}/send | Send via configured provider |
| PATCH | /emails/{id} | Edit before sending |

## Campaigns (CRM)
| Method | Path | Description |
|---|---|---|
| GET | /campaigns | Kanban-style list grouped by stage |
| PATCH | /campaigns/{id}/stage | Move stage, logs a `campaign_event` |
| POST | /campaigns/{id}/notes | Add note |
| PATCH | /campaigns/{id}/follow-up | Set follow-up date |

## Monitoring
| Method | Path | Description |
|---|---|---|
| GET | /health | Liveness |
| GET | /health/db | Database connectivity |
| GET | /health/workers | Celery worker ping (online count, active task count) |
| GET | /health/queue | Queue depth per queue |
| GET | /monitoring/stats | Failure rate, avg audit duration, avg lead score, AI token/cost usage (org-scoped) |

All list endpoints: `?page=&page_size=&sort=&order=`. All mutating endpoints
validate via Pydantic schemas; error responses follow
`{"error": {"code": str, "message": str, "details": [...]}}`.
