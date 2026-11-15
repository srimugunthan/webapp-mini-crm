export interface Group { id: number; name: string; created_at: number; member_count: number; stage_count: number; pipeline_epoch?: number }
export interface GroupRef { id: number; name: string }
export interface Contact {
  id: number; first_name: string; last_name: string; company: string; position: string; linkedin_url: string;
  email: string; connected_on: string | null; last_visited_at: number | null; last_messaged_at: number | null;
  groups: GroupRef[];
}
export interface Paged<T> { items: T[]; total: number; offset?: number; limit?: number }
export interface Stage { id: number; group_id: number; name: string; position: number; is_final: boolean }
export interface Member {
  contact_id: number; first_name: string; last_name: string; company: string; position: string; linkedin_url: string;
  last_visited_at: number | null; last_messaged_at: number | null; stage_id: number | null; stage_name: string | null;
  stage_is_final: number | null; stage_changed_at: number | null; next_follow_up_at: number | null; days_in_stage: number | null;
}
export interface StageCounts { total: number; unstaged: number; stages: { stage_id: number; name: string; is_final: number; count: number }[] }
export interface Template { id: number; name: string; stages: { name: string; position: number; is_final: number }[] }
export interface ImportSummary { new: number; updated: number; skipped: { row: number; reason: string; name: string }[]; errors: string[] }
export interface BulkPreview {
  token: string; counts: { move: number; no_change: number; add: number; not_found: number; unknown_stage: number };
  problems: { row: number; url: string; stage: string; reason: string }[];
}
export interface ContactDetail extends Contact {
  memberships: { group_id: number; group_name: string; stage_name: string | null; stage_changed_at: number | null; next_follow_up_at: number | null }[];
  history: { id: number; group_name: string; from_stage_name: string | null; to_stage_name: string | null; changed_at: number; source: string; note: string | null }[];
  notes: { id: number; body: string; created_at: number }[];
}
export interface ApplyPlan {
  template_id: number; template_stages: string[]; no_stage_to_first: number; first_stage: string;
  mapped: { stage_id: number; stage_name: string; count: number; to: string }[];
  unmatched: { stage_id: number; stage_name: string; count: number; to: string | null }[];
}
