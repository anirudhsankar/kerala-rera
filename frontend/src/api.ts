import { useEffect, useState } from "react";

const API_ORIGIN = import.meta.env.VITE_API_BASE ?? "";

export async function api<T>(
  path: string,
  params?: Record<string, unknown>,
): Promise<T> {
  const url = new URL(`${API_ORIGIN}/api${path}`, window.location.origin);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null && value !== "") {
        url.searchParams.set(key, String(value));
      }
    }
  }
  const res = await fetch(url.toString());
  if (!res.ok) {
    throw new Error(`${res.status} ${res.statusText}`);
  }
  return (await res.json()) as T;
}

export function useApi<T>(
  path: string,
  params?: Record<string, unknown>,
  enabled = true,
): { data: T | null; error: string | null; loading: boolean } {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const key = JSON.stringify(params ?? {});

  useEffect(() => {
    if (!enabled) {
      setData(null);
      setError(null);
      setLoading(false);
      return;
    }
    let active = true;
    setLoading(true);
    api<T>(path, params)
      .then((result) => {
        if (active) {
          setData(result);
          setError(null);
        }
      })
      .catch((err: unknown) => {
        if (active) setError(String(err));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, key, enabled]);

  return { data, error, loading };
}

// ---- shared types ---------------------------------------------------------
export interface Counted {
  count: number;
}
export interface StatusCount {
  status: string | null;
  count: number;
}
export interface TypeCount {
  type: string | null;
  count: number;
}

export interface Overview {
  total_projects: number;
  total_units: number;
  sold_units: number;
  sell_through: number | null;
  units_under_development: number;
  projects_with_units: number;
  projects_without_units: number;
  declared_completion_date_passed: number;
  by_status: StatusCount[];
  by_type: TypeCount[];
  derived_metrics: string[];
}

export interface PeriodCount {
  period: string;
  count: number;
}
export interface TimelineData {
  granularity: string;
  registrations: PeriodCount[];
  declared_completions: PeriodCount[];
  note: string;
}

export interface DistrictStat {
  district: string | null;
  projects: number;
  total_units: number;
  sold_units: number;
  sell_through: number | null;
  completed: number;
  inprogress: number;
}

export interface DistrictDetail {
  district: string;
  summary: {
    projects: number;
    total_units: number;
    sold_units: number;
    sell_through: number | null;
    completed: number;
    inprogress: number;
  };
  by_type: TypeCount[];
  taluks: { taluk: string; count: number }[];
  top_builders: { promoter_id: number | null; name: string; projects: number }[];
}

export interface BuilderStat {
  promoter_id: number;
  name: string;
  needs_review: boolean;
  projects: number;
  total_units: number;
  sold_units: number;
  sell_through: number | null;
  districts: number;
}

export interface BuilderDetail {
  promoter_id: number;
  name: string;
  needs_review: boolean;
  match_method: string | null;
  summary: {
    projects: number;
    total_units: number;
    sold_units: number;
    sell_through: number | null;
    completed: number;
    inprogress: number;
    past_due_count: number;
    avg_days_past_completion: number | null;
  };
  by_district: { district: string; count: number }[];
  by_type: TypeCount[];
  projects: ProjectBrief[];
}

export interface ProjectBrief {
  rera_registration_number: string;
  project_name: string | null;
  promoter_name_raw: string | null;
  promoter_id: number | null;
  project_type: string | null;
  project_status: string | null;
  project_start_date: string | null;
  declared_completion_date: string | null;
  certificate_number: string | null;
  certificate_date: string | null;
  total_units: number | null;
  sold_units: number | null;
  district: string | null;
  taluk: string | null;
  village: string | null;
}

export interface ProjectDetail extends ProjectBrief {
  promoter_canonical_name?: string | null;
  not_seen_in_latest_run: boolean;
  first_seen_at: string | null;
  last_seen_at: string | null;
  last_checked_at: string | null;
}

export interface ProjectPage {
  total: number;
  limit: number;
  offset: number;
  items: ProjectBrief[];
}

export interface Snapshot {
  id: number;
  snapshot_date: string;
  collected_at: string;
  source_hash: string;
  project_status: string | null;
  declared_completion_date: string | null;
  total_units: number | null;
  sold_units: number | null;
}

export interface ChangeEvent {
  id: number;
  detected_at: string;
  field_name: string;
  old_value: string | null;
  new_value: string | null;
}

export interface DQSummary {
  total: number;
  by_severity: Record<string, number>;
  by_type: { issue_type: string; count: number }[];
}

export interface RunInfo {
  id: number;
  started_at: string;
  completed_at: string | null;
  status: string;
  source: string;
  collection_method: string;
  parser_version: string;
  records_found: number;
  inserted: number;
  updated: number;
  unchanged: number;
  failed: number;
}

export interface BaselineInfo {
  baseline_at: string;
  source: string;
  record_count: number;
  parser_version: string;
  source_checksum: string;
}

export interface FilterOptions {
  districts: string[];
  types: string[];
  statuses: string[];
  taluks?: string[];
  villages?: string[];
}

// ---- locations ------------------------------------------------------------
export interface TalukStat {
  district?: string;
  taluk: string;
  projects: number;
  total_units?: number;
  sold_units?: number;
  sell_through?: number | null;
}

export interface VillageStat {
  village: string;
  projects: number;
}

export interface LocalitySummary {
  projects: number;
  total_units: number;
  sold_units: number;
  sell_through: number | null;
  completed: number;
  inprogress: number;
}

export interface BuilderRef {
  promoter_id: number | null;
  name: string;
  projects: number;
}

export interface TalukDetail {
  district: string;
  taluk: string;
  summary: LocalitySummary;
  villages: VillageStat[];
  by_type: TypeCount[];
  top_builders: BuilderRef[];
  recent: ProjectBrief[];
}

export interface VillageDetail {
  district: string;
  village: string;
  taluks: string[];
  summary: LocalitySummary;
  by_type: TypeCount[];
  top_builders: BuilderRef[];
  recent: ProjectBrief[];
}

export interface NewProjects {
  months: number;
  since: string;
  total: number;
  items: ProjectBrief[];
}

// ---- history --------------------------------------------------------------
export interface ChangeRow {
  id: number;
  project_id: number;
  rera_registration_number: string;
  project_name: string | null;
  district: string | null;
  taluk: string | null;
  detected_at: string;
  field_name: string;
  old_value: string | null;
  new_value: string | null;
  source_last_modified_date: string | null;
}

export interface ChangeEventPage {
  total: number;
  limit: number;
  offset: number;
  items: ChangeRow[];
}

export interface HistorySummary {
  total_changes: number;
  projects_changed: number;
  first_change_at: string | null;
  last_change_at: string | null;
  changes_by_month: PeriodCount[];
  changes_by_field: { field_name: string; count: number }[];
  status_transitions: { from: string | null; to: string | null; count: number }[];
  snapshots_by_month: PeriodCount[];
  baseline_at: string | null;
  note: string;
}

// ---- overdue / market -----------------------------------------------------
export interface OverdueItem extends ProjectBrief {
  days_past_completion: number;
}

export interface OverduePage {
  total: number;
  limit: number;
  offset: number;
  min_days: number;
  as_of: string;
  items: OverdueItem[];
}

export interface OverdueDistrict {
  district: string;
  count: number;
  avg_days: number;
}
export interface OverduePromoter {
  promoter_id: number;
  name: string;
  count: number;
  avg_days: number;
}
export interface OverdueSummary {
  total: number;
  avg_days_past_completion: number | null;
  min_days: number;
  as_of: string;
  by_district: OverdueDistrict[];
  by_promoter: OverduePromoter[];
}

export interface UnsoldGroup {
  district?: string;
  type?: string;
  projects: number;
  total_units: number;
  sold_units: number;
  unsold_units: number;
  undisclosed: number;
}
export interface UnsoldInventory {
  total_units: number;
  sold_units: number;
  unsold_units: number;
  undisclosed_projects: number;
  by_district: UnsoldGroup[];
  by_type: UnsoldGroup[];
}

export interface PipelineYear {
  year: number;
  projects: number;
  units: number;
}

export interface RegistrationTrend {
  granularity: string;
  by_type: boolean;
  periods: string[];
  series: { name: string; data: number[] }[];
}

export interface ProjectMix {
  districts: string[];
  types: string[];
  data: { district: string; type: string; count: number }[];
}

export interface Concentration {
  total_units: number;
  top10_units: number;
  top10_share: number | null;
  promoters: number;
  single_project_promoters: number;
}
