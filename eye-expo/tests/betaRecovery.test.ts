import { createSessionAdapter } from '../src/lib/sessionAdapter.ts';
import { fetchPrivateArtifact, projectArtifactHeaders, reconstructionRecovery, requiresPaidRetryConfirmation, retryInterruptedRequest } from '../src/lib/betaRecovery.ts';
import { fetchMe } from '../src/lib/projectsApi.ts';

process.env.EXPO_PUBLIC_GEOMETRY_API_BASE = 'https://api.example.test';

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(message);
}

async function run() {
  const webSession = new Map<string, string>([['dragonfly.session-token', 'session-token']]);
  const legacy = new Map<string, string>([['dragonfly.session-token', 'legacy-token'], ['dragonfly-alpha-result', '{"authToken":"plaintext-legacy"}']]);
  const web = createSessionAdapter({
    platform: 'web',
    sessionStorage: {
      getItem: (key) => webSession.get(key) || null,
      setItem: (key, value) => { webSession.set(key, value); },
      removeItem: (key) => { webSession.delete(key); },
    },
    clearLegacyStorage: () => { legacy.delete('dragonfly.session-token'); legacy.delete('dragonfly-alpha-result'); },
    secure: { read: async () => 'must-not-read', write: async () => {}, clear: async () => {} },
  });
  assert(await web.read() === 'session-token', 'web restoration must use sessionStorage');
  assert(!legacy.has('dragonfly-alpha-result'), 'legacy persistent token state must be removed');
  await web.write('next-session');
  assert(webSession.get('dragonfly.session-token') === 'next-session', 'web login must persist only in sessionStorage');
  await web.clear();
  assert(await web.read() === null, 'web logout must clear the session token');

  let secureValue: string | null = 'keychain-token';
  let secureReads = 0;
  const native = createSessionAdapter({
    platform: 'native',
    sessionStorage: { getItem: () => 'unsafe-web-token', setItem: () => {}, removeItem: () => {} },
    secure: {
      read: async () => { secureReads += 1; return secureValue; },
      write: async (token) => { secureValue = token; },
      clear: async () => { secureValue = null; },
    },
  });
  assert(await native.read() === 'keychain-token' && secureReads === 1, 'native restoration must use secure storage');
  const previousFetch = globalThis.fetch;
  let restorationHeader = '';
  globalThis.fetch = async (input, init) => {
    if (String(input) !== 'https://api.example.test/v1/auth/me') throw new Error('session restoration used the wrong endpoint');
    restorationHeader = new Headers(init?.headers).get('Authorization') || '';
    return new Response(JSON.stringify({ ok: true, user: { id: 'u', name: 'U', email: 'u@example.test' }, session_expires_at: 123 }), { status: 200 });
  };
  const restoredUser = await fetchMe(await native.read() || '');
  globalThis.fetch = previousFetch;
  assert(restoredUser.user.id === 'u' && restorationHeader === 'Bearer keychain-token', 'restored SecureStore token must be validated with /auth/me');
  await native.write('new-keychain-token');
  assert(secureValue === 'new-keychain-token', 'native login must persist through secure storage');
  await native.clear();
  assert(secureValue === null, 'native logout must revoke the local secure token');

  assert(JSON.stringify(projectArtifactHeaders('secret')) === JSON.stringify({ Authorization: 'Bearer secret' }), 'private download auth must use a header');
  let requestUrl = '';
  let requestHeader = '';
  for (const filename of ['m.glb', 'm.stl']) {
    const blob = await fetchPrivateArtifact(`https://api.test/v1/projects/p/models/${filename}`, 'owner-token', async (input, init) => {
      requestUrl = String(input);
      requestHeader = new Headers(init?.headers).get('Authorization') || '';
      return new Response(new Blob([filename]), { status: 200 });
    });
    assert(await blob.text() === filename && requestHeader === 'Bearer owner-token', `${filename} download must send the bearer header`);
    assert(!requestUrl.includes('token=') && !requestUrl.includes('sig='), 'private artifacts must not put credentials in URLs');
  }
  let expired = false;
  try { await fetchPrivateArtifact('https://api.test/private', 'expired', async () => new Response('', { status: 401 })); }
  catch (error: any) { expired = error.message.includes('session expired'); }
  assert(expired, 'artifact 401 must surface session expiry');

  assert(reconstructionRecovery({ jobId: 'job-1', idempotencyKey: 'key-1' }).action === 'resume-job', 'known jobs resume by job ID');
  assert(reconstructionRecovery({ idempotencyKey: 'key-1', serverJobAccepted: true }).action === 'resume-accepted', 'accepted jobs resume by key');
  assert(reconstructionRecovery({ idempotencyKey: 'key-1' }).action === 'submit-same-key', 'uncertain POST retry reuses the key');
  assert(reconstructionRecovery({}).action === 'start-new', 'new scans create new keys');

  let attempts = 0;
  const retryHeaders = { 'Idempotency-Key': 'stable-crypto-key' };
  const seenKeys: string[] = [];
  const result = await retryInterruptedRequest(async () => {
    attempts += 1;
    seenKeys.push(retryHeaders['Idempotency-Key']);
    if (attempts === 1) throw new Error('network dropped');
    return 'accepted';
  });
  assert(result === 'accepted' && attempts === 2 && seenKeys.join(',') === 'stable-crypto-key,stable-crypto-key', 'interrupted POST is retried once with its caller-owned stable key');
  assert(requiresPaidRetryConfirmation('provider_outcome_unknown', 'ai'), 'uncertain prediction requires confirmation');
  assert(requiresPaidRetryConfirmation('interrupted', 'ai'), 'interrupted AI jobs require confirmation');
  assert(requiresPaidRetryConfirmation('artifact_missing', 'ai'), 'missing AI artifact requires confirmation');
  assert(!requiresPaidRetryConfirmation('provider_failed', 'procedural_fallback'), 'known non-paid failures do not require paid retry confirmation');
  console.log('beta recovery integration PASS');
}

void run();
