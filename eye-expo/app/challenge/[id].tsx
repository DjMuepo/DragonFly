import * as React from 'react';
import { View, Text, StyleSheet, Pressable, FlatList, ActivityIndicator, ScrollView } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { getChallenge, submitChallengeEntry } from '../../src/lib/api';
import { useSnapStore } from '../../src/lib/useSnapStore';

export default function ChallengeDetail() {
  const router = useRouter();
  const { id } = useLocalSearchParams<{ id: string }>();
  const userProfile = useSnapStore((s:any) => s.userProfile);
  const currentUser = useSnapStore((s:any) => s.currentUser);
  const visionReconstruct = useSnapStore((s:any) => s.visionReconstruct);
  const [loading, setLoading] = React.useState(true);
  const [item, setItem] = React.useState<any>(null);

  const load = async () => {
    try {
      const res = await getChallenge(String(id));
      if (res.ok) setItem(res);
    } catch (e) { console.warn(e); }
    finally { setLoading(false); }
  };
  React.useEffect(() => { load(); }, [id]);

  return (
    <ScrollView style={styles.container} contentContainerStyle={{ padding:16, gap:12 }}>
      {loading ? <ActivityIndicator /> : null}
      {item?.challenge ? <>
        <Text style={styles.title}>{item.challenge.title}</Text>
        <Text style={styles.subtitle}>{item.challenge.type} • {item.challenge.difficulty} • {item.challenge.prize}</Text>
        <View style={styles.panel}>
          <Text style={styles.body}>{item.challenge.description}</Text>
          <Text style={styles.meta}>Seed family: {item.challenge.seed_family}</Text>
        </View>
        <Pressable style={styles.primary} onPress={async () => {
          try {
            await submitChallengeEntry(String(id), {
              creator: currentUser?.name || userProfile?.name || 'Anonymous',
              design_title: (visionReconstruct?.family || item.challenge.seed_family || 'Design') + ' Submission',
              object_dna: { geometry: { family: visionReconstruct?.family || item.challenge.seed_family }, ai_generation: { source: 'challenge_submit' }, user_edits: [], outcomes: {} },
              score: 10,
            });
            await load();
          } catch (e) { console.warn(e); }
        }}>
          <Text style={styles.primaryText}>Submit current design</Text>
        </Pressable>
        <View style={styles.panel}>
          <Text style={styles.sectionTitle}>Leaderboard</Text>
          <FlatList
            data={item.leaderboard || []}
            keyExtractor={(entry:any) => entry.id}
            renderItem={({ item: entry }: any) => <Text style={styles.meta}>• {entry.creator} — {entry.design_title} — score {entry.score}</Text>}
          />
        </View>
      </> : null}
      <Pressable style={styles.secondary} onPress={() => router.back()}><Text style={styles.secondaryText}>Back</Text></Pressable>
    </ScrollView>
  );
}
const styles = StyleSheet.create({
  container:{ flex:1, backgroundColor:'#000' },
  title:{ color:'#fff', fontSize:24, fontWeight:'800' },
  subtitle:{ color:'#bdbdbd', fontSize:13, lineHeight:18 },
  panel:{ borderWidth:1, borderColor:'#1f1f1f', backgroundColor:'#0b0b0b', borderRadius:18, padding:14, gap:8 },
  body:{ color:'#fff', lineHeight:20 },
  meta:{ color:'#bdbdbd', fontSize:12, lineHeight:18 },
  sectionTitle:{ color:'#fff', fontWeight:'800', fontSize:16 },
  primary:{ backgroundColor:'#fff', borderRadius:14, paddingVertical:14, alignItems:'center' },
  primaryText:{ color:'#000', fontWeight:'800' },
  secondary:{ borderRadius:14, paddingVertical:14, alignItems:'center', borderWidth:1, borderColor:'#2a2a2a', marginBottom:24 },
  secondaryText:{ color:'#fff', fontWeight:'800' },
});
