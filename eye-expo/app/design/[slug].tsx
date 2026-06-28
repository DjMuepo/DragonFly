import * as React from 'react';
import { View, Text, StyleSheet, Pressable, ActivityIndicator } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import * as Linking from 'expo-linking';
import { getDesign, likeDesign } from '../../src/lib/api';

export default function DesignDetail() {
  const router = useRouter();
  const { slug } = useLocalSearchParams<{ slug: string }>();
  const [loading, setLoading] = React.useState(true);
  const [design, setDesign] = React.useState<any>(null);

  React.useEffect(() => {
    (async () => {
      try {
        if (!slug) return;
        const res = await getDesign(String(slug));
        if (res.ok) setDesign(res.design);
      } catch (e) {
        console.warn(e);
      } finally {
        setLoading(false);
      }
    })();
  }, [slug]);

  return (
    <View style={styles.container}>
      {loading ? <ActivityIndicator /> : null}
      {design ? (
        <>
          <Text style={styles.title}>{design.title}</Text>
          <Text style={styles.subtitle}>{design.family} • by {design.creator}</Text>
          <View style={styles.panel}>
            <Text style={styles.body}>{design.description || 'No description yet.'}</Text>
            <Text style={styles.meta}>Print confidence: {design.print_confidence ? `${design.print_confidence}%` : 'N/A'}</Text>
            <Text style={styles.meta}>Tags: {(design.tags || []).join(', ') || 'none'}</Text>
          </View>
          <Pressable style={[styles.secondary, { marginTop: 4 }]} onPress={async () => { try { const r = await likeDesign(String(slug)); if (r.ok) setDesign(r.design); } catch {} }}><Text style={styles.secondaryText}>♥ Like ({design.likes || 0})</Text></Pressable>
          <Pressable style={styles.primary} onPress={() => Linking.openURL('https://example.com')}>
            <Text style={styles.primaryText}>Open landing page</Text>
          </Pressable>
        </>
      ) : (
        <Text style={styles.subtitle}>Design not found.</Text>
      )}
      <Pressable style={styles.secondary} onPress={() => router.back()}><Text style={styles.secondaryText}>Back</Text></Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  container:{ flex:1, backgroundColor:'#000', padding:16, gap:12 },
  title:{ color:'#fff', fontSize:24, fontWeight:'800' },
  subtitle:{ color:'#bdbdbd', fontSize:13, lineHeight:18 },
  panel:{ borderWidth:1, borderColor:'#1f1f1f', backgroundColor:'#0b0b0b', borderRadius:18, padding:14, gap:8 },
  body:{ color:'#fff', lineHeight:20 },
  meta:{ color:'#bdbdbd', fontSize:12 },
  primary:{ backgroundColor:'#fff', borderRadius:14, paddingVertical:14, alignItems:'center' },
  primaryText:{ color:'#000', fontWeight:'800' },
  secondary:{ borderRadius:14, paddingVertical:14, alignItems:'center', borderWidth:1, borderColor:'#2a2a2a' },
  secondaryText:{ color:'#fff', fontWeight:'800' },
});
