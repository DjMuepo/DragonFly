import { useEffect, useState } from 'react';
import { View, Text, StyleSheet, Pressable, ActivityIndicator } from 'react-native';
import { useRouter } from 'expo-router';
import { useSnapStore } from '../lib/useSnapStore';
import { ApiError, getProject, saveGuestJobs, setProjectCursor } from '../lib/projectsApi';

type Props = { refresh?: boolean };

export function ProjectPanel({ refresh = true }: Props) {
  const router = useRouter();
  const authToken = useSnapStore((s) => s.authToken);
  const projectId = useSnapStore((s) => s.projectId);
  const projectName = useSnapStore((s) => s.projectName);
  const projectSyncError = useSnapStore((s) => s.projectSyncError);
  const modelHistory = useSnapStore((s) => s.modelHistory);
  const modelHistoryIndex = useSnapStore((s) => s.modelHistoryIndex);
  const targetLabel = useSnapStore((s) => s.targetLabel);
  const loadProject = useSnapStore((s) => s.loadProject);
  const setProject = useSnapStore((s) => s.setProject);
  const setAuth = useSnapStore((s) => s.setAuth);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFailure = (err: any) => {
    if (err instanceof ApiError && err.status === 401) {
      setAuth(undefined, undefined);
      setError('Your session expired. Sign in again to keep saving your work.');
    } else if (err instanceof ApiError && err.status === 404) {
      setProject(undefined, undefined);
      setError('This project is no longer available on the server.');
    } else {
      setError(err?.message || 'The project service is unavailable.');
    }
  };

  // Signed file links expire, so reload the project whenever the screen opens.
  useEffect(() => {
    if (!refresh || !authToken || !projectId) return;
    let alive = true;
    getProject(authToken, projectId)
      .then((res) => { if (alive) { loadProject(res.project); setError(null); } })
      .catch((err) => { if (alive) handleFailure(err); });
    return () => { alive = false; };
  }, [refresh, authToken, projectId]);

  const saveNow = async () => {
    if (!authToken) return;
    const jobIds = modelHistory.map((revision) => revision.jobId);
    if (!jobIds.length || jobIds.some((id) => !id)) {
      setError('This model was created before saving was available. Generate it again after signing in.');
      return;
    }
    try {
      setBusy(true);
      setError(null);
      const res = await saveGuestJobs(authToken, jobIds as string[], targetLabel || undefined);
      const position = Math.max(0, Math.min(modelHistoryIndex, jobIds.length - 1));
      if (position !== jobIds.length - 1) await setProjectCursor(authToken, res.project.id, position);
      const reopened = await getProject(authToken, res.project.id);
      loadProject({ ...reopened.project, cursor_index: position });
      setMessage('Saved to your projects.');
    } catch (err: any) {
      handleFailure(err);
    } finally {
      setBusy(false);
    }
  };

  if (!modelHistory.length) return null;

  return (
    <View style={styles.card} accessibilityLabel="Project saving status">
      {projectId ? (
        <>
          <Text style={styles.title}>Saved: {projectName || 'Untitled project'}</Text>
          <Text style={styles.text}>Edits, calibration and revision history are stored with this project.</Text>
        </>
      ) : authToken ? (
        <>
          <Text style={styles.title}>Not saved yet</Text>
          <Text style={styles.text}>This model exists only on this device. Save it to reopen and keep editing later.</Text>
          <Pressable style={styles.button} onPress={saveNow} disabled={busy}><Text style={styles.buttonText}>Save to my projects</Text></Pressable>
        </>
      ) : (
        <>
          <Text style={styles.title}>Not saved</Text>
          <Text style={styles.text}>Sign in to save this model and reopen it later.</Text>
          <Pressable style={styles.button} onPress={() => router.push('/account')}><Text style={styles.buttonText}>Sign in or create account</Text></Pressable>
        </>
      )}
      {busy ? <ActivityIndicator /> : null}
      {message ? <Text style={styles.ok}>{message}</Text> : null}
      {projectSyncError ? <Text accessibilityRole="alert" style={styles.error}>Revision position was not saved: {projectSyncError}</Text> : null}
      {error ? <Text accessibilityRole="alert" style={styles.error}>{error}</Text> : null}
      {authToken ? <Pressable onPress={() => router.push('/account')}><Text style={styles.link}>My projects</Text></Pressable> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  card: { width: '100%', maxWidth: 340, backgroundColor: '#141b34', borderRadius: 12, padding: 14, gap: 8, marginTop: 14 },
  title: { color: '#fff', fontWeight: '800', fontSize: 16, textAlign: 'center' },
  text: { color: '#c8d0e7', textAlign: 'center', fontSize: 13, lineHeight: 18 },
  button: { backgroundColor: '#18c6d1', paddingVertical: 12, borderRadius: 10, alignItems: 'center' },
  buttonText: { color: '#fff', fontWeight: '800' },
  ok: { color: '#7be0a5', textAlign: 'center' },
  error: { color: '#ff9a9a', textAlign: 'center' },
  link: { color: '#18c6d1', textAlign: 'center', fontWeight: '700' },
});
