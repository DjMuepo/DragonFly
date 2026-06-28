import * as React from 'react';
import { View, Text, StyleSheet, FlatList, Pressable, ActivityIndicator } from 'react-native';
import { useRouter } from 'expo-router';
import { listChallenges } from '../src/lib/api';

export default function ChallengesScreen() {
  const router = useRouter();
  const [loading, setLoading] = React.useState(true);
  const [items, setItems] = React.useState<any[]>([]);

  React.useEffect(() => {
    (async () => {
      try {
        const res = await listChallenges();
        setItems(res.challenges || []);
      } catch (e) { console.warn(e); }
      finally { setLoading(false); }
    })();
  }, []);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Design Challenges</Text>
      <Text style={styles.subtitle}>Compete, improve designs, and help train the AI with real-world object variations.</Text>
      {loading ? <ActivityIndicator /> : null}
      <FlatList
        data={items}
        keyExtractor={(item:any) => item.id}
        renderItem={({ item }: any) => (
          <Pressable style={styles.card} onPress={() => router.push(`/challenge/${item.id}` as any)}>
            <Text style={styles.cardTitle}>{item.title}</Text>
            <Text style={styles.meta}>{item.type} • {item.difficulty} • {item.prize}</Text>
            <Text style={styles.meta}>{item.description}</Text>
          </Pressable>
        )}
        contentContainerStyle={{ gap: 10, paddingBottom: 20 }}
      />
      <Pressable style={styles.secondary} onPress={() => router.back()}><Text style={styles.secondaryText}>Back</Text></Pressable>
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
  secondary:{ borderRadius:14, paddingVertical:14, alignItems:'center', borderWidth:1, borderColor:'#2a2a2a', marginBottom:24 },
  secondaryText:{ color:'#fff', fontWeight:'800' },
});
