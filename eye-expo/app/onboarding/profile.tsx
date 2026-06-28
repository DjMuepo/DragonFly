import { View, Text, StyleSheet, Pressable, TextInput } from 'react-native';
import { useState } from 'react';
import { useRouter } from 'expo-router';
import { useSnapStore } from '../../src/lib/useSnapStore';
import { logEvent } from '../../src/lib/api';

const INTERESTS = ['Fashion', 'Art', 'Engineering', 'DIY Repair', 'Medical', 'Home Decor', 'Automotive', 'Education'];

export default function ProfileOnboarding() {
  const router = useRouter();
  const profile = useSnapStore((s:any) => s.userProfile);
  const setUserProfile = useSnapStore((s:any) => s.setUserProfile);
  const sessionId = useSnapStore((s:any) => s.sessionId);
  const [name, setName] = useState(profile?.name || '');
  const [interests, setInterests] = useState<string[]>(profile?.interests || []);
  const [skillLevel, setSkillLevel] = useState<'beginner'|'intermediate'|'advanced'>(profile?.skillLevel || 'beginner');
  const toggle = (item: string) => setInterests((curr) => curr.includes(item) ? curr.filter((x) => x !== item) : [...curr, item]);
  const save = () => {
    setUserProfile({ name, interests, skillLevel });
    logEvent({ event: 'profile_onboarding_save', session_id: sessionId, payload: { name_present: !!name, interests, skillLevel } });
    router.back();
  };
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Set up your profile</Text>
      <Text style={styles.subtitle}>This helps tailor suggestions and improves future AI recommendations.</Text>
      <View style={styles.panel}>
        <Text style={styles.label}>Name (optional)</Text>
        <TextInput value={name} onChangeText={setName} placeholder="Your name" placeholderTextColor="#666" style={styles.input} />
        <Text style={[styles.label, { marginTop: 12 }]}>What are your interests?</Text>
        <View style={styles.wrap}>
          {INTERESTS.map((it) => (
            <Pressable key={it} onPress={() => toggle(it)} style={[styles.chip, interests.includes(it) ? styles.chipOn : styles.chipOff]}>
              <Text style={{ color: interests.includes(it) ? '#fff' : '#bdbdbd', fontWeight: '700' }}>{it}</Text>
            </Pressable>
          ))}
        </View>
        <Text style={[styles.label, { marginTop: 12 }]}>Experience</Text>
        <View style={styles.row}>
          {(['beginner','intermediate','advanced'] as const).map((lvl) => (
            <Pressable key={lvl} onPress={() => setSkillLevel(lvl)} style={[styles.chip, skillLevel === lvl ? styles.chipOn : styles.chipOff]}>
              <Text style={{ color: skillLevel === lvl ? '#fff' : '#bdbdbd', fontWeight: '700', textTransform: 'capitalize' }}>{lvl}</Text>
            </Pressable>
          ))}
        </View>
      </View>
      <View style={styles.actions}>
        <Pressable style={styles.primary} onPress={save}><Text style={styles.primaryText}>Save profile</Text></Pressable>
        <Pressable style={styles.secondary} onPress={() => router.back()}><Text style={styles.secondaryText}>Back</Text></Pressable>
      </View>
    </View>
  );
}
const styles = StyleSheet.create({
  container:{ flex:1, backgroundColor:'#000', padding:16, gap:12 },
  title:{ color:'#fff', fontSize:24, fontWeight:'800' },
  subtitle:{ color:'#bdbdbd', fontSize:13, lineHeight:18 },
  panel:{ borderWidth:1, borderColor:'#1f1f1f', backgroundColor:'#0b0b0b', borderRadius:18, padding:14 },
  label:{ color:'#bdbdbd', marginBottom:8 },
  input:{ borderWidth:1, borderColor:'#222', borderRadius:14, padding:12, color:'#fff' },
  wrap:{ flexDirection:'row', flexWrap:'wrap', gap:8 },
  row:{ flexDirection:'row', gap:8, flexWrap:'wrap' },
  chip:{ paddingHorizontal:12, paddingVertical:10, borderRadius:999, borderWidth:1 },
  chipOn:{ borderColor:'#fff', backgroundColor:'#111' },
  chipOff:{ borderColor:'#222', backgroundColor:'#060606' },
  actions:{ marginTop:'auto', gap:10, paddingBottom:8 },
  primary:{ backgroundColor:'#fff', borderRadius:14, paddingVertical:14, alignItems:'center' },
  primaryText:{ color:'#000', fontWeight:'800', fontSize:16 },
  secondary:{ borderRadius:14, paddingVertical:14, alignItems:'center', borderWidth:1, borderColor:'#2a2a2a' },
  secondaryText:{ color:'#fff', fontWeight:'800' },
});
