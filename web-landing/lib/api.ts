const API_BASE = (process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000').replace(/\/$/, '');

export async function getDesign(slug: string) {
  const res = await fetch(`${API_BASE}/v1/designs/${slug}`, { cache: 'no-store' });
  if (!res.ok) throw new Error(`design fetch failed ${res.status}`);
  return await res.json();
}

export async function listCreatorDesigns(creator: string) {
  const res = await fetch(`${API_BASE}/v1/creators/${encodeURIComponent(creator)}`, { cache: 'no-store' });
  if (!res.ok) throw new Error(`creator fetch failed ${res.status}`);
  return await res.json();
}


export function getDesignPageUrl(slug: string) {
  const origin = process.env.NEXT_PUBLIC_SITE_ORIGIN || 'https://example.com';
  return `${origin}/design/${slug}`;
}
