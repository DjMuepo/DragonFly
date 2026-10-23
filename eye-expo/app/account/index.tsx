import * as React from 'react';
import { View, Text, StyleSheet, Pressable, TextInput, FlatList, ActivityIndicator } from 'react-native';
import { useRouter } from 'expo-router';
import { useSnapStore } from '../../src/lib/useSnapStore';
import { ApiError, deleteProject, fetchMe, getProject, listProjects, logIn, logOut, renameProject, signUp } from '../../src/lib/projectsApi';
import type { ServerProject } from '../../src/lib/projectMapping';

export default function AccountScreen() {
  const router = useRouter();
  const setAuth = useSnapStore((s) => s.setAuth);
  const authToken = useSnapStore((s) => s.authToken);
  const currentUser = useSnapStore((s) => s.currentUser);
  const loadProject = useSnapStore((s) => s.loadProject);
  const setProject = useSnapStore((s) => s.setProject);
  const activeProjectId = useSnapStore((s) => s.projectId);

  const [email, setEmail] = React.useState('');
  const [password, setPassword] = React.useState('');
  const [name, setName] = React.useState('');
  const [busy, setBusy] = React.useState(false);
  const [restoring, setRestoring] = React.useState(!!authToken);
  const [error, setError] = React.useState<string | null>(null);
  const [notice, setNotice] = React.useState<string | null>(null);
  const [projects, setProjects] = React.useState<ServerProject[]>([]);
  const [projectsLoading, setProjectsLoading] = React.useState(false);
  const [renamingId, setRenamingId] = React.useState<string | null>(null);
  const [renameValue, setRenameValue] = React.useState('');
  const [confirmDeleteId, setConfirmDeleteId] = React.useState<string | null>(null);

  const expireSession = React.useCallback((message: string) => {
    setAuth(undefined, undefined);
    setProjects([]);
    setError(message);
  }, [setAuth]);

  const handleFailure = React.useCallback((err: any, fallback: string) => {
    if (err instanceof ApiError && err.status === 401) expireSession('Your session expired. Sign in again.');
    else setError(err?.message || fallback);
  }, [expireSession]);

  const loadProjects = React.useCallback(async (token: string) => {
    setProjectsLoading(true);
    try {
      const res = await listProjects(token);
      setProjects(res.projects);
      setError(null);
    } catch (err: any) {
      handleFailure(err, 'Saved projects could not be loaded.');
    } finally {
      setProjectsLoading(false);
    }
  }, [handleFailure]);

  // Session restoration: confirm the stored token is still valid before showing account data.
  React.useEffect(() => {
    if (!authToken) { setRestoring(false); return; }
    let alive = true;
    setRestoring(true);
    fetchMe(authToken)
      .then((res) => { if (alive) { setAuth(authToken, res.user); loadProjects(authToken); } })
      .catch((err) => { if (alive) handleFailure(err, 'Could not confirm your session. Check your connection and retry.'); })
      .finally(() => { if (alive) setRestoring(false); });
    return () => { alive = false; };
  }, [authToken]);

  const submit = async (mode: 'signup' | 'login') => {
    setError(null);
    setNotice(null);
    if (!email.trim() || !password) { setError('Enter your email and password.'); return; }
    try {
      setBusy(true);
      const res = mode === 'signup' ? await signUp(email.trim(), password, name.trim()) : await logIn(email.trim(), password);
      setPassword('');
      setAuth(res.token, res.user);
    } catch (err: any) {
      setError(err?.message || 'The account service is unavailable.');
    } finally {
      setBusy(false);
    }
  };

  const signOut = async () => {
    const token = authToken;
    setAuth(undefined, undefined);
    setProject(undefined, undefined);
    setProjects([]);
    if (token) {
      try { await logOut(token); } catch { setNotice('Signed out on this device. The server could not be reached to revoke the session; it will expire on its own.'); }
    }
  };

  const openProject = async (id: string) => {
    if (!authToken) return;
    setError(null);
    try {
      setBusy(true);
      const res = await getProject(authToken, id);
      loadProject(res.project);
      router.push('/snap/viewer');
    } catch (err: any) {
      handleFailure(err, 'The project could not be opened.');
    } finally {
      setBusy(false);
    }
  };

  const saveRename = async (id: string) => {
    if (!authToken || !renameValue.trim()) return;
    try {
      setBusy(true);
      const res = await renameProject(authToken, id, renameValue.trim());
      setProjects((items) => items.map((item) => (item.id === id ? { ...item, name: res.project.name } : item)));
      if (id === activeProjectId) setProject(id, res.project.name);
      setRenamingId(null);
      setNotice('Project renamed.');
    } catch (err: any) {
      handleFailure(err, 'The project could not be renamed.');
    } finally {
      setBusy(false);
    }
  };

  const removeProject = async (id: string) => {
    if (!authToken) return;
    try {
      setBusy(true);
      await deleteProject(authToken, id);
      setProjects((items) => items.filter((item) => item.id !== id));
      if (id === activeProjectId) setProject(undefined, undefined);
      setConfirmDeleteId(null);
      setNotice('Project deleted.');
    } catch (err: any) {
      handleFailure(err, 'The project could not be deleted.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Account</Text>
      <Text style={styles.subtitle}>Sign in to save models, reopen them later and keep editing.</Text>

      {restoring ? (
        <View style={styles.panel}><ActivityIndicator /><Text style={styles.row}>Restoring your session...</Text></View>
      ) : currentUser && authToken ? (
        <View style={[styles.panel, { flex: 1 }]}>
          <Text style={styles.label}>Signed in as</Text>
          <Text style={styles.value}>{currentUser.name ? `${currentUser.name} • ` : ''}{currentUser.email}</Text>
          <Text style={[styles.label, { marginTop: 12 }]}>My projects</Text>
          {projectsLoading ? <ActivityIndicator /> : null}
          <FlatList
            data={projects}
            keyExtractor={(item) => item.id}
            renderItem={({ item }) => (
              <View style={styles.project}>
                {renamingId === item.id ? (
                  <View style={{ gap: 8 }}>
                    <TextInput value={renameValue} onChangeText={setRenameValue} style={styles.input} accessibilityLabel="Project name" autoFocus />
                    <View style={styles.rowButtons}>
                      <Pressable style={styles.small} onPress={() => saveRename(item.id)} disabled={busy}><Text style={styles.smallText}>Save name</Text></Pressable>
                      <Pressable style={styles.smallDark} onPress={() => setRenamingId(null)}><Text style={styles.smallText}>Cancel</Text></Pressable>
                    </View>
                  </View>
                ) : (
                  <>
                    <Text style={styles.value}>{item.name}</Text>
                    <Text style={styles.row}>{item.revision_count} revision{item.revision_count === 1 ? '' : 's'} • updated {new Date(item.updated_at * 1000).toLocaleString()}</Text>
                    <View style={styles.rowButtons}>
                      <Pressable style={styles.small} onPress={() => openProject(item.id)} disabled={busy}><Text style={styles.smallText}>Open</Text></Pressable>
                      <Pressable style={styles.smallDark} onPress={() => { setRenamingId(item.id); setRenameValue(item.name); }} disabled={busy}><Text style={styles.smallText}>Rename</Text></Pressable>
                      {confirmDeleteId === item.id ? (
                        <>
                          <Pressable style={styles.danger} onPress={() => removeProject(item.id)} disabled={busy}><Text style={styles.smallText}>Confirm delete</Text></Pressable>
                          <Pressable style={styles.smallDark} onPress={() => setConfirmDeleteId(null)}><Text style={styles.smallText}>Keep</Text></Pressable>
                        </>
                      ) : (
                        <Pressable style={styles.smallDark} onPress={() => setConfirmDeleteId(item.id)} disabled={busy}><Text style={styles.smallText}>Delete</Text></Pressable>
                      )}
                    </View>
                  </>
                )}
              </View>
            )}
            ListEmptyComponent={projectsLoading ? undefined : <Text style={styles.row}>No saved projects yet. Scan an object while signed in, or save the current model from the 3D preview.</Text>}
          />
          {notice ? <Text style={styles.ok}>{notice}</Text> : null}
          {error ? <Text accessibilityRole="alert" style={styles.error}>{error}</Text> : null}
          <View style={styles.rowButtons}>
            <Pressable style={styles.secondary} onPress={() => loadProjects(authToken)} disabled={projectsLoading}><Text style={styles.secondaryText}>Refresh</Text></Pressable>
            <Pressable style={styles.secondary} onPress={signOut}><Text style={styles.secondaryText}>Log out</Text></Pressable>
          </View>
        </View>
      ) : (
        <View style={styles.panel}>
          <TextInput value={name} onChangeText={setName} placeholder="Name (sign up only)" placeholderTextColor="#666" style={styles.input} />
          <TextInput value={email} onChangeText={setEmail} placeholder="Email" placeholderTextColor="#666" style={styles.input} autoCapitalize="none" keyboardType="email-address" />
          <TextInput value={password} onChangeText={setPassword} placeholder="Password (10+ characters)" placeholderTextColor="#666" style={styles.input} secureTextEntry />
          {notice ? <Text style={styles.ok}>{notice}</Text> : null}
          {error ? <Text accessibilityRole="alert" style={styles.error}>{error}</Text> : null}
          {busy ? <ActivityIndicator /> : null}
          <View style={{ flexDirection: 'row', gap: 10 }}>
            <Pressable style={[styles.primary, { flex: 1 }]} onPress={() => submit('signup')} disabled={busy}><Text style={styles.primaryText}>Sign up</Text></Pressable>
            <Pressable style={[styles.secondary, { flex: 1 }]} onPress={() => submit('login')} disabled={busy}><Text style={styles.secondaryText}>Log in</Text></Pressable>
          </View>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#000', padding: 16, gap: 12 },
  title: { color: '#fff', fontSize: 24, fontWeight: '800' },
  subtitle: { color: '#bdbdbd', fontSize: 13, lineHeight: 18 },
  panel: { borderWidth: 1, borderColor: '#1f1f1f', backgroundColor: '#0b0b0b', borderRadius: 18, padding: 14, gap: 10 },
  input: { borderWidth: 1, borderColor: '#222', borderRadius: 14, padding: 12, color: '#fff' },
  label: { color: '#8f8f8f' },
  value: { color: '#fff', fontWeight: '700' },
  row: { color: '#bdbdbd', marginTop: 4 },
  project: { borderTopWidth: 1, borderTopColor: '#1f1f1f', paddingVertical: 10, gap: 6 },
  rowButtons: { flexDirection: 'row', gap: 8, flexWrap: 'wrap', marginTop: 6 },
  small: { backgroundColor: '#18c6d1', borderRadius: 10, paddingVertical: 8, paddingHorizontal: 12 },
  smallDark: { backgroundColor: '#2a2a2a', borderRadius: 10, paddingVertical: 8, paddingHorizontal: 12 },
  danger: { backgroundColor: '#a33', borderRadius: 10, paddingVertical: 8, paddingHorizontal: 12 },
  smallText: { color: '#fff', fontWeight: '700' },
  ok: { color: '#7be0a5' },
  error: { color: '#ff7b7b' },
  primary: { backgroundColor: '#fff', borderRadius: 14, paddingVertical: 12, alignItems: 'center' },
  primaryText: { color: '#000', fontWeight: '800' },
  secondary: { borderRadius: 14, paddingVertical: 12, paddingHorizontal: 16, alignItems: 'center', borderWidth: 1, borderColor: '#2a2a2a' },
  secondaryText: { color: '#fff', fontWeight: '800' },
});
