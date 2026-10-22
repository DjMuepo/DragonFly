import { currentRevision } from '../src/lib/modelHistory.ts';
import { historyFromProject, revisionFromServer } from '../src/lib/projectMapping.ts';
import type { ServerProject } from '../src/lib/projectMapping.ts';

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(message);
}

const project: ServerProject = {
  id: 'p1', name: 'Bottle', label: 'bottle', updated_at: 1, cursor_index: 1, revision_count: 3, has_source_image: true,
  revisions: [
    { id: 'r0', seq: 0, kind: 'generate', job_id: 'j0', provider_kind: 'ai', scale_status: 'unknown', model_name: 'a.glb', model_url: 'https://x/a.glb?sig=1', stl_url: 'https://x/a.stl?sig=1', available: true },
    { id: 'r1', seq: 1, kind: 'calibration', job_id: 'j1', provider_kind: 'calibration', change_kind: 'geometry', scale_status: 'calibrated', calibration: { axis: 'height', value_mm: 180, source_measurement: '180 mm tall' }, model_name: 'b.glb', model_url: 'https://x/b.glb?sig=1', available: true },
    { id: 'r3', seq: 3, kind: 'edit', job_id: 'j3', provider_kind: 'deterministic_edit', model_name: 'c.glb', available: false, unavailable_reason: 'file is missing from storage' },
  ],
};

const { history, index } = historyFromProject(project);
assert(history.length === 3 && index === 1, 'history keeps the server cursor');
assert(currentRevision({ history, index })?.calibration?.value_mm === 180, 'calibration survives reopen');
assert(currentRevision({ history, index })?.scaleStatus === 'calibrated', 'scale status survives reopen');
assert(history[0].scaleStatus === 'unknown' && history[0].stlUrl === 'https://x/a.stl?sig=1', 'original keeps unknown scale and STL link');
assert(history[2].unavailableReason === 'file is missing from storage' && history[2].url === '', 'missing artifacts are flagged, not hidden');
assert(history.map((revision) => revision.jobId).join(',') === 'j0,j1,j3', 'job ids are preserved');
assert(historyFromProject({ ...project, cursor_index: 99 }).index === 2, 'cursor is clamped');
assert(historyFromProject({ ...project, revisions: [] }).index === -1, 'empty project has no current revision');
assert(revisionFromServer(project.revisions![0]).revisionId === 'r0', 'revision ids are preserved');
console.log('project mapping PASS');
