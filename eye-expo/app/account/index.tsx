import * as React from 'react';
import { View, Text, StyleSheet, Pressable, TextInput, FlatList } from 'react-native';
import { useSnapStore } from '../../src/lib/useSnapStore';
import { signupUser, loginUser, listMyDesigns } from '../../src/lib/api';

export default function AccountScreen() {
  const setAuth = useSnapStore((s:any) => s.setAuth);
  const authToken = useSnapStore((s:any) => s.authToken);
  const currentUser = useSnapStore((s:any) => s.currentUser);
  const userProfile = useSnapStore((s:any) => s.userProfile);

  const [email, setEmail] = React.useState('');
  const [password, setPassword] = React.useState('');
  const [name, setName] = React.useState(userProfile?.name || '');
  const [myDesigns, setMyDesigns] = React.useState<any[]>([]);
  const [error, setError] = React.useState<string | null>(null);

  const loadMyDesigns = async (token: string) => {
    try {
      const res = await listMyDesigns(token);
      if (res.ok) setMyDesigns(res.designs || []);
    } catch {}
  };

  React.useEffect(() => {
    if (authToken) loadMyDesigns(authToken);
  }, [authToken]);

  const onSignup = async () => {
    setError(null);
    try {
      const res = await signupUser({ email, password, name, interests: userProfile?.interests || [], skill_level: userProfile?.skillLevel || 'beginner' });
      if (!res.ok) return setError(res.error || 'Signup failed');
      setAuth(res.token, res.user);
      loadMyDesigns(res.token);
    } catch {
      setError('Signup failed');
    }
  };

  const onLogin = async () => {
    setError(null);
    try {
      const res = await loginUser({ email, password });
      if (!res.ok) return setError(res.error || 'Login failed');
      setAuth(res.token, res.user);
      loadMyDesigns(res.token);
    } catch {
      setError('Login failed');
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Account</Text>
      <Text style={styles.subtitle}>Create an account so shared designs are linked to you.</Text>

      {currentUser ? (
        <View style={styles.panel}>
          <Text style={styles.label}>Signed in as</Text>
          <Text style={styles.value}>{currentUser.name} • {currentUser.email}</Text>
          <Text style={[styles.label, { marginTop: 12 }]}>My published designs</Text>
          <FlatList
            data={myDesigns}
            keyExtractor={(item:any) => item.id}
            renderItem={({ item }: any) => <Text style={styles.row}>• {item.title} ({item.family})</Text>}
            ListEmptyComponent={<Text style={styles.row}>No published designs yet.</Text>}
          />
        </View>
      ) : (
        <View style={styles.panel}>
          <TextInput value={name} onChangeText={setName} placeholder="Name" placeholderTextColor="#666" style={styles.input} />
          <TextInput value={email} onChangeText={setEmail} placeholder="Email" placeholderTextColor="#666" style={styles.input} autoCapitalize="none" />
          <TextInput value={password} onChangeText={setPassword} placeholder="Password" placeholderTextColor="#666" style={styles.input} secureTextEntry />
          {error ? <Text style={styles.error}>{error}</Text> : null}
          <View style={{ flexDirection:'row', gap:10 }}>
            <Pressable style={[styles.primary, { flex:1 }]} onPress={onSignup}><Text style={styles.primaryText}>Sign up</Text></Pressable>
            <Pressable style={[styles.secondary, { flex:1 }]} onPress={onLogin}><Text style={styles.secondaryText}>Log in</Text></Pressable>
          </View>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container:{ flex:1, backgroundColor:'#000', padding:16, gap:12 },
  title:{ color:'#fff', fontSize:24, fontWeight:'800' },
  subtitle:{ color:'#bdbdbd', fontSize:13, lineHeight:18 },
  panel:{ borderWidth:1, borderColor:'#1f1f1f', backgroundColor:'#0b0b0b', borderRadius:18, padding:14, gap:10 },
  input:{ borderWidth:1, borderColor:'#222', borderRadius:14, padding:12, color:'#fff' },
  label:{ color:'#8f8f8f' },
  value:{ color:'#fff', fontWeight:'700' },
  row:{ color:'#bdbdbd', marginTop:4 },
  error:{ color:'#ff7b7b' },
  primary:{ backgroundColor:'#fff', borderRadius:14, paddingVertical:12, alignItems:'center' },
  primaryText:{ color:'#000', fontWeight:'800' },
  secondary:{ borderRadius:14, paddingVertical:12, alignItems:'center', borderWidth:1, borderColor:'#2a2a2a' },
  secondaryText:{ color:'#fff', fontWeight:'800' },
});
