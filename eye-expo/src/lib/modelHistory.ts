import type { ModelRevision } from './useSnapStore';

export type ModelHistoryState = { history: ModelRevision[]; index: number };

export function appendRevision(history: ModelRevision[], index: number, revision: ModelRevision): ModelHistoryState {
  const next = [...history.slice(0, index + 1), revision];
  return { history: next, index: next.length - 1 };
}

export function undoRevision(history: ModelRevision[], index: number): ModelHistoryState {
  return { history, index: Math.max(0, index - 1) };
}

export function redoRevision(history: ModelRevision[], index: number): ModelHistoryState {
  return { history, index: Math.min(history.length - 1, index + 1) };
}

export function resetRevisions(history: ModelRevision[]): ModelHistoryState {
  return { history, index: history.length ? 0 : -1 };
}

export function currentRevision(state: ModelHistoryState): ModelRevision | undefined {
  return state.history[state.index];
}
