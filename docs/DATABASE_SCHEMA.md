# LeadForge — Database Schema (PostgreSQL)

All tables: `id UUID PK default gen_random_uuid()`, `created_at`, `updated_at`
timestamptz, `organization_id UUID NULL` (multi-tenancy hook).

## organizations / users
```
organizations(id, name, plan, is_active)
users(id, organization_id, email UNIQUE, hashed_password, full_name, role
      ENUM(owner,admin,analyst,viewer), is_active, last_login_at)
```

## businesses
```
businesses(
  id, organization_id,
  name, category, phone, address, city, country,
  latitude NUMERIC, longitude NUMERIC,
  website_url, google_place_id, google_rating NUMERIC(2,1), review_count INT,
  discovery_provider VARCHAR,     -- e.g. "google_places"
  discovered_at, status ENUM(discovered,validated,audited,archived)
)
INDEX (organization_id, city, category)
INDEX (website_url)
UNIQUE (organization_id, google_place_id)
```

## audit_jobs
```
audit_jobs(
  id, organization_id, business_id FK,
  status ENUM(pending,running,completed,failed),
  current_stage VARCHAR,           -- e.g. "lighthouse"
  failed_stage VARCHAR NULL,
  error_message TEXT NULL,
  started_at, finished_at
)
INDEX (business_id, status)
```

## job_events   (per-stage timing/cost log, feeds "LOGGING" requirement)
```
job_events(
  id, audit_job_id FK, stage VARCHAR, status ENUM(started,succeeded,failed,retried),
  duration_ms INT, retries INT DEFAULT 0,
  model_used VARCHAR NULL, tokens_input INT NULL, tokens_output INT NULL,
  cost_usd NUMERIC(10,4) NULL, memory_mb INT NULL, message TEXT NULL,
  created_at
)
INDEX (audit_job_id, stage)
```

## website_snapshots  (raw crawl output)
```
website_snapshots(
  id, business_id FK, audit_job_id FK,
  final_url, http_status INT, redirect_chain JSONB,
  html_storage_path, robots_txt TEXT, sitemap_urls JSONB,
  meta JSONB,            -- title, description, OpenGraph, Twitter Card, structured data
  favicon_url, nav_structure JSONB, forms JSONB, buttons JSONB,
  images JSONB, fonts JSONB, js_files JSONB, css_files JSONB,
  crawled_at
)
```

## screenshots
```
screenshots(
  id, website_snapshot_id FK,
  device ENUM(desktop,tablet,mobile), storage_path, width INT, height INT
)
```

## lighthouse_reports
```
lighthouse_reports(
  id, audit_job_id FK, raw_json_storage_path,
  performance_score INT, accessibility_score INT, seo_score INT, best_practices_score INT,
  lcp_ms NUMERIC, cls NUMERIC, speed_index_ms NUMERIC, tti_ms NUMERIC, fcp_ms NUMERIC
)
```

## security_findings   (passive hygiene only — see guardrails in ARCHITECTURE.md)
```
security_findings(
  id, audit_job_id FK,
  https BOOLEAN, tls_version VARCHAR, cert_issuer VARCHAR, cert_expires_at,
  hsts BOOLEAN, csp TEXT NULL, permissions_policy TEXT NULL, referrer_policy TEXT NULL,
  x_frame_options TEXT NULL, x_content_type_options TEXT NULL,
  cookie_flags JSONB, mixed_content BOOLEAN, directory_listing_exposed BOOLEAN,
  exposed_source_maps JSONB, exposed_config_files JSONB, exposed_secrets_regex_hits JSONB,
  tech_fingerprint JSONB, server_header TEXT, compression TEXT, caching_headers JSONB,
  public_api_endpoints JSONB, manifest_present BOOLEAN, service_worker_present BOOLEAN,
  hygiene_score INT
)
```

## accessibility_findings
```
accessibility_findings(
  id, audit_job_id FK,
  missing_alt_count INT, heading_hierarchy_issues JSONB, aria_issues JSONB,
  contrast_issues JSONB, unlabeled_buttons JSONB, keyboard_nav_issues JSONB,
  unlabeled_form_fields JSONB, accessibility_score INT
)
```

## vision_analyses
```
vision_analyses(
  id, audit_job_id FK, screenshot_id FK, provider VARCHAR, model VARCHAR,
  trust_score INT, professionalism_score INT, modernity_score INT,
  whitespace_score INT, typography_score INT, layout_score INT,
  visual_hierarchy_score INT, cta_score INT, conversion_score INT,
  brand_consistency_score INT, nav_clarity_score INT, mobile_friendliness_score INT,
  overall_score INT, raw_response JSONB
)
```

## ai_reports
```
ai_reports(
  id, audit_job_id FK, provider VARCHAR, model VARCHAR,
  executive_summary TEXT, technical_summary TEXT, business_summary TEXT,
  seo_summary TEXT, accessibility_summary TEXT, security_summary TEXT, design_summary TEXT,
  top_improvements JSONB, estimated_effort JSONB, priority_fixes JSONB,
  estimated_business_impact TEXT,
  markdown_storage_path, html_storage_path
)
```

## lead_scores
```
lead_scores(
  id, business_id FK, audit_job_id FK,
  performance_component NUMERIC, security_component NUMERIC,
  accessibility_component NUMERIC, seo_component NUMERIC, design_component NUMERIC,
  business_rating_component NUMERIC, review_count_component NUMERIC,
  website_age_component NUMERIC, technology_component NUMERIC,
  overall_score NUMERIC(5,2),   -- 0-100
  priority ENUM(low,medium,high,critical),
  scored_at
)
INDEX (business_id, scored_at)
```

## outreach_emails
```
outreach_emails(
  id, business_id FK, audit_job_id FK, template_key VARCHAR,
  subject TEXT, body_text TEXT, body_html TEXT,
  provider VARCHAR, model VARCHAR, status ENUM(drafted,approved,sent,failed)
)
```

## campaigns / campaign_events   (CRM pipeline)
```
campaigns(id, organization_id, business_id FK, name,
  stage ENUM(discovered,audited,email_drafted,sent,opened,clicked,responded,
             meeting_scheduled,closed_won,closed_lost,archived),
  owner_user_id FK NULL, next_follow_up_at NULL)

campaign_events(id, campaign_id FK, event_type VARCHAR, note TEXT, occurred_at, created_by FK)
```

## settings
```
settings(id, organization_id, key, value JSONB)
UNIQUE (organization_id, key)
```

All FK columns indexed; `audit_job_id` FKs use `ON DELETE CASCADE` from the
owning `audit_jobs` row so a re-run can safely purge and regenerate stage output.
