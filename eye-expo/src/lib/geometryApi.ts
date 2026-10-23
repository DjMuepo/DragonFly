import { useSnapStore } from './useSnapStore';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Crypto from 'expo-crypto';

export type GeometryResponse = {
  ok: boolean;
  job_id: string;
  project_id?: string;
  revision_id?: string;
  revision_seq?: number;
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
  quality_mode?: 'FAST' | 'STANDARD' | 'HIGH_QUALITY';
  preprocessing?: {
    quality_mode: 'FAST' | 'STANDARD' | 'HIGH_QUALITY';
    source_dimensions: [number, number];
    output_dimensions: [number, number];
    foreground_segmenter: string;
    object_crop_applied: boolean;
    resized: boolean;
    source_images: number;
    hidden_surfaces: string;
  };
  hidden_surface_uncertainty?: string;
  reconstruction_quality?: {
    status: 'warning' | 'not_flagged';
    fidelity_verified: false;
    warnings: string[];
    limitation: string;
  };
};

export type GeometryJobResponse = {
  job_id: string;
  status: 'queued' | 'processing' | 'done' | 'error';
  progress: number;
  provider: string;
  provider_kind: 'ai' | 'procedural_fallback' | 'deterministic_edit' | 'visual_only' | 'calibration';
  quality_mode?: 'FAST' | 'STANDARD' | 'HIGH_QUALITY';
  stage?: string;
  stage_detail?: string;
  preprocessing?: GeometryResponse['preprocessing'];
  error?: string;
  error_code?: string;
  project_id?: string;
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

function authHeaders(): Record<string, string> {
  const token = useSnapStore.getState().authToken;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export function newIdempotencyKey(): string {
  return Crypto.randomUUID();
}

export class GeometryJobFailed extends Error {
  code?: string;
  providerKind?: string;
  constructor(job: GeometryJobResponse) {
    super(`Generation failed — Job DF-${job.job_id}: ${job.error || `${job.provider} reconstruction failed`}`);
    this.code = job.error_code;
    this.providerKind = job.provider_kind;
  }
}

async function failureMessage(res: Response, label: string): Promise<string> {
  if (res.status === 401 && useSnapStore.getState().authToken) {
    useSnapStore.getState().setAuth(undefined, undefined);
    return 'Your session expired. Sign in again to keep saving your work.';
  }
  const text = await res.text().catch(() => '');
  return `${label} (${res.status}): ${text}`;
}

async function postWithRetry(url: string, init: RequestInit): Promise<Response> {
  // Same Idempotency-Key makes a network-level retry safe: the backend returns the original job.
  try {
    return await timedFetch(url, init);
  } catch {
    return await timedFetch(url, init);
  }
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
    if (current.status === 'error') throw new GeometryJobFailed(current);
    await new Promise((resolve) => setTimeout(resolve, 1000));
    let response: Response | null = null;
    for (let retry = 0; retry < 3 && !response; retry += 1) {
      try {
        response = await timedFetch(`${getGeometryApiBase()}/v1/geometry/jobs/${encodeURIComponent(current.job_id)}`, { headers: authHeaders() });
      } catch (error) {
        if (retry === 2) throw error;
        await new Promise((resolve) => setTimeout(resolve, 2000));
      }
    }
    if (!response || !response.ok) throw new Error(response ? await failureMessage(response, 'Geometry job lookup failed') : 'Geometry job lookup failed');
    current = (await response.json()) as GeometryJobResponse;
  }
  throw new Error('Geometry generation timed out before the backend returned a model.');
}

export async function generateGeometryFromImage(params: { imageUri?: string; label?: string; confidence?: number; qualityMode?: 'FAST' | 'STANDARD' | 'HIGH_QUALITY'; idempotencyKey?: string; onProgress?: (job: GeometryJobResponse) => void }): Promise<GeometryResponse> {
  const label = params.label || 'Object';
  if (!params.imageUri) throw new Error('Choose or capture a photo before generating a model.');
  const idempotencyKey = params.idempotencyKey || newIdempotencyKey();
  const pendingKey = 'dragonfly.pending-reconstruction';
  await AsyncStorage.setItem(pendingKey, JSON.stringify({ idempotencyKey, jobId: null, label, imageUri: params.imageUri }));
  const form = new FormData();
  form.append('label', label);
  form.append('confidence', String(params.confidence ?? 0.7));
  form.append('quality_mode', params.qualityMode ?? 'STANDARD');
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
  const res = await postWithRetry(`${getGeometryApiBase()}/v1/geometry/generate-from-image`, { method: 'POST', body: form, headers: { ...authHeaders(), 'Idempotency-Key': idempotencyKey } });
  if (!res.ok) throw new Error(await failureMessage(res, 'Geometry backend failed'));
  const initial = (await res.json()) as GeometryJobResponse;
  await AsyncStorage.setItem(pendingKey, JSON.stringify({ idempotencyKey, jobId: initial.job_id, label, imageUri: params.imageUri }));
  try {
    const result = await waitForGeometryJob(initial, (job) => {
      void AsyncStorage.setItem(pendingKey, JSON.stringify({ idempotencyKey, jobId: job.job_id, label, imageUri: params.imageUri }));
      params.onProgress?.(job);
    });
    await AsyncStorage.removeItem(pendingKey);
    return result;
  } catch (error) {
    if (error instanceof GeometryJobFailed) await AsyncStorage.removeItem(pendingKey);
    throw error;
  }
}

export async function resumeGeometryJob(jobId: string, onProgress?: (job: GeometryJobResponse) => void): Promise<GeometryResponse> {
  const response = await timedFetch(`${getGeometryApiBase()}/v1/geometry/jobs/${encodeURIComponent(jobId)}`, { headers: authHeaders() });
  if (!response.ok) throw new Error(await failureMessage(response, 'Could not resume the existing reconstruction job'));
  try {
    const result = await waitForGeometryJob((await response.json()) as GeometryJobResponse, onProgress);
    await AsyncStorage.removeItem('dragonfly.pending-reconstruction');
    return result;
  } catch (error) {
    if (error instanceof GeometryJobFailed) await AsyncStorage.removeItem('dragonfly.pending-reconstruction');
    throw error;
  }
}

export async function findGeometryJobByKey(key: string): Promise<GeometryJobResponse | null> {
  const response = await timedFetch(`${getGeometryApiBase()}/v1/geometry/idempotency`, { headers: { ...authHeaders(), 'Idempotency-Key': key } });
  if (response.status === 404) return null;
  if (!response.ok) throw new Error(await failureMessage(response, 'Could not recover the existing reconstruction request'));
  return response.json() as Promise<GeometryJobResponse>;
}

export async function generateGeometryFromPrompt(params: { label?: string; prompt?: string; onProgress?: (job: GeometryJobResponse) => void }): Promise<GeometryResponse> {
  const res = await fetch(`${getGeometryApiBase()}/v1/geometry/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ label: params.label || 'Object', confidence: 0.7, mode: 'approximate', prompt: params.prompt }),
  });
  if (!res.ok) throw new Error(`Geometry backend failed (${res.status}): ${await res.text()}`);
  return waitForGeometryJob((await res.json()) as GeometryJobResponse, params.onProgress);
}

export async function editGeometry(params: { label?: string; modelUrl?: string; prompt: string; projectId?: string }): Promise<GeometryResponse> {
  const res = await postWithRetry(`${getGeometryApiBase()}/v1/geometry/edit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders(), 'Idempotency-Key': newIdempotencyKey() },
    body: JSON.stringify({ label: params.label || 'Object', model_url: params.modelUrl, prompt: params.prompt, project_id: params.projectId }),
  });
  if (!res.ok) throw new Error(await failureMessage(res, 'Edit backend failed'));
  return waitForGeometryJob((await res.json()) as GeometryJobResponse);
}

export async function calibrateGeometry(params: { label?: string; modelUrl: string; measurement: string; projectId?: string }): Promise<GeometryResponse> {
  const res = await postWithRetry(`${getGeometryApiBase()}/v1/geometry/calibrate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders(), 'Idempotency-Key': newIdempotencyKey() },
    body: JSON.stringify({ label: params.label || 'Object', model_url: params.modelUrl, measurement: params.measurement, project_id: params.projectId }),
  });
  if (!res.ok) throw new Error(await failureMessage(res, 'Calibration failed'));
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
