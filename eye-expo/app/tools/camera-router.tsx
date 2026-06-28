import * as React from 'react';
import { View, Text, StyleSheet, Pressable, TextInput, ScrollView } from 'react-native';
import { useRouter } from 'expo-router';
import { routeCameraAction } from '../../src/lib/api';

const SAMPLES = [
  { label: 'chair', confidence: 0.92 },
  { label: 'bracket', confidence: 0.88 },
  { label: 'container', confidence: 0.83 },
  { label: 'clip', confidence: 0.84 },
  { label: 'unknown', confidence: 0.50 },
];

export default function CameraRouterTool() {
  const router = useRouter();
  const [paid, setPaid] = React.useState(false);
  const [notes, setNotes] = React.useState('');
  const [result, setResult] = React.useState<any>(null);

  const runSample = async (sample: any) => {
    try {
      const res = await routeCameraAction({ ...sample, is_paid: paid, stable_frames: 3, user_notes: notes });
      setResult(res);
    } catch (e) {
      console.warn(e);
    }
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={{ padding:16, gap:12 }}>
      <Text style={styles.title}>Camera Router</Text>
      <Text style={styles.subtitle}>Prototype for routing live detections directly into Scan the World, Fix This Object, or Instant Builder.</Text>

      <View style={styles.panel}>
        <Text style={styles.meta}>Paid account: {paid ? 'Yes' : 'No'}</Text>
        <Pressable style={styles.secondary} onPress={() => setPaid(!paid)}>
          <Text style={styles.secondaryText}>{paid ? 'Switch to Free' : 'Switch to Paid'}</Text>
        </Pressable>
        <TextInput
          style={styles.input}
          value={notes}
          onChangeText={setNotes}
          placeholder="Optional repair notes"
          placeholderTextColor="#666"
        />
      </View>

      <View style={styles.panel}>
        {SAMPLES.map((sample, idx) => (
          <Pressable key={idx} style={styles.secondary} onPress={() => runSample(sample)}>
            <Text style={styles.secondaryText}>Route {sample.label} ({sample.confidence})</Text>
          </Pressable>
        ))}
      </View>

      {result ? (
        <View style={styles.panel}>
          <Text style={styles.meta}>Route: {result.route}</Text>
          <Text style={styles.meta}>Detection label: {result?.detection?.label}</Text>
          <Text style={styles.meta}>Workflow: {result?.detection?.workflow || 'none'}</Text>
          <Text style={styles.message}>{result?.detection?.message || result?.message}</Text>

          {result.fix_plan?.ok ? (
            <>
              <Text style={styles.sectionTitle}>Fix Plan</Text>
              <Text style={styles.meta}>Replacement family: {result.fix_plan.replacement_family}</Text>
              <Text style={styles.meta}>Failure region: {result.fix_plan.failure_region}</Text>
              <Text style={styles.meta}>Material: {result.fix_plan.recommended_material}</Text>
            </>
          ) : null}

          {result.scan_plan ? (
            <>
              <Text style={styles.sectionTitle}>Scan Plan</Text>
              <Text style={styles.meta}>Premium required: {result.scan_plan.premium_required ? 'Yes' : 'No'}</Text>
              <Text style={styles.meta}>Actions: {(result.scan_plan.suggested_actions || []).join(', ')}</Text>
            </>
          ) : null}

          {result.builder_plan ? (
            <>
              <Text style={styles.sectionTitle}>Builder Plan</Text>
              <Text style={styles.meta}>Template family: {result.builder_plan.template_family}</Text>
              <Text style={styles.meta}>Actions: {(result.builder_plan.suggested_actions || []).join(', ')}</Text>
            </>
          ) : null}
        </View>
      ) : null}

      <Pressable style={styles.secondaryBottom} onPress={() => router.back()}>
        <Text style={styles.secondaryText}>Back</Text>
      </Pressable>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container:{ flex:1, backgroundColor:'#000' },
  title:{ color:'#fff', fontSize:24, fontWeight:'800' },
  subtitle:{ color:'#bdbdbd', fontSize:13, lineHeight:18 },
  panel:{ borderWidth:1, borderColor:'#1f1f1f', backgroundColor:'#0b0b0b', borderRadius:18, padding:14, gap:10 },
  input:{ borderWidth:1, borderColor:'#222', borderRadius:12, padding:12, color:'#fff' },
  sectionTitle:{ color:'#fff', fontSize:16, fontWeight:'800' },
  meta:{ color:'#bdbdbd', fontSize:12, lineHeight:18 },
  message:{ color:'#fff', fontSize:14, lineHeight:20 },
  secondary:{ borderRadius:14, paddingVertical:12, paddingHorizontal:12, alignItems:'center', borderWidth:1, borderColor:'#2a2a2a' },
  secondaryBottom:{ borderRadius:14, paddingVertical:14, alignItems:'center', borderWidth:1, borderColor:'#2a2a2a', marginBottom:24 },
  secondaryText:{ color:'#fff', fontWeight:'800' },
});
