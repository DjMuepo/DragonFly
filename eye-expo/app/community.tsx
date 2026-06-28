import * as React from 'react';
import { View, Text, StyleSheet, FlatList, Pressable, ActivityIndicator } from 'react-native';
import { useRouter } from 'expo-router';
import { listDesigns, likeDesign } from '../src/lib/api';

export default function Community() {
  const router = useRouter();
  const [loading, setLoading] = React.useState(true);
  const [designs, setDesigns] = React.useState<any[]>([]);

  React.useEffect(() => {
    (async () => {
      try {
        const res = await listDesigns();
        setDesigns(res.designs || []);
      } catch (e) {
        console.warn(e);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Explore Designs</Text>
      <Text style={styles.subtitle}>Browse public designs shared in the app.</Text>
      {loading ? <ActivityIndicator /> : null}
      <FlatList
        data={designs}
        keyExtractor={(item:any) => item.id}
        renderItem={({ item }: any) => (
          <Pressable style={styles.card} onPress={() => router.push(`/design/${item.slug}` as any)}>
            <Text style={styles.cardTitle}>{item.title}</Text>
            <Text style={styles.cardMeta}>{item.family} • {item.print_confidence ? `${item.print_confidence}% print confidence` : 'No score yet'}</Text>
            <Text style={styles.cardMeta}>by {item.creator}</Text>
            <View style={{ flexDirection:'row', gap:10, marginTop:6 }}>
              <Pressable style={styles.likeBtn} onPress={async () => { try { await likeDesign(item.slug); const res = await listDesigns(); setDesigns(res.designs || []); } catch {} }}><Text style={styles.likeText}>♥ {item.likes || 0}</Text></Pressable>
            </View>
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
  cardMeta:{ color:'#bdbdbd', fontSize:12, lineHeight:18 },
  secondary:{ borderRadius:14, paddingVertical:14, alignItems:'center', borderWidth:1, borderColor:'#2a2a2a' },
  secondaryText:{ color:'#fff', fontWeight:'800' },
  likeBtn:{ alignSelf:'flex-start', paddingHorizontal:10, paddingVertical:6, borderRadius:999, borderWidth:1, borderColor:'#2a2a2a' },
  likeText:{ color:'#fff', fontWeight:'700' },
});
