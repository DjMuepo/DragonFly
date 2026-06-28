import { View, Text, Pressable, StyleSheet } from 'react-native';
import { useRouter } from 'expo-router';
import { useSnapStore } from '../src/lib/useSnapStore';

export default function HomeScreen() {
  const router = useRouter();
  const clear = useSnapStore((s) => s.clear);

  const startScan = () => {
    clear();
    router.push('/snap/camera');
  };

  return (
    <View style={styles.container}>
      <Text style={styles.kicker}>Eye Platform</Text>
      <Text style={styles.title}>One-photo AI 3D scan</Text>
      <Text style={styles.subtitle}>Capture one object, detect it with AI, generate a draft, preview it, and prepare it for printing.</Text>

      <View style={styles.actions}>
        <Pressable style={styles.primaryButton} onPress={startScan}>
          <Text style={styles.primaryText}>Start Scan</Text>
        </Pressable>
        <Pressable style={styles.secondaryButton} onPress={() => router.push('/snap/result')}>
          <Text style={styles.secondaryText}>Last Result</Text>
        </Pressable>
        <Pressable style={styles.secondaryButton} onPress={() => router.push('/launch-hub')}>
          <Text style={styles.secondaryText}>Tools</Text>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: '#f8fafc', padding: 28 },
  kicker: { color: '#18a8b2', fontWeight: '900', letterSpacing: 1.5, textTransform: 'uppercase', marginBottom: 8 },
  title: { fontSize: 34, fontWeight: '900', color: '#111', textAlign: 'center', marginBottom: 12 },
  subtitle: { color: '#555', textAlign: 'center', maxWidth: 360, lineHeight: 22, marginBottom: 26 },
  actions: { width: 300, gap: 12 },
  primaryButton: { backgroundColor: '#18c6d1', paddingVertical: 16, borderRadius: 14, alignItems: 'center' },
  primaryText: { color: '#fff', fontWeight: '900', fontSize: 16 },
  secondaryButton: { backgroundColor: '#fff', borderWidth: 1, borderColor: '#d9dce5', paddingVertical: 15, borderRadius: 14, alignItems: 'center' },
  secondaryText: { color: '#111', fontWeight: '800' },
});
