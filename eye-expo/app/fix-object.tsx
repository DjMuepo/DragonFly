import * as React from 'react';
import { View, Text, StyleSheet, Pressable, TextInput, ScrollView } from 'react-native';
import { useRouter } from 'expo-router';
import { generateFixObjectPlan } from '../src/lib/api';

const SAMPLES = [
  { label: 'bracket', confidence: 0.9 },
  { label: 'hinge', confidence: 0.86 },
  { label: 'clip', confidence: 0.84 },
  { label: 'hook', confidence: 0.88 },
];

export default function FixObjectScreen() {
  const router = useRouter();
  const [notes, setNotes] = React.useState('');
  const [result, setResult] = React.useState<any>(null);

  const runSample = async (sample: any) => {
    try {
      const res = await generateFixObjectPlan({ ...sample, user_notes: notes });
      setResult(res);
    } catch (e) {
      console.warn(e);
    }
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={{ padding: 16, gap: 12 }}>
      <Text style={styles.title}>Fix This Object</Text>
      <Text style={styles.subtitle}>Repair broken real-world parts by generating a replacement, strengthening it, and routing it to a printer.</Text>

      <View style={styles.panel}>
        <Text style={styles.meta}>Optional repair notes</Text>
        <TextInput
          style={styles.input}
          value={notes}
          onChangeText={setNotes}
          placeholder="Example: broken at the hinge corner"
          placeholderTextColor="#666"
        />
      </View>

      <View style={styles.panel}>
        <Text style={styles.sectionTitle}>Sample broken parts</Text>
        {SAMPLES.map((sample, idx) => (
          <Pressable key={idx} style={styles.secondary} onPress={() => runSample(sample)}>
            <Text style={styles.secondaryText}>Test {sample.label} ({sample.confidence})</Text>
          </Pressable>
        ))}
      </View>

      {result ? (
        <View style={styles.panel}>
          <Text style={styles.sectionTitle}>Repair Plan</Text>
          <Text style={styles.body}>{result.message}</Text>
          <Text style={styles.meta}>Replacement family: {result.replacement_family}</Text>
          <Text style={styles.meta}>Failure region: {result.failure_region}</Text>
          <Text style={styles.meta}>Recommended material: {result.recommended_material}</Text>
          <Text style={styles.meta}>Repair confidence: {result.repair_confidence}</Text>
          <Text style={styles.sectionTitle}>Quick actions</Text>
          {((result.quick_actions || []) as string[]).map((action, idx) => (
            <Text key={idx} style={styles.meta}>• {action}</Text>
          ))}
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
  body:{ color:'#fff', lineHeight:20 },
  meta:{ color:'#bdbdbd', fontSize:12, lineHeight:18 },
  secondary:{ borderRadius:14, paddingVertical:12, paddingHorizontal:12, alignItems:'center', borderWidth:1, borderColor:'#2a2a2a' },
  secondaryBottom:{ borderRadius:14, paddingVertical:14, alignItems:'center', borderWidth:1, borderColor:'#2a2a2a', marginBottom:24 },
  secondaryText:{ color:'#fff', fontWeight:'800' },
});
