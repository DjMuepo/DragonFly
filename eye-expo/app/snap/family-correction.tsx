import { View, Text, StyleSheet, Pressable } from 'react-native';
import { useRouter } from 'expo-router';
import { useSnapStore } from '../../src/lib/useSnapStore';
import { logEvent } from '../../src/lib/api';

const FAMILIES = ['bracket','hook','clip','handle','enclosure','adapter'];

export default function FamilyCorrection() {
  const router = useRouter();
  const visionClassify = useSnapStore((s:any) => s.visionClassify);
  const setVisionClassify = useSnapStore((s:any) => s.setVisionClassify);
  const setCorrectedFamily = useSnapStore((s:any) => s.setCorrectedFamily);
  const sessionId = useSnapStore((s:any) => s.sessionId);
  const current = (visionClassify?.object_family || 'object').toLowerCase();

  const choose = (family: string) => {
    setVisionClassify({ ...(visionClassify || {}), object_family: family, confidence: family === current ? visionClassify?.confidence : 0.99, corrected: true });
    setCorrectedFamily(family);
    logEvent({ event: 'family_correction', session_id: sessionId, payload: { predicted: current, corrected: family } });
    router.back();
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Wrong object family?</Text>
      <Text style={styles.subtitle}>Pick the closest one. This helps train the model.</Text>
      <View style={styles.panel}>
        {FAMILIES.map((f) => (
          <Pressable key={f} style={styles.card} onPress={() => choose(f)}>
            <Text style={styles.cardText}>{f}</Text>
          </Pressable>
        ))}
      </View>
      <View style={styles.actions}>
        <Pressable style={styles.secondary} onPress={() => router.back()}><Text style={styles.secondaryText}>Back</Text></Pressable>
      </View>
    </View>
  );
}
const styles = StyleSheet.create({
  container:{ flex:1, backgroundColor:'#000', padding:16, gap:12 },
  title:{ color:'#fff', fontSize:24, fontWeight:'800' },
  subtitle:{ color:'#bdbdbd', fontSize:13, lineHeight:18 },
  panel:{ borderWidth:1, borderColor:'#1f1f1f', backgroundColor:'#0b0b0b', borderRadius:18, padding:14, gap:10 },
  card:{ borderWidth:1, borderColor:'#1f1f1f', backgroundColor:'#060606', borderRadius:14, padding:14 },
  cardText:{ color:'#fff', fontWeight:'800', textTransform:'capitalize' },
  actions:{ marginTop:'auto', gap:10, paddingBottom:8 },
  secondary:{ borderRadius:14, paddingVertical:14, alignItems:'center', borderWidth:1, borderColor:'#2a2a2a' },
  secondaryText:{ color:'#fff', fontWeight:'800' },
});
