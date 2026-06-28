import * as React from 'react';
import { View, Text, StyleSheet, Pressable } from 'react-native';
import { useRouter } from 'expo-router';
import { runJobsOnce, getPostgresHealth } from '../../src/lib/api';

export default function WorkerTool() {
  const router = useRouter();
  const [workerResult, setWorkerResult] = React.useState<any>(null);
  const [dbHealth, setDbHealth] = React.useState<any>(null);

  const checkDb = async () => {
    try { setDbHealth(await getPostgresHealth()); } catch (e) { console.warn(e); }
  };

  const runWorker = async () => {
    try { setWorkerResult(await runJobsOnce(25)); } catch (e) { console.warn(e); }
  };

  React.useEffect(() => { checkDb(); }, []);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Worker + Cloud DB</Text>
      <Text style={styles.subtitle}>Foundation tools for running queued jobs and checking Postgres config.</Text>

      <View style={styles.panel}>
        <Text style={styles.meta}>Postgres configured: {dbHealth?.configured ? 'Yes' : 'No'}</Text>
        <Text style={styles.meta}>Mode: {dbHealth?.mode || 'postgres'}</Text>
      </View>

      <Pressable style={styles.primary} onPress={checkDb}>
        <Text style={styles.primaryText}>Refresh DB Health</Text>
      </Pressable>

      <Pressable style={styles.primary} onPress={runWorker}>
        <Text style={styles.primaryText}>Run Worker Once</Text>
      </Pressable>

      {workerResult ? (
        <View style={styles.panel}>
          <Text style={styles.meta}>Processed jobs: {workerResult.processed ?? 0}</Text>
        </View>
      ) : null}

      <Pressable style={styles.secondary} onPress={() => router.back()}>
        <Text style={styles.secondaryText}>Back</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  container:{ flex:1, backgroundColor:'#000', padding:16, gap:12 },
  title:{ color:'#fff', fontSize:24, fontWeight:'800' },
  subtitle:{ color:'#bdbdbd', fontSize:13, lineHeight:18 },
  panel:{ borderWidth:1, borderColor:'#1f1f1f', backgroundColor:'#0b0b0b', borderRadius:18, padding:14, gap:6 },
  meta:{ color:'#bdbdbd', fontSize:12, lineHeight:18 },
  primary:{ backgroundColor:'#fff', borderRadius:14, paddingVertical:14, alignItems:'center' },
  primaryText:{ color:'#000', fontWeight:'800' },
  secondary:{ borderRadius:14, paddingVertical:14, alignItems:'center', borderWidth:1, borderColor:'#2a2a2a', marginBottom:24 },
  secondaryText:{ color:'#fff', fontWeight:'800' },
});
