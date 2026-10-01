export type GeometryResponse = {
  ok: boolean;
  job_id: string;
  engine: string;
  provider_kind: 'ai' | 'procedural_fallback' | 'deterministic_edit' | 'visual_only' | 'calibration';
  status: string;
  label: string;
  detected_family?: string;
  model_name: string;
  model_url: string;
  download_url: string;
  stl_download_url?: string;
  created_at: number;
  notes?: string;
  change_kind?: 'geometry' | 'visual_only';
  edit_summary?: string;
  operations?: string[];
  validation?: {
    watertight: boolean;
    mesh_integrity: { winding_consistent: boolean; body_count: number; vertices: number; faces: number };
    scale_status: 'unknown' | 'calibrated';
    dimensions_mm: { width: number; depth: number; height: number } | null;
    dimensions_model_units: { width: number; depth: number; height: number } | null;
    minimum_feature_thickness_mm: number | null;
    minimum_feature_thickness_status: 'not_measured' | 'measured';
    warnings: string[];
  };
  scale_status: 'unknown' | 'calibrated';
  calibration?: { axis: 'width' | 'depth' | 'height'; value_mm: number; source_measurement: string };
};

export type GeometryJobResponse = {
  job_id: string;
  status: 'queued' | 'processing' | 'done' | 'error';
  progress: number;
  provider: string;
  provider_kind: 'ai' | 'procedural_fallback' | 'deterministic_edit' | 'visual_only' | 'calibration';
  error?: string;
  result?: GeometryResponse;
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
  const envBase = process.env.EXPO_PUBLIC_GEOMETRY_API_BASE || process.env.EXPO_PUBLIC_API_BASE;
  if (envBase) return cleanBase(envBase);
  throw new Error('EXPO_PUBLIC_GEOMETRY_API_BASE must be set to your public backend URL.');
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

async function timedFetch(url: string, options?: RequestInit): Promise<Response> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 30000);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } catch (error) {
    if (controller.signal.aborted) throw new Error('The connection timed out. Check your network and try again.');
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

async function waitForGeometryJob(job: GeometryJobResponse, onProgress?: (job: GeometryJobResponse) => void): Promise<GeometryResponse> {
  let current = job;
  for (let attempt = 0; attempt < 720; attempt += 1) {
    onProgress?.(current);
    if (current.status === 'done') {
      if (!current.result?.model_url || !/^https?:\/\//i.test(absoluteUrl(current.result.model_url))) {
        throw new Error('Geometry job completed without a valid model URL. Try again.');
      }
      return normalize(current.result);
    }
    if (current.status === 'error') throw new Error(current.error || `${current.provider} reconstruction failed`);
    await new Promise((resolve) => setTimeout(resolve, 1000));
    const response = await timedFetch(`${getGeometryApiBase()}/v1/geometry/jobs/${encodeURIComponent(current.job_id)}`);
    if (!response.ok) throw new Error(`Geometry job lookup failed (${response.status})`);
    current = (await response.json()) as GeometryJobResponse;
  }
  throw new Error('Geometry generation timed out before the backend returned a model.');
}

export async function generateGeometryFromImage(params: { imageUri?: string; label?: string; confidence?: number; onProgress?: (job: GeometryJobResponse) => void }): Promise<GeometryResponse> {
  const label = params.label || 'Object';
  if (!params.imageUri) throw new Error('Choose or capture a photo before generating a model.');
  const form = new FormData();
  form.append('label', label);
  form.append('confidence', String(params.confidence ?? 0.7));
  if (typeof window !== 'undefined') {
    const imageRes = await fetch(params.imageUri);
    if (!imageRes.ok) throw new Error('Could not read the selected photo. Select it again and retry.');
    const blob = await imageRes.blob();
    if (!blob.size || blob.size > 15 * 1024 * 1024 || (blob.type && !blob.type.startsWith('image/'))) {
      throw new Error('Choose a valid image smaller than 15 MB.');
    }
    form.append('image', blob, 'scan.jpg');
  } else {
    form.append('image', { uri: params.imageUri, name: 'scan.jpg', type: 'image/jpeg' } as any);
  }
  const res = await timedFetch(`${getGeometryApiBase()}/v1/geometry/generate-from-image`, { method: 'POST', body: form });
  if (!res.ok) throw new Error(`Geometry backend failed (${res.status}): ${await res.text()}`);
  return waitForGeometryJob((await res.json()) as GeometryJobResponse, params.onProgress);
}

export async function generateGeometryFromPrompt(params: { label?: string; prompt?: string; onProgress?: (job: GeometryJobResponse) => void }): Promise<GeometryResponse> {
  const res = await fetch(`${getGeometryApiBase()}/v1/geometry/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ label: params.label || 'Object', confidence: 0.7, mode: 'approximate', prompt: params.prompt }),
  });
  if (!res.ok) throw new Error(`Geometry backend failed (${res.status}): ${await res.text()}`);
  return waitForGeometryJob((await res.json()) as GeometryJobResponse, params.onProgress);
}

export async function editGeometry(params: { label?: string; modelUrl?: string; prompt: string }): Promise<GeometryResponse> {
  const res = await fetch(`${getGeometryApiBase()}/v1/geometry/edit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ label: params.label || 'Object', model_url: params.modelUrl, prompt: params.prompt }),
  });
  if (!res.ok) throw new Error(`Edit backend failed (${res.status}): ${await res.text()}`);
  return waitForGeometryJob((await res.json()) as GeometryJobResponse);
}

export async function calibrateGeometry(params: { label?: string; modelUrl: string; measurement: string }): Promise<GeometryResponse> {
  const res = await timedFetch(`${getGeometryApiBase()}/v1/geometry/calibrate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ label: params.label || 'Object', model_url: params.modelUrl, measurement: params.measurement }),
  });
  if (!res.ok) throw new Error(`Calibration failed (${res.status}): ${await res.text()}`);
  return waitForGeometryJob((await res.json()) as GeometryJobResponse);
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
