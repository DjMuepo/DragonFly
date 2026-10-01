import { appendRevision, currentRevision, redoRevision, resetRevisions, undoRevision } from '../src/lib/modelHistory.ts';
import type { ModelRevision } from '../src/lib/useSnapStore.ts';

function assert(condition: unknown, message: string): asserts condition {
	if (!condition) throw new Error(message);
}

const original: ModelRevision = { url: 'original.glb', name: 'original.glb', stlUrl: 'original.stl', providerKind: 'ai' };
const first: ModelRevision = { url: 'first.glb', name: 'first.glb', stlUrl: 'first.stl', providerKind: 'deterministic_edit', changeKind: 'geometry' };
const second: ModelRevision = { url: 'second.glb', name: 'second.glb', providerKind: 'visual_only', changeKind: 'visual_only' };

let state = appendRevision([], -1, original);
state = appendRevision(state.history, state.index, first);
state = appendRevision(state.history, state.index, second);
assert(currentRevision(state)?.url === 'second.glb', 'latest revision should be current');
state = undoRevision(state.history, state.index);
assert(currentRevision(state)?.url === 'first.glb', 'undo should select previous revision');
state = undoRevision(state.history, state.index);
assert(currentRevision(state)?.url === 'original.glb', 'second undo should reach original');
state = redoRevision(state.history, state.index);
assert(currentRevision(state)?.url === 'first.glb', 'redo should restore edit');
state = appendRevision(state.history, state.index, second);
assert(state.history.map((revision) => revision.url).join(',') === 'original.glb,first.glb,second.glb', 'new edit should replace redo branch');
state = resetRevisions(state.history);
assert(state.index === 0, 'reset should select original index');
assert(currentRevision(state)?.url === 'original.glb', 'reset should restore original model');
console.log('model history PASS');
