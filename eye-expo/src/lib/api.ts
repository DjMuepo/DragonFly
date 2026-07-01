import * as FileSystem from 'expo-file-system';

export type LicenseStatus = 'OK' | 'RESTRICTED' | 'UNKNOWN';
export type Novelty = 'COMMON' | 'SOMEWHAT_UNIQUE' | 'UNIQUE';
export type JobStatus = 'created' | 'uploaded' | 'processing' | 'done' | 'error';

export type MatchCandidate = {
  hosted?: boolean;
  externalUrl?: string;

  id: string;
  title: string;
  similarity: number;
  license: LicenseStatus;
  previewUrl?: string;
};

export type JobCreateResponse = {
  job_id: string;
  upload: {
    hero_put_url: string;
    burst_put_urls?: string[];
  };
};

export type JobGetResponse = {
  job_id: string;
  status: JobStatus;
  created_at: number;
  updated_at: number;
  result?: {
    matches: MatchCandidate[];
    novelty: Novelty;
    preview_url?: string;
    model_download_url?: string;
  };
  error?: string;
};

function baseUrl(): string {
  // Set this in your shell before running: EXPO_PUBLIC_API_BASE=http://YOUR_LAN_IP:8000
  return (process.env.EXPO_PUBLIC_API_BASE || 'http://localhost:8000').replace(/\/$/, '');
}

const API_BASE = baseUrl();


export function geometryBaseUrl(): string {
  const explicit = process.env.EXPO_PUBLIC_GEOMETRY_API_BASE;
  if (explicit) return explicit.replace(/\/$/, '');

  if (typeof window !== 'undefined' && window.location?.hostname) {
    const { protocol, hostname } = window.location;
    if (hostname.includes('-8081.app.github.dev')) {
      return `${protocol}//${hostname.replace('-8081.app.github.dev', '-8010.app.github.dev')}`;
    }
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
      return 'http://localhost:8010';
    }
  }

  return 'http://localhost:8010';
}

export function geometryUrl(pathOrUrl?: string): string | undefined {
  if (!pathOrUrl) return undefined;
  if (/^https?:\/\//i.test(pathOrUrl)) return pathOrUrl;
  return `${geometryBaseUrl()}${pathOrUrl.startsWith('/') ? pathOrUrl : `/${pathOrUrl}`}`;
}

export type GeometryGenerateResponse = {
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

async function appendImageToForm(form: FormData, uri: string) {
  if (typeof window !== 'undefined' && (uri.startsWith('blob:') || uri.startsWith('data:') || uri.startsWith('http'))) {
    const blob = await fetch(uri).then((r) => r.blob());
    form.append('image', blob, 'capture.jpg');
    return;
  }
  form.append('image', { uri, name: 'capture.jpg', type: 'image/jpeg' } as any);
}

export async function generateGeometryFromImage(uri: string, label: string = 'Object', confidence: number = 0.7): Promise<GeometryGenerateResponse> {
  const form = new FormData();
  form.append('label', label || 'Object');
  form.append('confidence', String(confidence));
  await appendImageToForm(form, uri);

  const res = await fetch(`${geometryBaseUrl()}/v1/geometry/generate-from-image`, {
    method: 'POST',
    body: form,
  });

  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`geometry image generation failed: ${res.status} ${text}`);
  }

  const data = (await res.json()) as GeometryGenerateResponse;
  return {
    ...data,
    model_url: geometryUrl(data.model_url) || '',
    download_url: geometryUrl(data.download_url) || '',
  };
}

export async function generateGeometryDraft(label: string = 'Object', confidence: number = 0.7): Promise<GeometryGenerateResponse> {
  const res = await fetch(`${geometryBaseUrl()}/v1/geometry/generate`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ label, confidence, mode: 'approximate' }),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`geometry generation failed: ${res.status} ${text}`);
  }
  const data = (await res.json()) as GeometryGenerateResponse;
  return {
    ...data,
    model_url: geometryUrl(data.model_url) || '',
    download_url: geometryUrl(data.download_url) || '',
  };
}

