import { View, Text, StyleSheet, Pressable, Linking } from 'react-native';
import { useRouter } from 'expo-router';

export default function LaunchHubScreen() {
  const router = useRouter();

  return (
    <View style={styles.container}>
      <Text style={styles.kicker}>Launch Tools</Text>
      <Text style={styles.title}>Eye Alpha Checklist</Text>
      <Text style={styles.subtitle}>Use this page to verify the launch-ready flow and backend connection.</Text>

      <View style={styles.card}>
        <Text style={styles.item}>✓ One-photo camera capture</Text>
        <Text style={styles.item}>✓ AI object detection with fallback</Text>
        <Text style={styles.item}>✓ Geometry backend contract</Text>
        <Text style={styles.item}>✓ GLB-style model output</Text>
        <Text style={styles.item}>✓ Result and preview screens</Text>
      </View>

      <View style={styles.actions}>
        <Pressable style={styles.primaryButton} onPress={() => router.push('/snap/camera')}>
          <Text style={styles.buttonText}>Start Test Scan</Text>
        </Pressable>
        <Pressable style={styles.secondaryButton} onPress={() => router.push('/')}>
          <Text style={styles.secondaryText}>Home</Text>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: '#f8fafc', padding: 28 },
  kicker: { color: '#18a8b2', fontWeight: '900', letterSpacing: 1.5, textTransform: 'uppercase', marginBottom: 8 },
  title: { fontSize: 32, fontWeight: '900', color: '#111', textAlign: 'center', marginBottom: 12 },
  subtitle: { color: '#555', textAlign: 'center', maxWidth: 360, lineHeight: 22, marginBottom: 22 },
  card: { width: '100%', maxWidth: 360, backgroundColor: '#fff', borderRadius: 18, padding: 18, borderWidth: 1, borderColor: '#e6e8ef', marginBottom: 24 },
  item: { color: '#111', fontWeight: '700', marginBottom: 10 },
  actions: { width: 300, gap: 12 },
  primaryButton: { backgroundColor: '#18c6d1', paddingVertical: 16, borderRadius: 14, alignItems: 'center' },
  buttonText: { color: '#fff', fontWeight: '900', fontSize: 16 },
  secondaryButton: { backgroundColor: '#fff', borderWidth: 1, borderColor: '#d9dce5', paddingVertical: 15, borderRadius: 14, alignItems: 'center' },
  secondaryText: { color: '#111', fontWeight: '800' },
});
