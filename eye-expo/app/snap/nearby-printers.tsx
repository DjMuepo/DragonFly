import * as React from 'react';
import { View, Text, StyleSheet, Pressable, ActivityIndicator, FlatList } from 'react-native';
import * as Location from 'expo-location';
import { useRouter } from 'expo-router';
import { useSnapStore } from '../../src/lib/useSnapStore';
import { findNearbyPrinters } from '../../src/lib/api';

export default function NearbyPrinters() {
  const router = useRouter();
  const visionReconstruct = useSnapStore((s:any) => s.visionReconstruct);
  const [loading, setLoading] = React.useState(true);
  const [printers, setPrinters] = React.useState<any[]>([]);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    (async () => {
      try {
        setLoading(true);
        const perm = await Location.requestForegroundPermissionsAsync();
        if (!perm.granted) {
          setError('Location permission is required. No nearby search was performed.');
          setPrinters([]);
          return;
        }
        const loc = await Location.getCurrentPositionAsync({});
        const lat = loc.coords.latitude;
        const lon = loc.coords.longitude;
        const material = visionReconstruct?.parametric_draft?.recommended_material || 'PLA';
        const res = await findNearbyPrinters(lat, lon, material);
        setPrinters(res.printers || []);
      } catch (e) {
        console.warn(e);
        setError('Could not find nearby printers right now.');
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Nearby Printers</Text>
      <Text style={styles.subtitle}>Sample printer records for interface preview only. Live locations, availability and ordering are not integrated.</Text>

      {loading ? <ActivityIndicator /> : null}
      {error ? <Text style={styles.error}>{error}</Text> : null}

      <FlatList
        data={printers}
        keyExtractor={(item:any) => item.id}
        renderItem={({ item }: any) => (
          <View style={styles.card}>
            <Text style={styles.cardTitle}>{item.name}</Text>
            <Text style={styles.cardMeta}>{item.distance_miles} miles • sample distance, not live location</Text>
            <Text style={styles.cardMeta}>Materials: {item.materials.join(', ')}</Text>
            <Text style={styles.cardMeta}>Build volume: {item.max_x}×{item.max_y}×{item.max_z} mm</Text>
            <Text style={styles.note}>Ordering is unavailable until a real printer partner is connected.</Text>
          </View>
        )}
        contentContainerStyle={{ gap: 10, paddingBottom: 20 }}
      />

      <Pressable style={styles.secondary} onPress={() => router.back()}>
        <Text style={styles.secondaryText}>Back</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  container:{ flex:1, backgroundColor:'#000', padding:16, gap:12 },
  title:{ color:'#fff', fontSize:24, fontWeight:'800' },
  subtitle:{ color:'#bdbdbd', fontSize:13, lineHeight:18 },
  error:{ color:'#ff7b7b' },
  row:{ color:'#bdbdbd' },
  label:{ color:'#8f8f8f' },
  value:{ color:'#fff', fontWeight:'700' },
  note:{ color:'#bdbdbd', fontSize:12, lineHeight:18 },
  card:{ borderWidth:1, borderColor:'#1f1f1f', backgroundColor:'#0b0b0b', borderRadius:18, padding:14, gap:8 },
  cardTitle:{ color:'#fff', fontWeight:'800', fontSize:16 },
  cardMeta:{ color:'#bdbdbd', fontSize:12, lineHeight:18 },
  primary:{ backgroundColor:'#fff', borderRadius:14, paddingVertical:12, alignItems:'center', marginTop:6 },
  primaryText:{ color:'#000', fontWeight:'800' },
  secondary:{ borderRadius:14, paddingVertical:14, alignItems:'center', borderWidth:1, borderColor:'#2a2a2a' },
  secondaryText:{ color:'#fff', fontWeight:'800' },
});
