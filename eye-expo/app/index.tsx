import { View, Text, Pressable, StyleSheet } from 'react-native';
import { useRouter } from 'expo-router';
import { useSnapStore } from '../src/lib/useSnapStore';

export default function HomeScreen() {
  const router = useRouter();
  const clear = useSnapStore((s) => s.clear);
  const generatedModelUrl = useSnapStore((s) => s.generatedModelUrl);

  const startScan = () => {
    clear();
    router.push('/snap/camera');
  };

  return (
    <View style={styles.container}>
      <Text style={styles.kicker}>Eye Platform</Text>
      <Text style={styles.title}>One-photo AI 3D scan</Text>
      <Text style={styles.subtitle}>Capture or upload one object to create and view a 3D model.</Text>

      <View style={styles.actions}>
        <Pressable style={styles.primaryButton} onPress={startScan}>
          <Text style={styles.primaryText}>Start Scan</Text>
        </Pressable>
        {generatedModelUrl ? <Pressable style={styles.secondaryButton} onPress={() => router.push('/snap/result')}>
          <Text style={styles.secondaryText}>Last Result</Text>
        </Pressable> : null}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: '#f8fafc', padding: 28 },
  kicker: { color: '#18a8b2', fontWeight: '900', letterSpacing: 1.5, textTransform: 'uppercase', marginBottom: 8 },
  title: { fontSize: 34, fontWeight: '900', color: '#111', textAlign: 'center', marginBottom: 12 },
  subtitle: { color: '#555', textAlign: 'center', maxWidth: 360, lineHeight: 22, marginBottom: 26 },
  actions: { width: '100%', maxWidth: 300, gap: 12 },
  primaryButton: { backgroundColor: '#18c6d1', paddingVertical: 16, borderRadius: 14, alignItems: 'center' },
  primaryText: { color: '#fff', fontWeight: '900', fontSize: 16 },
  secondaryButton: { backgroundColor: '#fff', borderWidth: 1, borderColor: '#d9dce5', paddingVertical: 15, borderRadius: 14, alignItems: 'center' },
  secondaryText: { color: '#111', fontWeight: '800' },
});
