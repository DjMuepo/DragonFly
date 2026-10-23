import { ApiError, listProjects } from '../src/lib/projectsApi.ts';

process.env.EXPO_PUBLIC_GEOMETRY_API_BASE = 'https://api.example.test';

const originalFetch = globalThis.fetch;

async function run() {
  let requests = 0;
  globalThis.fetch = async (input, init) => {
    requests += 1;
    if (String(input) !== 'https://api.example.test/v1/projects') throw new Error('wrong URL');
    if (new Headers(init?.headers).get('Authorization') !== 'Bearer test-token') throw new Error('missing bearer token');
    return new Response(JSON.stringify({ ok: false, detail: 'Service unavailable' }), { status: 503 });
  };
  try {
    await listProjects('test-token');
    throw new Error('expected 503');
  } catch (error) {
    if (!(error instanceof ApiError) || error.status !== 503 || error.message !== 'Service unavailable') throw error;
  }
  if (requests !== 1) throw new Error(`expected one request, got ${requests}`);

  globalThis.fetch = async () => new Response(JSON.stringify({ detail: 'Your session has expired. Sign in again.' }), { status: 401 });
  try {
    await listProjects('expired-token');
    throw new Error('expected 401');
  } catch (error) {
    if (!(error instanceof ApiError) || error.status !== 401) throw error;
  }

  globalThis.fetch = async () => { throw new TypeError('network unavailable'); };
  try {
    await listProjects('test-token');
    throw new Error('expected network error');
  } catch (error) {
    if (!(error instanceof ApiError) || error.status !== 0 || error.message !== 'network unavailable') throw error;
  }
  console.log('API failure recovery PASS');
}

run().finally(() => { globalThis.fetch = originalFetch; });
