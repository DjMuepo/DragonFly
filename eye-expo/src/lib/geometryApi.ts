export type GeometryResponse = {
  ok: boolean;
  engine: string;
  status: string;
  label: string;
  model_name: string;
  model_url: string;
  download_url: string;
  created_at: number;
  notes?: string;
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

async function generateFromLabel(label: string): Promise<GeometryResponse> {
  const res = await fetch(`${getGeometryApiBase()}/v1/geometry/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ label: label || 'Object', confidence: 0.7, mode: 'approximate' }),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Geometry backend failed (${res.status}): ${text}`);
  }

  const data = (await res.json()) as GeometryResponse;
  return {
    ...data,
    model_url: absoluteUrl(data.model_url),
    download_url: absoluteUrl(data.download_url),
  };
}

export async function generateGeometryFromImage(params: {
  imageUri?: string;
  label?: string;
  confidence?: number;
}): Promise<GeometryResponse> {
  const label = params.label || 'Object';

  if (!params.imageUri) {
    return generateFromLabel(label);
  }

  try {
    const form = new FormData();
    form.append('label', label);
    form.append('confidence', String(params.confidence ?? 0.7));

    if (typeof window !== 'undefined') {
      const imageRes = await fetch(params.imageUri);
      const blob = await imageRes.blob();
      form.append('image', blob, 'scan.jpg');
    } else {
      form.append('image', {
        uri: params.imageUri,
        name: 'scan.jpg',
        type: 'image/jpeg',
      } as any);
    }

    const res = await fetch(`${getGeometryApiBase()}/v1/geometry/generate-from-image`, {
      method: 'POST',
      body: form,
    });

    if (!res.ok) {
      return generateFromLabel(label);
    }

    const data = (await res.json()) as GeometryResponse;
    return {
      ...data,
      model_url: absoluteUrl(data.model_url),
      download_url: absoluteUrl(data.download_url),
    };
  } catch (err) {
    return generateFromLabel(label);
  }
}
