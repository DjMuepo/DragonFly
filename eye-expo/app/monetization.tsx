import * as React from 'react';
import { View, Text, StyleSheet, Pressable, ScrollView, TextInput } from 'react-native';
import {
  createBehaviorSession,
  runGhostSave,
  getExitWarning,
  recoverBehaviorSession,
  recordPrintSuccess
} from '../src/lib/api';

function GoldOrb({ label }: { label: string }) {
  return (
    <View style={styles.orbWrap}>
      <View style={styles.orb} />
      <Text style={styles.orbText}>{label}</Text>
    </View>
  );
}

export default function MonetizationScreen() {
  const [sessionId, setSessionId] = React.useState<string>('');
  const [title, setTitle] = React.useState('Hook Prototype');
  const [result, setResult] = React.useState<any>(null);

  const startSession = async () => {
    try {
      const res = await createBehaviorSession({
        title,
        design: { family: 'hook', size: 'medium' },
        ttl_seconds: 3600,
      });
      setSessionId(res.session_id);
      setResult(res);
    } catch (e) { console.warn(e); }
  };

  const ghostSave = async () => {
    if (!sessionId) return;
    try { setResult(await runGhostSave({ session_id: sessionId })); } catch (e) { console.warn(e); }
  };

  const exitWarn = async () => {
    if (!sessionId) return;
    try { setResult(await getExitWarning({ session_id: sessionId })); } catch (e) { console.warn(e); }
  };

  const recover = async () => {
    if (!sessionId) return;
    try { setResult(await recoverBehaviorSession({ session_id: sessionId })); } catch (e) { console.warn(e); }
  };

  const printSuccess = async () => {
    try { setResult(await recordPrintSuccess({ title, printer_id: 'prt_demo_1', rating: 5 })); } catch (e) { console.warn(e); }
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={{ padding:16, gap:12 }}>
      <Text style={styles.title}>v64 Behavior Engine</Text>
      <Text style={styles.subtitle}>Ghost save, session loss warning, one-time recovery, gold-orb premium cues, and first print success prompt.</Text>

      <View style={styles.panel}>
        <Text style={styles.meta}>Design title</Text>
        <TextInput style={styles.input} value={title} onChangeText={setTitle} placeholder="Hook Prototype" placeholderTextColor="#666" />
        <Pressable style={styles.primary} onPress={startSession}>
          <Text style={styles.primaryText}>Start Free Session</Text>
        </Pressable>
        {sessionId ? <Text style={styles.meta}>Session: {sessionId}</Text> : null}
      </View>

      <View style={styles.panel}>
        <GoldOrb label="Save Permanently (Pro)" />
        <GoldOrb label="Export Production STL" />
        <GoldOrb label="Publish To World Map" />
      </View>

      <View style={styles.panel}>
        <Pressable style={styles.secondary} onPress={ghostSave}><Text style={styles.secondaryText}>Ghost Save</Text></Pressable>
        <Pressable style={styles.secondary} onPress={exitWarn}><Text style={styles.secondaryText}>Exit Warning</Text></Pressable>
        <Pressable style={styles.secondary} onPress={recover}><Text style={styles.secondaryText}>One-Time Recovery</Text></Pressable>
        <Pressable style={styles.secondary} onPress={printSuccess}><Text style={styles.secondaryText}>First Print Success</Text></Pressable>
      </View>

      {result ? (
        <View style={styles.panel}>
          <Text style={styles.sectionTitle}>Result</Text>
          {Object.entries(result).map(([k,v], idx) => (
            <Text key={idx} style={styles.meta}>{k}: {typeof v === 'object' ? JSON.stringify(v) : String(v)}</Text>
          ))}
        </View>
      ) : null}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container:{ flex:1, backgroundColor:'#000' },
  title:{ color:'#fff', fontSize:24, fontWeight:'800' },
  subtitle:{ color:'#bdbdbd', fontSize:13, lineHeight:18 },
  panel:{ borderWidth:1, borderColor:'#1f1f1f', backgroundColor:'#0b0b0b', borderRadius:18, padding:14, gap:10 },
  meta:{ color:'#bdbdbd', fontSize:12, lineHeight:18 },
  sectionTitle:{ color:'#fff', fontSize:16, fontWeight:'800' },
  input:{ borderWidth:1, borderColor:'#222', borderRadius:12, padding:12, color:'#fff' },
  primary:{ backgroundColor:'#fff', borderRadius:14, paddingVertical:14, alignItems:'center' },
  primaryText:{ color:'#000', fontWeight:'800' },
  secondary:{ borderRadius:14, paddingVertical:12, paddingHorizontal:12, alignItems:'center', borderWidth:1, borderColor:'#2a2a2a' },
  secondaryText:{ color:'#fff', fontWeight:'800' },
  orbWrap:{ flexDirection:'row', alignItems:'center', gap:10 },
  orb:{ width:12, height:12, borderRadius:99, backgroundColor:'#d4af37' },
  orbText:{ color:'#fff', fontWeight:'700' },
});
