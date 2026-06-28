import * as React from 'react';
import { View, Text, StyleSheet, Pressable, FlatList } from 'react-native';
import { useRouter } from 'expo-router';
import { enqueueBackgroundJob, listBackgroundJobs, updateBackgroundJob } from '../../src/lib/api';

export default function JobQueueTool() {
  const router = useRouter();
  const [jobs, setJobs] = React.useState<any[]>([]);

  const load = async () => {
    try {
      const res = await listBackgroundJobs(100);
      setJobs(res.jobs || []);
    } catch (e) {
      console.warn(e);
    }
  };

  React.useEffect(() => { load(); }, []);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Background Jobs</Text>
      <Text style={styles.subtitle}>Foundation queue for previews, exports, and future training tasks.</Text>

      <Pressable style={styles.primary} onPress={async () => { await enqueueBackgroundJob('preview_render', { source: 'tool' }); await load(); }}>
        <Text style={styles.primaryText}>Enqueue Preview Job</Text>
      </Pressable>

      <FlatList
        data={jobs}
        keyExtractor={(item:any) => item.id}
        renderItem={({ item }: any) => (
          <View style={styles.card}>
            <Text style={styles.cardTitle}>{item.kind}</Text>
            <Text style={styles.meta}>Status: {item.status}</Text>
            <Text style={styles.meta}>Job ID: {item.id}</Text>
            <View style={{ flexDirection:'row', gap:10, marginTop:8 }}>
              <Pressable style={styles.secondary} onPress={async () => { await updateBackgroundJob(item.id, { status: 'running' }); await load(); }}>
                <Text style={styles.secondaryText}>Mark Running</Text>
              </Pressable>
              <Pressable style={styles.secondary} onPress={async () => { await updateBackgroundJob(item.id, { status: 'done', result: { ok: true } }); await load(); }}>
                <Text style={styles.secondaryText}>Mark Done</Text>
              </Pressable>
            </View>
          </View>
        )}
        contentContainerStyle={{ gap: 10, paddingBottom: 20 }}
      />

      <Pressable style={styles.secondaryBottom} onPress={() => router.back()}><Text style={styles.secondaryText}>Back</Text></Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  container:{ flex:1, backgroundColor:'#000', padding:16, gap:12 },
  title:{ color:'#fff', fontSize:24, fontWeight:'800' },
  subtitle:{ color:'#bdbdbd', fontSize:13, lineHeight:18 },
  card:{ borderWidth:1, borderColor:'#1f1f1f', backgroundColor:'#0b0b0b', borderRadius:18, padding:14, gap:6 },
  cardTitle:{ color:'#fff', fontWeight:'800', fontSize:16 },
  meta:{ color:'#bdbdbd', fontSize:12, lineHeight:18 },
  secondary:{ borderRadius:14, paddingVertical:10, paddingHorizontal:12, alignItems:'center', borderWidth:1, borderColor:'#2a2a2a' },
  primary:{ backgroundColor:'#fff', borderRadius:14, paddingVertical:14, alignItems:'center' },
  primaryText:{ color:'#000', fontWeight:'800' },
  secondaryBottom:{ borderRadius:14, paddingVertical:14, alignItems:'center', borderWidth:1, borderColor:'#2a2a2a', marginBottom:24 },
  secondaryText:{ color:'#fff', fontWeight:'800' },
});
