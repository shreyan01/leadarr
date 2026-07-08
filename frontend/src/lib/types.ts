export type Role = "owner" | "admin" | "analyst" | "viewer";

export interface User {
  id: string;
  organization_id: string;
  email: string;
  full_name: string;
  role: Role;
  is_active: boolean;
}

export type BusinessStatus = "discovered" | "validated" | "audited" | "archived";

export interface Business {
  id: string;
  name: string;
  category: string;
  phone: string | null;
  email: string | null;
  address: string | null;
  city: string;
  country: string;
  latitude: number | null;
  longitude: number | null;
  website_url: string | null;
  facebook_url: string | null;
  instagram_url: string | null;
  google_rating: number | null;
  review_count: number | null;
  status: BusinessStatus;
  discovered_at: string | null;
  is_social_only_lead: boolean;
}

export interface BusinessListResponse {
  items: Business[];
  total: number;
  page: number;
  page_size: number;
}

export type AuditStatus = "pending" | "running" | "completed" | "failed";
export type JobEventStatus = "started" | "succeeded" | "failed" | "retried";

export interface JobEvent {
  stage: string;
  status: JobEventStatus;
  duration_ms: number | null;
  retries: number;
  model_used: string | null;
  message: string | null;
  created_at: string;
}

export interface AuditJob {
  id: string;
  business_id: string;
  status: AuditStatus;
  current_stage: string | null;
  failed_stage: string | null;
  error_message: string | null;
  started_at: string | null;
  finished_at: string | null;
  events: JobEvent[];
}

export interface LighthouseReport {
  performance_score: number | null;
  accessibility_score: number | null;
  seo_score: number | null;
  best_practices_score: number | null;
  lcp_ms: number | null;
  cls: number | null;
  speed_index_ms: number | null;
  tti_ms: number | null;
  fcp_ms: number | null;
}

export interface AccessibilityFinding {
  missing_alt_count: number | null;
  heading_hierarchy_issues: { issues: Array<{ type: string; detail: string }> } | null;
  aria_issues: { issues: unknown[] } | null;
  contrast_issues: { issues: unknown[] } | null;
  unlabeled_buttons: { items: unknown[] } | null;
  keyboard_nav_issues: { items: unknown[] } | null;
  unlabeled_form_fields: { items: unknown[] } | null;
  accessibility_score: number | null;
}

export interface SecurityFinding {
  https: boolean | null;
  tls_version: string | null;
  cert_issuer: string | null;
  cert_expires_at: string | null;
  hsts: boolean | null;
  csp: string | null;
  permissions_policy: string | null;
  referrer_policy: string | null;
  x_frame_options: string | null;
  x_content_type_options: string | null;
  cookie_flags: { cookies: Array<{ name: string; secure: boolean; http_only: boolean }> } | null;
  mixed_content: boolean | null;
  directory_listing_exposed: boolean | null;
  exposed_source_maps: { urls: string[] } | null;
  exposed_config_files: { paths: string[] } | null;
  exposed_secrets_regex_hits: { findings: Array<{ type: string; source: string }> } | null;
  server_header: string | null;
  compression: string | null;
  caching_headers: Record<string, string> | null;
  public_api_endpoints: { endpoints: string[] } | null;
  manifest_present: boolean | null;
  service_worker_present: boolean | null;
  hygiene_score: number | null;
}

export interface TechnicalFinding {
  page_load_time_ms: number | null;
  sitemap_present: boolean | null;
  robots_present: boolean | null;
  favicon_present: boolean | null;
  schema_markup_present: boolean | null;
  schema_markup_valid: boolean | null;
  open_graph_present: boolean | null;
  twitter_card_present: boolean | null;
  google_business_link: string | null;
  broken_links: { items: Array<{ url: string; status: number | null }> } | null;
  broken_links_count: number | null;
  oversized_images: { items: Array<{ url: string; size_bytes: number; reason: string }> } | null;
  oversized_images_count: number | null;
  technical_score: number | null;
}

export type ScreenshotDevice = "desktop" | "tablet" | "mobile";

export interface Screenshot {
  device: ScreenshotDevice;
  storage_path: string;
  width: number;
  height: number;
}

export interface VisionAnalysis {
  screenshot_id: string;
  provider: string;
  model: string;
  trust_score: number | null;
  professionalism_score: number | null;
  modernity_score: number | null;
  whitespace_score: number | null;
  typography_score: number | null;
  layout_score: number | null;
  visual_hierarchy_score: number | null;
  cta_score: number | null;
  conversion_score: number | null;
  brand_consistency_score: number | null;
  nav_clarity_score: number | null;
  mobile_friendliness_score: number | null;
  overall_score: number | null;
}

export interface AIReportImprovement {
  title: string;
  detail: string;
  category?: string;
}

export interface AIReport {
  executive_summary: string | null;
  technical_summary: string | null;
  business_summary: string | null;
  seo_summary: string | null;
  accessibility_summary: string | null;
  security_summary: string | null;
  design_summary: string | null;
  top_improvements: { items: AIReportImprovement[] } | null;
  estimated_effort: Record<string, string> | null;
  priority_fixes: { items: string[] } | null;
  estimated_business_impact: string | null;
  markdown_storage_path: string | null;
  html_storage_path: string | null;
}

export type LeadPriority = "low" | "medium" | "high" | "critical";

export interface LeadScore {
  business_id: string;
  audit_job_id: string;
  performance_component: number | null;
  security_component: number | null;
  accessibility_component: number | null;
  seo_component: number | null;
  design_component: number | null;
  business_rating_component: number | null;
  review_count_component: number | null;
  website_age_component: number | null;
  technology_component: number | null;
  overall_score: number;
  priority: LeadPriority;
  scored_at: string;
}

export interface LeadListItem {
  business_id: string;
  overall_score: number;
  priority: LeadPriority;
  scored_at: string;
}

export interface LeadListResponse {
  items: LeadListItem[];
  total: number;
  page: number;
  page_size: number;
}

export type EmailStatus = "drafted" | "approved" | "sent" | "failed";

export interface OutreachEmail {
  id: string;
  business_id: string;
  template_key: string;
  subject: string;
  body_text: string;
  body_html: string | null;
  status: EmailStatus;
  created_at: string;
}

export type CampaignStage =
  | "discovered"
  | "audited"
  | "email_drafted"
  | "sent"
  | "opened"
  | "clicked"
  | "responded"
  | "meeting_scheduled"
  | "closed_won"
  | "closed_lost"
  | "archived";

export interface CampaignEvent {
  event_type: string;
  note: string | null;
  occurred_at: string;
}

export interface Campaign {
  id: string;
  business_id: string;
  name: string;
  stage: CampaignStage;
  next_follow_up_at: string | null;
  events: CampaignEvent[];
}