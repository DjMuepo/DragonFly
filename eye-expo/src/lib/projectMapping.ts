import type { ModelRevision } from './useSnapStore';

export type ServerRevision = {
  id: string;
  seq: number;
  kind: string;
  job_id?: string | null;
  provider_kind?: string | null;
  change_kind?: string | null;
  summary?: string | null;
  scale_status?: string | null;
  calibration?: ModelRevision['calibration'] | null;
  validation?: ModelRevision['validation'] | null;
  model_name?: string | null;
  model_url?: string;
  stl_url?: string;
  available: boolean;
  unavailable_reason?: string | null;
  warnings?: string[];
};

export type ServerProject = {
  id: string;
  name: string;
  label: string;
  updated_at: number;
  cursor_index: number;
  revision_count: number;
  has_source_image: boolean;
  revisions?: ServerRevision[];
};

export function revisionFromServer(revision: ServerRevision): ModelRevision {
  return {
    url: revision.model_url || '',
    name: revision.model_name || '',
    stlUrl: revision.stl_url,
    providerKind: revision.provider_kind || 'ai',
    changeKind: (revision.change_kind as ModelRevision['changeKind']) || undefined,
    summary: revision.summary || undefined,
    scaleStatus: revision.scale_status === 'calibrated' ? 'calibrated' : 'unknown',
    calibration: revision.calibration || undefined,
    validation: revision.validation || undefined,
    jobId: revision.job_id || undefined,
    revisionId: revision.id,
    unavailableReason: revision.available ? undefined : revision.unavailable_reason || 'Model file is unavailable.',
  };
}

export function historyFromProject(project: ServerProject): { history: ModelRevision[]; index: number } {
  const history = (project.revisions || []).map(revisionFromServer);
  const index = history.length ? Math.min(Math.max(project.cursor_index, 0), history.length - 1) : -1;
  return { history, index };
}
