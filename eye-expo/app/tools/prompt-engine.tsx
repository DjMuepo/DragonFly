import * as React from 'react';
import { View, Text, StyleSheet, Pressable } from 'react-native';
import { useRouter } from 'expo-router';
import { runLiveDetection } from '../../src/lib/api';

const SAMPLES = [
  { label: 'chair', confidence: 0.92 },
  { label: 'bracket', confidence: 0.88 },
  { label: 'container', confidence: 0.83 },
  { label: 'unknown', confidence: 0.50 },
];

export default function PromptEngineTool() {
  const router = useRouter();
  const [result, setResult] = React.useState<any>(null);
  const [paid, setPaid] = React.useState(false);

  const testSample = async (sample: any) => {
    try {
      const res = await runLiveDetection({ ...sample, is_paid: paid, stable_frames: 3 });
      setResult(res.result);
    } catch (e) {
      console.warn(e);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Prompt Engine</Text>
      <Text style={styles.subtitle}>Prototype for “This looks like a chair. Scan it?” routing.</Text>

      <View style={styles.panel}>
        <Text style={styles.meta}>Paid account: {paid ? 'Yes' : 'No'}</Text>
        <Pressable style={styles.secondary} onPress={() => setPaid(!paid)}>
          <Text style={styles.secondaryText}>{paid ? 'Switch to Free' : 'Switch to Paid'}</Text>
        </Pressable>
      </View>

      <View style={styles.panel}>
        {SAMPLES.map((sample, idx) => (
          <Pressable key={idx} style={styles.secondary} onPress={() => testSample(sample)}>
            <Text style={styles.secondaryText}>Test {sample.label} ({sample.confidence})</Text>
          </Pressable>
        ))}
      </View>

      {result ? (
        <View style={styles.panel}>
          <Text style={styles.meta}>Label: {result.label}</Text>
          <Text style={styles.meta}>Workflow: {result.workflow || 'none'}</Text>
          <Text style={styles.meta}>Prompt: {result.should_show_prompt ? 'Yes' : 'No'}</Text>
          <Text style={styles.message}>{result.message}</Text>
        </View>
      ) : null}

      <Pressable style={styles.secondaryBottom} onPress={() => router.back()}>
        <Text style={styles.secondaryText}>Back</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  container:{ flex:1, backgroundColor:'#000', padding:16, gap:12 },
  title:{ color:'#fff', fontSize:24, fontWeight:'800' },
  subtitle:{ color:'#bdbdbd', fontSize:13, lineHeight:18 },
  panel:{ borderWidth:1, borderColor:'#1f1f1f', backgroundColor:'#0b0b0b', borderRadius:18, padding:14, gap:10 },
  meta:{ color:'#bdbdbd', fontSize:12, lineHeight:18 },
  message:{ color:'#fff', fontSize:14, lineHeight:20 },
  secondary:{ borderRadius:14, paddingVertical:12, paddingHorizontal:12, alignItems:'center', borderWidth:1, borderColor:'#2a2a2a' },
  secondaryBottom:{ borderRadius:14, paddingVertical:14, alignItems:'center', borderWidth:1, borderColor:'#2a2a2a', marginBottom:24 },
  secondaryText:{ color:'#fff', fontWeight:'800' },
});
