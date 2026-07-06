export interface Membership {
  org_id: string;
  org_name: string;
  org_slug: string;
  role: string;
}

export interface Me {
  id: string;
  email: string;
  full_name: string;
  avatar_initials: string;
  memberships: Membership[];
}

export interface DashboardContext {
  scan_time: string | null;
  scan_date: string | null;
  reports_count: number;
  domains_count: number;
  next_scan_in: string | null;
}

export interface SLAStatus {
  breach: number;
  warning: number;
  healthy: number;
  total: number;
  layer: string;
  as_of: string | null;
}

export interface Incident {
  id: string;
  type: string;
  severity: "critical" | "warning";
  status: string;
  ai_name: string;
  ai_description: string;
  mart_name: string;
  layer_statuses: Record<string, string>;
  detected_at: string;
  est_recovery_time: string | null;
  sla_delay_minutes: number | null;
  dq_actual_pct: number | null;
  dq_target_pct: number | null;
  occurrence_count: number;
  occurrence_window_days: number | null;
  reports_affected_count: number;
  availability_label: string | null;
  delay_label: string | null;
  occurrence_label: string | null;
  dq_delta_label: string | null;
}

export interface CatalogReport {
  id: string;
  name: string;
  icon: string;
  domain_name: string;
  owner_team: string;
  refresh_schedule: string;
  last_run_at: string | null;
  current_status: "go" | "warn" | "stop";
}
