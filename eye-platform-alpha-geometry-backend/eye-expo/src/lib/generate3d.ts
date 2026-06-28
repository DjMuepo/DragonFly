export type Generate3DResult = {
  ok: boolean;
  engine: string;
  status: string;
  label: string;
  model_name: string;
  model_url: string;
  download_url: string;
  created_at: number;
  notes: string;
};

function apiBase(): string {
  return (process.env.EXPO_PUBLIC_API_BASE || 'http://localhost:8000').replace(/\/$/, '');
}

function absoluteUrl(pathOrUrl: string): string {
  if (!pathOrUrl) return pathOrUrl;
  if (pathOrUrl.startsWith('http://') || pathOrUrl.startsWith('https://') || pathOrUrl.startsWith('mvp://')) return pathOrUrl;
  return `${apiBase()}${pathOrUrl.startsWith('/') ? '' : '/'}${pathOrUrl}`;
}

function localFallback(label?: string): Generate3DResult {
  const safe = (label || 'object').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'object';
  return {
    ok: true,
    engine: 'local-fallback-procedural-preview',
    status: 'done',
    label: label || 'Object',
    model_name: `${safe}-draft.glb`,
    model_url: `mvp://${safe}-draft.glb`,
    download_url: `mvp://${safe}-draft.glb`,
    created_at: Date.now() / 1000,
    notes: 'Geometry backend unavailable. Local MVP preview fallback used.',
  };
}

export async function generate3DFromLabel(label?: string, confidence = 0.7): Promise<Generate3DResult> {
  try {
    const res = await fetch(`${apiBase()}/v1/geometry/generate`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ label: label || 'Object', confidence, mode: 'approximate' }),
    });

    if (!res.ok) throw new Error(`Geometry backend failed: ${res.status}`);
    const data = (await res.json()) as Generate3DResult;

    return {
      ...data,
      model_url: absoluteUrl(data.model_url),
      download_url: absoluteUrl(data.download_url),
    };
  } catch (error) {
    console.warn('Geometry generation fallback:', error);
    return localFallback(label);
  }
}