export async function createJob(payload: { include_burst?: boolean } = {}): Promise<JobCreateResponse> {
  const res = await fetch(`${baseUrl()}/v1/jobs`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ mode: 'snap_copy', include_burst: payload.include_burst ?? false }),
  });
  if (!res.ok) throw new Error(`createJob failed: ${res.status}`);
  return (await res.json()) as JobCreateResponse;
}

export async function uploadHero(job: JobCreateResponse, heroUri: string): Promise<void> {
  // Use FileSystem to read the image into binary and PUT it.
  const fileInfo = await FileSystem.getInfoAsync(heroUri);
  if (!fileInfo.exists) throw new Error('Hero image missing on device');

  const binary = await FileSystem.readAsStringAsync(heroUri, {
    encoding: FileSystem.EncodingType.Base64,
  });

  const bytes = Uint8Array.from(atob(binary), (c) => c.charCodeAt(0));

  const res = await fetch(job.upload.hero_put_url, {
    method: 'PUT',
    headers: {
      'content-type': 'image/jpeg',
    },
    body: bytes,
  });

  if (!res.ok) {
    const t = await res.text().catch(() => '');
    throw new Error(`uploadHero failed: ${res.status} ${t}`);
  }
}

function mapMatch(m: any): MatchCandidate {
  return {
    id: m.id,
    title: m.title,
    similarity: m.similarity,
    license: (m.license?.status ?? m.license ?? 'UNKNOWN') as LicenseStatus,
    previewUrl: m.preview_url ?? m.previewUrl,
    hosted: m.hosted ?? true,
    externalUrl: m.external_url ?? m.externalUrl,
  };
}

export async function getJob(jobId: string): Promise<JobGetResponse> {
  const res = await fetch(`${baseUrl()}/v1/jobs/${encodeURIComponent(jobId)}`);
  if (!res.ok) throw new Error(`getJob failed: ${res.status}`);
  const j = (await res.json()) as any;
  if (j?.result?.matches) {
    j.result.matches = j.result.matches.map(mapMatch);
  }
  return j as JobGetResponse;
}

export type SegmentResponse = { mask_url: string; confidence: number };

export async function segmentJob(jobId: string): Promise<SegmentResponse> {
  const res = await fetch(`${baseUrl()}/v1/segment`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ job_id: jobId }),
  });
  if (!res.ok) throw new Error(`segmentJob failed: ${res.status}`);
  return (await res.json()) as SegmentResponse;
}

export async function refineMask(jobId: string, tapX: number, tapY: number): Promise<SegmentResponse> {
  const res = await fetch(`${baseUrl()}/v1/segment/refine`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ job_id: jobId, tap_x: tapX, tap_y: tapY }),
  });
  if (!res.ok) throw new Error(`refineMask failed: ${res.status}`);
  return (await res.json()) as SegmentResponse;
}

// Tiny atob polyfill for RN/JS runtimes that may not provide it.
function atob(input: string): string {
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  const { decode } = require('base-64');
  return decode(input);
}


export type StructuralReport = {
  confidence: number;
  band: 'GREEN'|'YELLOW'|'RED'|string;
  primary_risk: string;
  load_type: string;
  stress_risk: number;
  printability_risk: number;
  notes: string[];
  suggestions: { id: string; label: string; action: any }[];
};

