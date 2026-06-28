import * as React from 'react';
import { View, Text, StyleSheet, Pressable, ActivityIndicator, FlatList } from 'react-native';
import * as Location from 'expo-location';
import { useRouter } from 'expo-router';
import { useSnapStore } from '../../src/lib/useSnapStore';
import { findNearbyPrinters, submitPrinterJob } from '../../src/lib/api';

export default function NearbyPrinters() {
  const router = useRouter();
  const visionReconstruct = useSnapStore((s:any) => s.visionReconstruct);
  const sessionId = useSnapStore((s:any) => s.sessionId);
  const setSelectedPrinter = useSnapStore((s:any) => s.setSelectedPrinter);
  const setPrintRequest = useSnapStore((s:any) => s.setPrintRequest);
  const printRequest = useSnapStore((s:any) => s.printRequest);
  const [loading, setLoading] = React.useState(true);
  const [printers, setPrinters] = React.useState<any[]>([]);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    (async () => {
      try {
        setLoading(true);
        const perm = await Location.requestForegroundPermissionsAsync();
        let lat = 34.0522;
        let lon = -118.2437;
        if (perm.granted) {
          const loc = await Location.getCurrentPositionAsync({});
          lat = loc.coords.latitude;
          lon = loc.coords.longitude;
        }
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

  const sendToPrinter = async (printer: any) => {
    try {
      const req = await submitPrinterJob({
        printer_id: printer.id,
        session_id: sessionId,
        family: visionReconstruct?.family,
        material: visionReconstruct?.parametric_draft?.recommended_material || 'PLA',
      });
      setSelectedPrinter(printer);
      setPrintRequest(req);
    } catch (e) {
      console.warn(e);
      setError('Could not submit printer request.');
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Nearby Printers</Text>
      <Text style={styles.subtitle}>Find a printer close to you that can print this design.</Text>

      {loading ? <ActivityIndicator /> : null}
      {error ? <Text style={styles.error}>{error}</Text> : null}

      {printRequest ? (
        <View style={styles.panel}>
          <Text style={styles.panelTitle}>Print request sent</Text>
          <Text style={styles.row}><Text style={styles.label}>Printer: </Text><Text style={styles.value}>{printRequest.printer_name}</Text></Text>
          <Text style={styles.row}><Text style={styles.label}>Status: </Text><Text style={styles.value}>{printRequest.status}</Text></Text>
          <Text style={styles.row}><Text style={styles.label}>ETA: </Text><Text style={styles.value}>{printRequest.eta}</Text></Text>
          <Text style={styles.note}>{printRequest.note}</Text>
        </View>
      ) : null}

      <FlatList
        data={printers}
        keyExtractor={(item:any) => item.id}
        renderItem={({ item }: any) => (
          <View style={styles.card}>
            <Text style={styles.cardTitle}>{item.name}</Text>
            <Text style={styles.cardMeta}>{item.distance_miles} miles away • {item.same_day ? 'Same day available' : 'Standard turnaround'}</Text>
            <Text style={styles.cardMeta}>Materials: {item.materials.join(', ')}</Text>
            <Text style={styles.cardMeta}>Build volume: {item.max_x}×{item.max_y}×{item.max_z} mm</Text>
            <Pressable style={styles.primary} onPress={() => sendToPrinter(item)}>
              <Text style={styles.primaryText}>Send design</Text>
            </Pressable>
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
  panel:{ borderWidth:1, borderColor:'#1f1f1f', backgroundColor:'#0b0b0b', borderRadius:18, padding:14, gap:6 },
  panelTitle:{ color:'#fff', fontSize:16, fontWeight:'800' },
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
