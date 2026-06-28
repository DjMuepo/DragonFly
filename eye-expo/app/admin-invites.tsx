import * as React from 'react';
import { View, Text, StyleSheet, Pressable, ScrollView, TextInput } from 'react-native';
import { createInviteCode, listInvites, disableInviteCode } from '../src/lib/api';

export default function AdminInvitesScreen() {
  const [data, setData] = React.useState<any>(null);
  const [email, setEmail] = React.useState('');

  const load = async () => {
    try { setData(await listInvites()); } catch (e) { console.warn(e); }
  };

  React.useEffect(() => { load(); }, []);

  const createCode = async () => {
    try {
      await createInviteCode({ assigned_email: email || undefined, usage_limit: 1, created_by: 'owner_admin' });
      setEmail('');
      await load();
    } catch (e) { console.warn(e); }
  };

  const disable = async (code: string) => {
    try { await disableInviteCode({ code }); await load(); } catch (e) { console.warn(e); }
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={{ padding:16, gap:12 }}>
      <Text style={styles.title}>Admin Invites</Text>
      <View style={styles.panel}>
        <TextInput style={styles.input} value={email} onChangeText={setEmail} placeholder="Assigned email (optional)" placeholderTextColor="#666" />
        <Pressable style={styles.primary} onPress={createCode}><Text style={styles.primaryText}>Create Invite</Text></Pressable>
      </View>
      {Object.entries((data?.data?.codes || {})).map(([code, invite]: any) => (
        <View key={code} style={styles.card}>
          <Text style={styles.cardTitle}>{code}</Text>
          <Text style={styles.meta}>Enabled: {invite.enabled ? 'Yes' : 'No'}</Text>
          <Text style={styles.meta}>Uses: {invite.uses}/{invite.usage_limit}</Text>
          <Text style={styles.meta}>Assigned: {invite.assigned_email || 'n/a'}</Text>
          <Pressable style={styles.secondary} onPress={() => disable(code)}>
            <Text style={styles.secondaryText}>Disable</Text>
          </Pressable>
        </View>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container:{ flex:1, backgroundColor:'#000' },
  title:{ color:'#fff', fontSize:24, fontWeight:'800' },
  panel:{ borderWidth:1, borderColor:'#1f1f1f', backgroundColor:'#0b0b0b', borderRadius:18, padding:14, gap:10 },
  card:{ borderWidth:1, borderColor:'#1f1f1f', backgroundColor:'#0b0b0b', borderRadius:18, padding:14, gap:8 },
  cardTitle:{ color:'#fff', fontSize:16, fontWeight:'800' },
  meta:{ color:'#bdbdbd', fontSize:12, lineHeight:18 },
  input:{ borderWidth:1, borderColor:'#222', borderRadius:12, padding:12, color:'#fff' },
  primary:{ backgroundColor:'#fff', borderRadius:14, paddingVertical:14, alignItems:'center' },
  primaryText:{ color:'#000', fontWeight:'800' },
  secondary:{ borderWidth:1, borderColor:'#2a2a2a', borderRadius:14, paddingVertical:10, alignItems:'center' },
  secondaryText:{ color:'#fff', fontWeight:'800' },
});
