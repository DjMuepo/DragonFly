export type GeometryResponse = {
  ok: boolean;
  job_id: string;
  engine: string;
  status: string;
  label: string;
  detected_family?: string;
  model_name: string;
  model_url: string;
  download_url: string;
  stl_download_url?: string;
  created_at: number;
  notes?: string;
};

export type VisionResponse = {
  ok: boolean;
  label: string;
  family: string;
  confidence: number;
  suggestions: string[];
};

function cleanBase(url: string) {
  return url.replace(/\/$/, '');
}

export function getGeometryApiBase() {
  const envBase = process.env.EXPO_PUBLIC_GEOMETRY_API_BASE;
  if (envBase) return cleanBase(envBase);
  if (typeof window !== 'undefined') {
    const origin = window.location.origin;
    if (origin.includes('-8081.')) return cleanBase(origin.replace('-8081.', '-8010.'));
    if (origin.includes(':8081')) return cleanBase(origin.replace(':8081', ':8010'));
  }
  return 'http://localhost:8010';
}

function absoluteUrl(pathOrUrl: string) {
  if (!pathOrUrl) return pathOrUrl;
  if (/^https?:\/\//i.test(pathOrUrl)) return pathOrUrl;
  const path = pathOrUrl.startsWith('/') ? pathOrUrl : `/${pathOrUrl}`;
  return `${getGeometryApiBase()}${path}`;
}

function normalize(data: GeometryResponse): GeometryResponse {
  return {
    ...data,
    model_url: absoluteUrl(data.model_url),
    download_url: absoluteUrl(data.download_url),
    stl_download_url: data.stl_download_url ? absoluteUrl(data.stl_download_url) : undefined,
  };
}

export async function generateGeometryFromImage(params: { imageUri?: string; label?: string; confidence?: number }): Promise<GeometryResponse> {
  const label = params.label || 'Object';
  if (!params.imageUri) return generateGeometryFromPrompt({ label });
  const form = new FormData();
  form.append('label', label);
  form.append('confidence', String(params.confidence ?? 0.7));
  if (typeof window !== 'undefined') {
    const imageRes = await fetch(params.imageUri);
    const blob = await imageRes.blob();
    form.append('image', blob, 'scan.jpg');
  } else {
    form.append('image', { uri: params.imageUri, name: 'scan.jpg', type: 'image/jpeg' } as any);
  }
  const res = await fetch(`${getGeometryApiBase()}/v1/geometry/generate-from-image`, { method: 'POST', body: form });
  if (!res.ok) throw new Error(`Geometry backend failed (${res.status}): ${await res.text()}`);
  return normalize((await res.json()) as GeometryResponse);
}

export async function generateGeometryFromPrompt(params: { label?: string; prompt?: string }): Promise<GeometryResponse> {
  const res = await fetch(`${getGeometryApiBase()}/v1/geometry/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ label: params.label || 'Object', confidence: 0.7, mode: 'approximate', prompt: params.prompt }),
  });
  if (!res.ok) throw new Error(`Geometry backend failed (${res.status}): ${await res.text()}`);
  return normalize((await res.json()) as GeometryResponse);
}

export async function editGeometry(params: { label?: string; modelUrl?: string; prompt: string }): Promise<GeometryResponse> {
  const res = await fetch(`${getGeometryApiBase()}/v1/geometry/edit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ label: params.label || 'Object', model_url: params.modelUrl, prompt: params.prompt }),
  });
  if (!res.ok) throw new Error(`Edit backend failed (${res.status}): ${await res.text()}`);
  return normalize((await res.json()) as GeometryResponse);
}

export async function preparePrint(params: { modelUrl?: string; material?: string; infillPercent?: number }) {
  const res = await fetch(`${getGeometryApiBase()}/v1/geometry/prepare-print`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ model_url: params.modelUrl, material: params.material || 'PLA', infill_percent: params.infillPercent ?? 20 }),
  });
  if (!res.ok) throw new Error(`Print prep failed (${res.status}): ${await res.text()}`);
  return await res.json();
}
