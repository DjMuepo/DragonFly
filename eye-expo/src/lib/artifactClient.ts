import { Linking, Platform } from 'react-native';
import * as FileSystem from 'expo-file-system/legacy';
import { fetchPrivateArtifact, projectArtifactHeaders } from './betaRecovery';

export function isProjectArtifact(url?: string): boolean {
  return !!url && /\/v1\/projects\/[^/]+\/models\//.test(url);
}

export async function fetchProjectArtifact(url: string, token?: string, signal?: AbortSignal): Promise<Blob> {
  if (!isProjectArtifact(url)) throw new Error('This is not a project artifact URL.');
  return fetchPrivateArtifact(url, token, fetch, signal);
}

export async function openArtifact(url: string, token?: string, filename?: string): Promise<void> {
  if (!isProjectArtifact(url)) {
    await Linking.openURL(url);
    return;
  }
  if (Platform.OS === 'web') {
    const blob = await fetchProjectArtifact(url, token);
    const localUrl = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = localUrl;
    anchor.download = filename || url.split('/').pop() || 'dragonfly-model';
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    setTimeout(() => URL.revokeObjectURL(localUrl), 60_000);
    return;
  }
  if (!FileSystem.cacheDirectory) throw new Error('Device cache is unavailable.');
  const safeName = (filename || url.split('/').pop() || 'dragonfly-model').replace(/[^a-zA-Z0-9._-]/g, '_');
  const destination = `${FileSystem.cacheDirectory}dragonfly-${Date.now()}-${safeName}`;
  const result = await FileSystem.downloadAsync(url, destination, { headers: projectArtifactHeaders(token) });
  if (result.status !== 200) throw new Error(`Could not download this artifact (${result.status}).`);
  await Linking.openURL(result.uri);
}
