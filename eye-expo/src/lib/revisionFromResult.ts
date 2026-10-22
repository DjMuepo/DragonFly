import type { GeometryResponse } from './geometryApi';
import type { ModelRevision } from './useSnapStore';

export function revisionFromResult(result: GeometryResponse, fallbackSummary?: string): ModelRevision {
  return {
    url: result.model_url,
    name: result.model_name,
    stlUrl: result.stl_download_url,
    providerKind: result.provider_kind,
    changeKind: result.change_kind || (result.provider_kind === 'calibration' ? 'geometry' : undefined),
    summary: result.edit_summary || result.notes || fallbackSummary,
    scaleStatus: result.scale_status,
    calibration: result.calibration,
    validation: result.validation,
    jobId: result.job_id,
    revisionId: result.revision_id,
  };
}
