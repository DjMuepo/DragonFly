import { Linking, Platform } from 'react-native';
import * as FileSystem from 'expo-file-system/legacy';

export function isProjectArtifact(url?: string): boolean {
  return !!url && /\/v1\/projects\/[^/]+\/models\//.test(url);
}

export async function fetchProjectArtifact(url: string, token?: string, signal?: AbortSignal): Promise<Blob> {
  if (!isProjectArtifact(url)) throw new Error('This is not a project artifact URL.');
  const response = await fetch(url, { headers: token ? { Authorization: `Bearer ${token}` } : {}, cache: 'no-store', signal });
  if (response.status === 401) throw new Error('Your session expired. Sign in again to open this project.');
  if (!response.ok) throw new Error(response.status === 404 ? 'This project artifact is unavailable.' : `Could not download this artifact (${response.status}).`);
  return response.blob();
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
  const result = await FileSystem.downloadAsync(url, destination, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
  if (result.status !== 200) throw new Error(`Could not download this artifact (${result.status}).`);
  await Linking.openURL(result.uri);
}
