import type { ServerProject } from './projectMapping';

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

function base(): string {
  const configured = process.env.EXPO_PUBLIC_GEOMETRY_API_BASE || process.env.EXPO_PUBLIC_API_BASE;
  if (!configured) throw new Error('Set EXPO_PUBLIC_GEOMETRY_API_BASE to the public backend URL.');
  return configured.replace(/\/$/, '');
}

async function request<T>(path: string, options: { method?: string; token?: string; body?: unknown } = {}): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 30000);
  try {
    const res = await fetch(`${base()}${path}`, {
      method: options.method || 'GET',
      headers: { ...(options.body ? { 'Content-Type': 'application/json' } : {}), ...(options.token ? { Authorization: `Bearer ${options.token}` } : {}) },
      body: options.body ? JSON.stringify(options.body) : undefined,
      signal: controller.signal,
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const detail = data?.error || (typeof data?.detail === 'string' ? data.detail : '') || `Request failed (${res.status})`;
      throw new ApiError(detail, res.status);
    }
    return data as T;
  } catch (error: any) {
    if (controller.signal.aborted) throw new ApiError('The connection timed out. Check your network and try again.', 0);
    if (error instanceof ApiError) throw error;
    throw new ApiError(error?.message || 'The service is unreachable.', 0);
  } finally {
    clearTimeout(timeout);
  }
}

export type AuthUser = { id: string; email: string; name: string };
export type AuthResult = { ok: boolean; token: string; expires_at: number; user: AuthUser };

export const signUp = (email: string, password: string, name: string) => request<AuthResult>('/v1/auth/signup', { method: 'POST', body: { email, password, name } });
export const logIn = (email: string, password: string) => request<AuthResult>('/v1/auth/login', { method: 'POST', body: { email, password } });
export const logOut = (token: string) => request<{ ok: boolean }>('/v1/auth/logout', { method: 'POST', token });
export const fetchMe = (token: string) => request<{ ok: boolean; user: AuthUser; session_expires_at: number }>('/v1/auth/me', { token });

export const listProjects = (token: string) => request<{ ok: boolean; projects: ServerProject[] }>('/v1/projects', { token });
export const getProject = (token: string, id: string) => request<{ ok: boolean; project: ServerProject }>(`/v1/projects/${encodeURIComponent(id)}`, { token });
export const renameProject = (token: string, id: string, name: string) => request<{ ok: boolean; project: ServerProject }>(`/v1/projects/${encodeURIComponent(id)}`, { method: 'PATCH', token, body: { name } });
export const deleteProject = (token: string, id: string) => request<{ ok: boolean }>(`/v1/projects/${encodeURIComponent(id)}`, { method: 'DELETE', token });
export const setProjectCursor = (token: string, id: string, index: number) => request<{ ok: boolean }>(`/v1/projects/${encodeURIComponent(id)}/cursor`, { method: 'PUT', token, body: { index } });
export const saveGuestJobs = (token: string, jobIds: string[], name?: string) => request<{ ok: boolean; project: ServerProject }>('/v1/projects', { method: 'POST', token, body: { from_job_ids: jobIds, name } });
