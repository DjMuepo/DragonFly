export type ReconstructionRecoveryInput = {
  jobId?: string | null;
  idempotencyKey?: string | null;
  serverJobAccepted?: boolean;
};

export type ReconstructionRecovery =
  | { action: 'resume-job'; jobId: string }
  | { action: 'resume-accepted'; idempotencyKey: string }
  | { action: 'submit-same-key'; idempotencyKey: string }
  | { action: 'start-new' };

export function reconstructionRecovery(input: ReconstructionRecoveryInput): ReconstructionRecovery {
  if (input.jobId) return { action: 'resume-job', jobId: input.jobId };
  if (input.idempotencyKey && input.serverJobAccepted) return { action: 'resume-accepted', idempotencyKey: input.idempotencyKey };
  if (input.idempotencyKey) return { action: 'submit-same-key', idempotencyKey: input.idempotencyKey };
  return { action: 'start-new' };
}

export function requiresPaidRetryConfirmation(errorCode?: string, providerKind?: string): boolean {
  return errorCode === 'provider_outcome_unknown' || errorCode === 'interrupted' || (errorCode === 'artifact_missing' && providerKind === 'ai');
}

export function projectArtifactHeaders(token?: string): Record<string, string> {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function fetchPrivateArtifact(url: string, token: string | undefined, fetcher: typeof fetch = fetch, signal?: AbortSignal): Promise<Blob> {
  const response = await fetcher(url, { headers: projectArtifactHeaders(token), cache: 'no-store', signal });
  if (response.status === 401) throw new Error('Your session expired. Sign in again to open this project.');
  if (!response.ok) throw new Error(response.status === 404 ? 'This project artifact is unavailable.' : `Could not download this artifact (${response.status}).`);
  return response.blob();
}

export async function retryInterruptedRequest<T>(request: () => Promise<T>, retries = 1): Promise<T> {
  let lastError: unknown;
  for (let attempt = 0; attempt <= retries; attempt += 1) {
    try {
      return await request();
    } catch (error) {
      lastError = error;
    }
  }
  throw lastError;
}
