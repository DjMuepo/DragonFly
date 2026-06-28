import * as React from 'react';
import { View, Text, StyleSheet, Pressable, ActivityIndicator, ScrollView } from 'react-native';
import { useRouter } from 'expo-router';
import { aggregateTraining, getTrainingFeatures } from '../../src/lib/api';

export default function TrainingInsights() {
  const router = useRouter();
  const [loading, setLoading] = React.useState(true);
  const [features, setFeatures] = React.useState<any>(null);

  const load = async () => {
    try {
      setLoading(true);
      await aggregateTraining(5000);
      const res = await getTrainingFeatures();
      setFeatures(res.features);
    } catch (e) {
      console.warn(e);
    } finally {
      setLoading(false);
    }
  };

  React.useEffect(() => { load(); }, []);

  const families = Object.entries(features?.families || {});

  return (
    <ScrollView style={styles.container} contentContainerStyle={{ padding: 16, gap: 12 }}>
      <Text style={styles.title}>Training Insights</Text>
      <Text style={styles.subtitle}>See what the learning system is discovering about each object family.</Text>

      {loading ? <ActivityIndicator /> : null}

      {features ? (
        <View style={styles.panel}>
          <Text style={styles.meta}>Events processed: {features?.global?.event_count || 0}</Text>
          <Text style={styles.meta}>Families covered: {(features?.global?.families_covered || []).join(', ') || 'none yet'}</Text>
        </View>
      ) : null}

      {families.map(([family, data]: any) => (
        <View key={family} style={styles.panel}>
          <Text style={styles.panelTitle}>{family}</Text>
          <Text style={styles.meta}>Sample weight: {data.sample_weight || 0}</Text>
          <Text style={styles.meta}>Min thickness: {data.min_thickness ?? 'n/a'}</Text>
          <Text style={styles.meta}>Preferred material: {data.preferred_material || 'PLA'}</Text>
          <Text style={styles.meta}>Reinforcement bias: {data.reinforcement_bias ?? 0}</Text>
          <Text style={styles.meta}>Fillet bias: {data.fillet_bias ?? 0}</Text>
          <Text style={styles.meta}>Top failures: {Object.keys(data.failure_signals || {}).slice(0,3).join(', ') || 'none'}</Text>
          <Text style={styles.meta}>Top successes: {Object.keys(data.success_signals || {}).slice(0,3).join(', ') || 'none'}</Text>
        </View>
      ))}

      <Pressable style={styles.primary} onPress={load}><Text style={styles.primaryText}>Refresh insights</Text></Pressable>
      <Pressable style={styles.secondary} onPress={() => router.back()}><Text style={styles.secondaryText}>Back</Text></Pressable>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container:{ flex:1, backgroundColor:'#000' },
  title:{ color:'#fff', fontSize:24, fontWeight:'800' },
  subtitle:{ color:'#bdbdbd', fontSize:13, lineHeight:18 },
  panel:{ borderWidth:1, borderColor:'#1f1f1f', backgroundColor:'#0b0b0b', borderRadius:18, padding:14, gap:6 },
  panelTitle:{ color:'#fff', fontSize:16, fontWeight:'800', textTransform:'capitalize' },
  meta:{ color:'#bdbdbd', fontSize:12, lineHeight:18 },
  primary:{ backgroundColor:'#fff', borderRadius:14, paddingVertical:14, alignItems:'center' },
  primaryText:{ color:'#000', fontWeight:'800' },
  secondary:{ borderRadius:14, paddingVertical:14, alignItems:'center', borderWidth:1, borderColor:'#2a2a2a', marginBottom: 24 },
  secondaryText:{ color:'#fff', fontWeight:'800' },
});