export async function structuralAnalyze(params: any): Promise<StructuralReport> {
  const res = await fetch(`${API_BASE}/v1/structural/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ params }),
  });
  if (!res.ok) throw new Error(`analyze failed ${res.status}`);
  return (await res.json()) as StructuralReport;
}

export async function structuralStrengthen(params: any): Promise<{params:any; report: StructuralReport}> {
  const res = await fetch(`${API_BASE}/v1/structural/strengthen`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ params }),
  });
  if (!res.ok) throw new Error(`strengthen failed ${res.status}`);
  return (await res.json()) as any;
}


export async function logEvent(e: {event: string; session_id?: string; user_id?: string; job_id?: string; model_id?: string; payload?: any;}): Promise<void> {
  try {
    await fetch(`${API_BASE}/v1/events/log`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(e),
    });
  } catch {
    // swallow
  }
}


export async function uploadReviewPhoto(uri: string): Promise<{filename: string}|null> {
  const form = new FormData();
  form.append('file', {
    uri,
    name: 'review.jpg',
    type: 'image/jpeg',
  } as any);

  const res = await fetch(`${API_BASE}/v1/review/photo`, {
    method: 'POST',
    body: form,
  });

  if (!res.ok) return null;
  return await res.json();
}


export async function simulateBasic(params: any, force: number, mode: 'custom'|'drop'|'side_load'|'twist' = 'custom'): Promise<{deflection_score:number; risk:string; force:number; mode:string; load_type?:string; force_vector?:any}> {
  const res = await fetch(`${API_BASE}/v1/simulate/basic`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ params, force, mode }),
  });
  if (!res.ok) throw new Error(`simulate failed ${res.status}`);
  return (await res.json()) as any;
}


export type VisionClassifyResponse = {
  object_family: string;
  confidence: number;
  top: { label: string; confidence: number }[];
};

export type VisionSegmentResponse = {
  ok: boolean;
  mask_filename: string;
  preview_filename: string;
};

export type VisionDraftResponse = {
  classification: VisionClassifyResponse;
  draft: {
    strategy: string;
    object_family: string;
    bbox: { x0: number; y0: number; x1: number; y1: number };
    aspect_ratio: number;
    estimated_depth_ratio: number;
    confidence: number;
    notes: string[];
  };
};

async function fileToForm(uri: string): Promise<FormData> {
  const form = new FormData();
  form.append('file', {
    uri,
    name: 'capture.jpg',
    type: 'image/jpeg',
  } as any);
  return form;
}

export async function classifyPhoto(uri: string): Promise<VisionClassifyResponse> {
  const form = await fileToForm(uri);
  const res = await fetch(`${API_BASE}/v1/vision/classify`, {
    method: 'POST',
    body: form,
  });
  if (!res.ok) throw new Error(`vision classify failed ${res.status}`);
  return await res.json();
}

export async function segmentPhoto(uri: string): Promise<VisionSegmentResponse> {
  const form = await fileToForm(uri);
  const res = await fetch(`${API_BASE}/v1/vision/segment`, {
    method: 'POST',
    body: form,
  });
  if (!res.ok) throw new Error(`vision segment failed ${res.status}`);
  return await res.json();
}

export async function retrievePhoto(uri: string, limit: number = 8): Promise<any> {
  const form = await fileToForm(uri);
  const res = await fetch(`${API_BASE}/v1/vision/retrieve?limit=${limit}`, {
    method: 'POST',
    body: form,
  });
  if (!res.ok) throw new Error(`vision retrieve failed ${res.status}`);
  return await res.json();
}

export async function draftPhoto(uri: string): Promise<VisionDraftResponse> {
  const form = await fileToForm(uri);
  const res = await fetch(`${API_BASE}/v1/vision/draft`, {
    method: 'POST',
    body: form,
  });
  if (!res.ok) throw new Error(`vision draft failed ${res.status}`);
  return await res.json();
}


export type VisionPreviewResponse = {
  classification: VisionClassifyResponse;
  draft: {
    strategy: string;
    object_family: string;
    bbox: { x0: number; y0: number; x1: number; y1: number };
    aspect_ratio: number;
    estimated_depth_ratio: number;
    confidence: number;
    notes: string[];
  };
  preview_filename: string;
  preview_url: string;
};

export async function previewPhoto(uri: string): Promise<VisionPreviewResponse> {
  const form = await fileToForm(uri);
  const res = await fetch(`${API_BASE}/v1/vision/preview`, {
    method: 'POST',
    body: form,
  });
  if (!res.ok) throw new Error(`vision preview failed ${res.status}`);
  return await res.json();
}


export type VisionGeometryPreviewResponse = {
  classification: VisionClassifyResponse;
  draft: {
    strategy: string;
    object_family: string;
    bbox: { x0: number; y0: number; x1: number; y1: number };
    aspect_ratio: number;
    estimated_depth_ratio: number;
    confidence: number;
    notes: string[];
  };
  geometry: {
    shape: 'box' | 'capsule' | 'wedge' | string;
    width: number;
    height: number;
    depth: number;
    notes: string[];
  };
};

export async function geometryPreviewPhoto(uri: string): Promise<VisionGeometryPreviewResponse> {
  const form = await fileToForm(uri);
  const res = await fetch(`${API_BASE}/v1/vision/geometry_preview`, {
    method: 'POST',
    body: form,
  });
  if (!res.ok) throw new Error(`vision geometry preview failed ${res.status}`);
  return await res.json();
}


export type VisionReconstructResponse = {
  classification: VisionClassifyResponse;
  supported_family: boolean;
  family: string;
  parametric_draft: {
    family: string;
    bbox: { x0: number; y0: number; x1: number; y1: number };
    aspect_ratio: number;
    estimated_depth_ratio: number;
    depth_meta: { depth_center: number; depth_edges: number; depth_contrast: number; confidence: number; notes: string[] };
    params: Record<string, any>;
    confidence: number;
    notes: string[];
  };
};

export async function reconstructPhoto(uri: string): Promise<VisionReconstructResponse> {
  const form = await fileToForm(uri);
  const res = await fetch(`${API_BASE}/v1/vision/reconstruct`, {
    method: 'POST',
    body: form,
  });
  if (!res.ok) throw new Error(`vision reconstruct failed ${res.status}`);
  return await res.json();
}


async function filesToForm(uris: string[]): Promise<FormData> {
  const form = new FormData();
  uris.forEach((uri, idx) => {
    form.append('files', {
      uri,
      name: `capture_${idx}.jpg`,
      type: 'image/jpeg',
    } as any);
  });
  return form;
}

export async function classifyPhotoSet(uris: string[]): Promise<any> {
  const form = await filesToForm(uris);
  const res = await fetch(`${API_BASE}/v1/vision/classify_multi`, { method: 'POST', body: form });
  if (!res.ok) throw new Error(`vision classify multi failed ${res.status}`);
  return await res.json();
}

export async function retrievePhotoSet(uris: string[], limit: number = 8): Promise<any> {
  const form = await filesToForm(uris);
  const res = await fetch(`${API_BASE}/v1/vision/retrieve_multi?limit=${limit}`, { method: 'POST', body: form });
  if (!res.ok) throw new Error(`vision retrieve multi failed ${res.status}`);
  return await res.json();
}

export async function reconstructPhotoSet(uris: string[]): Promise<any> {
  const form = await filesToForm(uris);
  const res = await fetch(`${API_BASE}/v1/vision/reconstruct_multi`, { method: 'POST', body: form });
  if (!res.ok) throw new Error(`vision reconstruct multi failed ${res.status}`);
  return await res.json();
}


export type VisionExportStlResponse = {
  ok: boolean;
  filename: string;
  download_url: string;
  meta: {
    ok: boolean;
    out_path: string;
    is_watertight: boolean;
    faces: number;
    vertices: number;
    bounds: number[][];
  };
};

export async function exportDraftStl(parametricDraft: any): Promise<VisionExportStlResponse> {
  const res = await fetch(`${API_BASE}/v1/vision/export_stl`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ parametric_draft: parametricDraft }),
  });
  if (!res.ok) throw new Error(`vision export stl failed ${res.status}`);
  return await res.json();
}


export type VisionPrintabilityResponse = {
  family: string;
  print_confidence: number;
  band: 'HIGH' | 'MEDIUM' | 'LOW';
  risks: string[];
  notes: string[];
  suggestions: string[];
  checks: Record<string, boolean>;
  recommended_material: string;
};

export async function analyzePrintability(parametricDraft: any): Promise<VisionPrintabilityResponse> {
  const res = await fetch(`${API_BASE}/v1/vision/printability`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ parametric_draft: parametricDraft }),
  });
  if (!res.ok) throw new Error(`vision printability failed ${res.status}`);
  return await res.json();
}


export type NearbyPrinter = {
  id: string;
  name: string;
  lat: number;
  lon: number;
  materials: string[];
  max_x: number;
  max_y: number;
  max_z: number;
  same_day: boolean;
  distance_miles: number;
};

export async function findNearbyPrinters(lat: number, lon: number, material?: string): Promise<{printers: NearbyPrinter[]}> {
  const res = await fetch(`${API_BASE}/v1/printers/nearby`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ lat, lon, material }),
  });
  if (!res.ok) throw new Error(`nearby printers failed ${res.status}`);
  return await res.json();
}

export async function submitPrinterJob(payload: any): Promise<any> {
  const res = await fetch(`${API_BASE}/v1/printers/submit`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`printer submit failed ${res.status}`);
  return await res.json();
}


export type SharedDesign = {
  id: string;
  slug: string;
  title: string;
  description: string;
  creator: string;
  family: string;
  print_confidence?: number;
  is_public: boolean;
  created_at: number;
  preview_url?: string;
  stl_url?: string;
  likes: number;
  remix_count: number;
  tags: string[];
};

export async function listDesigns(): Promise<{designs: SharedDesign[]}> {
  const res = await fetch(`${API_BASE}/v1/designs`);
  if (!res.ok) throw new Error(`design list failed ${res.status}`);
  return await res.json();
}

export async function getDesign(slug: string): Promise<{ok:boolean; design?: SharedDesign; error?: string}> {
  const res = await fetch(`${API_BASE}/v1/designs/${slug}`);
  if (!res.ok) throw new Error(`design get failed ${res.status}`);
  return await res.json();
}

export async function publishDesign(payload: any): Promise<{ok:boolean; design: SharedDesign; share_url: string; app_deep_link: string}> {
  const res = await fetch(`${API_BASE}/v1/designs/publish`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`design publish failed ${res.status}`);
  return await res.json();
}


export async function signupUser(payload: {email:string; password:string; name?:string; interests?:string[]; skill_level?:string}) {
  const res = await fetch(`${API_BASE}/v1/auth/signup`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`signup failed ${res.status}`);
  return await res.json();
}

export async function loginUser(payload: {email:string; password:string}) {
  const res = await fetch(`${API_BASE}/v1/auth/login`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`login failed ${res.status}`);
  return await res.json();
}

export async function getMe(token: string) {
  const res = await fetch(`${API_BASE}/v1/me?token=${encodeURIComponent(token)}`);
  if (!res.ok) throw new Error(`me failed ${res.status}`);
  return await res.json();
}

export async function listMyDesigns(token: string) {
  const res = await fetch(`${API_BASE}/v1/my-designs?token=${encodeURIComponent(token)}`);
  if (!res.ok) throw new Error(`my designs failed ${res.status}`);
  return await res.json();
}

export async function likeDesign(slug: string) {
  const res = await fetch(`${API_BASE}/v1/designs/${slug}/like`, { method: 'POST' });
  if (!res.ok) throw new Error(`like design failed ${res.status}`);
  return await res.json();
}


export async function pushTrainingEvent(payload: any) {
  const res = await fetch(`${API_BASE}/v1/training/event`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`training event failed ${res.status}`);
  return await res.json();
}

export async function aggregateTraining(limit: number = 5000) {
  const res = await fetch(`${API_BASE}/v1/training/aggregate`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ limit }),
  });
  if (!res.ok) throw new Error(`training aggregate failed ${res.status}`);
  return await res.json();
}

export async function getTrainingFeatures() {
  const res = await fetch(`${API_BASE}/v1/training/features`);
  if (!res.ok) throw new Error(`training features failed ${res.status}`);
  return await res.json();
}

export async function adaptDraftWithLearnedFeatures(parametricDraft: any) {
  const res = await fetch(`${API_BASE}/v1/training/adapt`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ parametric_draft: parametricDraft }),
  });
  if (!res.ok) throw new Error(`training adapt failed ${res.status}`);
  return await res.json();
}


export async function applyLearnedDefaults(parametricDraft: any) {
  const res = await fetch(`${API_BASE}/v1/vision/apply_learned_defaults`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ parametric_draft: parametricDraft }),
  });
  if (!res.ok) throw new Error(`apply learned defaults failed ${res.status}`);
  return await res.json();
}


export async function hostDesignPreview(slug: string) {
  const res = await fetch(`${API_BASE}/v1/designs/${slug}/host-preview`, { method: 'POST' });
  if (!res.ok) throw new Error(`host preview failed ${res.status}`);
  return await res.json();
}


export async function enqueueBackgroundJob(kind: string, payload: any = {}) {
  const res = await fetch(`${API_BASE}/v1/jobs`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ kind, payload }),
  });
  if (!res.ok) throw new Error(`enqueue job failed ${res.status}`);
  return await res.json();
}

export async function listBackgroundJobs(limit: number = 100) {
  const res = await fetch(`${API_BASE}/v1/jobs?limit=${limit}`);
  if (!res.ok) throw new Error(`list jobs failed ${res.status}`);
  return await res.json();
}

export async function updateBackgroundJob(jobId: string, payload: {status?: string; result?: any}) {
  const res = await fetch(`${API_BASE}/v1/jobs/${jobId}/status`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`update job failed ${res.status}`);
  return await res.json();
}

export async function listPrinterNodes() {
  const res = await fetch(`${API_BASE}/v1/printers/nodes`);
  if (!res.ok) throw new Error(`printer nodes failed ${res.status}`);
  return await res.json();
}

export async function updatePrinterNodeStatus(nodeId: string, payload: {is_online?: boolean; queue_depth?: number; materials?: string[]}) {
  const res = await fetch(`${API_BASE}/v1/printers/nodes/${nodeId}/status`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`update printer node failed ${res.status}`);
  return await res.json();
}


export async function runJobsOnce(limit: number = 25) {
  const res = await fetch(`${API_BASE}/v1/jobs/run-once`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ limit }),
  });
  if (!res.ok) throw new Error(`run jobs failed ${res.status}`);
  return await res.json();
}

export async function getPostgresHealth() {
  const res = await fetch(`${API_BASE}/v1/db/postgres-health`);
  if (!res.ok) throw new Error(`postgres health failed ${res.status}`);
  return await res.json();
}


export async function listChallenges() {
  const res = await fetch(`${API_BASE}/v1/challenges`);
  if (!res.ok) throw new Error(`list challenges failed ${res.status}`);
  return await res.json();
}

export async function getChallenge(challengeId: string) {
  const res = await fetch(`${API_BASE}/v1/challenges/${challengeId}`);
  if (!res.ok) throw new Error(`get challenge failed ${res.status}`);
  return await res.json();
}

export async function submitChallengeEntry(challengeId: string, payload: any) {
  const res = await fetch(`${API_BASE}/v1/challenges/${challengeId}/submit`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`submit challenge failed ${res.status}`);
  return await res.json();
}


export async function runLiveDetection(payload: {label?: string; confidence?: number; is_paid?: boolean; stable_frames?: number}) {
  const res = await fetch(`${API_BASE}/v1/vision/live-detect`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`live detect failed ${res.status}`);
  return await res.json();
}


export async function generateFixObjectPlan(payload: {label?: string; confidence?: number; user_notes?: string}) {
  const res = await fetch(`${API_BASE}/v1/fix-object/plan`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`fix object plan failed ${res.status}`);
  return await res.json();
}


export async function routeCameraAction(payload: {label?: string; confidence?: number; is_paid?: boolean; stable_frames?: number; user_notes?: string}) {
  const res = await fetch(`${API_BASE}/v1/camera/route`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`camera route failed ${res.status}`);
  return await res.json();
}


export async function getDiscoveryRadar(payload: {lat?: number; lon?: number; is_paid?: boolean}) {
  const res = await fetch(`${API_BASE}/v1/radar/discovery`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`radar discovery failed ${res.status}`);
  return await res.json();
}


export async function generateArPlacementPlan(payload: {design_title?: string; family?: string; surface?: string; width_mm?: number; height_mm?: number; depth_mm?: number}) {
  const res = await fetch(`${API_BASE}/v1/ar/placement-plan`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`ar placement plan failed ${res.status}`);
  return await res.json();
}


export async function createObjectDnaRecord(payload: any) {
  const res = await fetch(`${API_BASE}/v1/object-dna`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(payload) });
  if (!res.ok) throw new Error(`create object dna failed ${res.status}`);
  return await res.json();
}
export async function listObjectDnaRecords(limit: number = 100) {
  const res = await fetch(`${API_BASE}/v1/object-dna?limit=${limit}`);
  if (!res.ok) throw new Error(`list object dna failed ${res.status}`);
  return await res.json();
}
export async function getObjectDnaRecord(recordId: string) {
  const res = await fetch(`${API_BASE}/v1/object-dna/${recordId}`);
  if (!res.ok) throw new Error(`get object dna failed ${res.status}`);
  return await res.json();
}
export async function updateObjectDnaRecord(recordId: string, payload: any) {
  const res = await fetch(`${API_BASE}/v1/object-dna/${recordId}`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(payload) });
  if (!res.ok) throw new Error(`update object dna failed ${res.status}`);
  return await res.json();
}


export async function createObjectDnaFromScan(payload: any) { const res = await fetch(`${API_BASE}/v1/object-dna/flows/scan`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(payload) }); if (!res.ok) throw new Error(`object dna scan flow failed ${res.status}`); return await res.json(); }
export async function createObjectDnaFromFix(payload: any) { const res = await fetch(`${API_BASE}/v1/object-dna/flows/fix`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(payload) }); if (!res.ok) throw new Error(`object dna fix flow failed ${res.status}`); return await res.json(); }
export async function createObjectDnaFromAr(payload: any) { const res = await fetch(`${API_BASE}/v1/object-dna/flows/ar`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(payload) }); if (!res.ok) throw new Error(`object dna ar flow failed ${res.status}`); return await res.json(); }
export async function writeObjectDnaPrintOutcome(payload: any) { const res = await fetch(`${API_BASE}/v1/object-dna/flows/print`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(payload) }); if (!res.ok) throw new Error(`object dna print flow failed ${res.status}`); return await res.json(); }
export async function appendObjectDnaEdit(payload: any) { const res = await fetch(`${API_BASE}/v1/object-dna/flows/edit`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(payload) }); if (!res.ok) throw new Error(`object dna edit flow failed ${res.status}`); return await res.json(); }


export async function getAiLearningSummary(limit: number = 500) {
  const res = await fetch(`${API_BASE}/v1/ai/learning-summary?limit=${limit}`);
  if (!res.ok) throw new Error(`ai learning summary failed ${res.status}`);
  return await res.json();
}


export async function acceptScanFlow(payload: any) {
  const res = await fetch(`${API_BASE}/v1/flows/scan/accept`, { method:'POST', headers:{'content-type':'application/json'}, body: JSON.stringify(payload) });
  if (!res.ok) throw new Error(`scan accept failed ${res.status}`);
  return await res.json();
}
export async function acceptFixFlow(payload: any) {
  const res = await fetch(`${API_BASE}/v1/flows/fix/accept`, { method:'POST', headers:{'content-type':'application/json'}, body: JSON.stringify(payload) });
  if (!res.ok) throw new Error(`fix accept failed ${res.status}`);
  return await res.json();
}
export async function confirmArFlow(payload: any) {
  const res = await fetch(`${API_BASE}/v1/flows/ar/confirm`, { method:'POST', headers:{'content-type':'application/json'}, body: JSON.stringify(payload) });
  if (!res.ok) throw new Error(`ar confirm failed ${res.status}`);
  return await res.json();
}
export async function completePrintFlow(payload: any) {
  const res = await fetch(`${API_BASE}/v1/flows/print/complete`, { method:'POST', headers:{'content-type':'application/json'}, body: JSON.stringify(payload) });
  if (!res.ok) throw new Error(`print complete failed ${res.status}`);
  return await res.json();
}
export async function appendEditFlow(payload: any) {
  const res = await fetch(`${API_BASE}/v1/flows/edit/append`, { method:'POST', headers:{'content-type':'application/json'}, body: JSON.stringify(payload) });
  if (!res.ok) throw new Error(`edit append failed ${res.status}`);
  return await res.json();
}


export async function checkAutoSaveSubscription(payload: {is_paid?: boolean}) {
  const res = await fetch(`${API_BASE}/v1/subscription/auto-save-check`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`auto-save subscription check failed ${res.status}`);
  return await res.json();
}


export async function getAdminFeatures() {
  const res = await fetch(`${API_BASE}/v1/admin/features`);
  if (!res.ok) throw new Error(`get admin features failed ${res.status}`);
  return await res.json();
}

export async function checkFeatureAccess(payload: any) {
  const res = await fetch(`${API_BASE}/v1/admin/features/check`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`feature access check failed ${res.status}`);
  return await res.json();
}

export async function updateAdminFeature(payload: any) {
  const res = await fetch(`${API_BASE}/v1/admin/features/update`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`feature update failed ${res.status}`);
  return await res.json();
}

export async function setAdminFeatureOverride(payload: any) {
  const res = await fetch(`${API_BASE}/v1/admin/features/override`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`feature override failed ${res.status}`);
  return await res.json();
}

export async function getAdminFeatureAudit(limit: number = 100) {
  const res = await fetch(`${API_BASE}/v1/admin/features/audit?limit=${limit}`);
  if (!res.ok) throw new Error(`feature audit failed ${res.status}`);
  return await res.json();
}


export async function createBehaviorSession(payload: any) {
  const res = await fetch(`${API_BASE}/v1/behavior/session/create`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`behavior session create failed ${res.status}`);
  return await res.json();
}

export async function runGhostSave(payload: any) {
  const res = await fetch(`${API_BASE}/v1/behavior/ghost-save`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`ghost save failed ${res.status}`);
  return await res.json();
}

export async function getExitWarning(payload: any) {
  const res = await fetch(`${API_BASE}/v1/behavior/exit-warning`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`exit warning failed ${res.status}`);
  return await res.json();
}

export async function recoverBehaviorSession(payload: any) {
  const res = await fetch(`${API_BASE}/v1/behavior/recover`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`recover session failed ${res.status}`);
  return await res.json();
}

export async function recordPrintSuccess(payload: any) {
  const res = await fetch(`${API_BASE}/v1/behavior/print-success`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`print success failed ${res.status}`);
  return await res.json();
}

export async function getBehaviorEvents(limit: number = 100) {
  const res = await fetch(`${API_BASE}/v1/behavior/events?limit=${limit}`);
  if (!res.ok) throw new Error(`behavior events failed ${res.status}`);
  return await res.json();
}


export async function listInvites() {
  const res = await fetch(`${API_BASE}/v1/invites`);
  if (!res.ok) throw new Error(`list invites failed ${res.status}`);
  return await res.json();
}

export async function createInviteCode(payload: any) {
  const res = await fetch(`${API_BASE}/v1/invites/create`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`create invite failed ${res.status}`);
  return await res.json();
}

export async function validateInviteCode(payload: any) {
  const res = await fetch(`${API_BASE}/v1/invites/validate`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`validate invite failed ${res.status}`);
  return await res.json();
}

export async function redeemInviteCode(payload: any) {
  const res = await fetch(`${API_BASE}/v1/invites/redeem`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`redeem invite failed ${res.status}`);
  return await res.json();
}

export async function disableInviteCode(payload: any) {
  const res = await fetch(`${API_BASE}/v1/invites/disable`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`disable invite failed ${res.status}`);
  return await res.json();
}


export async function createShareLink(payload: any) {
  const res = await fetch(`${API_BASE}/v1/share/create`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`share create failed ${res.status}`);
  return await res.json();
}

export async function listShareLinks(limit: number = 100) {
  const res = await fetch(`${API_BASE}/v1/share/list?limit=${limit}`);
  if (!res.ok) throw new Error(`share list failed ${res.status}`);
  return await res.json();
}
