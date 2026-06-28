import { View, Text, Image, StyleSheet, Pressable } from 'react-native';
import { useRouter } from 'expo-router';
import { useSnapStore } from '../../src/lib/useSnapStore';

export default function MoreAnglesScreen() {
  const router = useRouter();
  const heroUri = useSnapStore((s) => s.heroUri);
  const cutoutUri = useSnapStore((s) => s.cutoutUri);
  const targetLabel = useSnapStore((s) => s.targetLabel);
  const captured = useSnapStore((s) => s.captured);
  const imageUri = cutoutUri || heroUri;

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Improve Model</Text>
      <Text style={styles.subtitle}>Target object: {targetLabel || 'Unknown object'}</Text>
      <Text style={styles.subtitle}>Captured views: {Math.max(captured.length, imageUri ? 1 : 0)}</Text>

      {imageUri ? <Image source={{ uri: imageUri }} style={styles.image} /> : null}

      <Text style={styles.help}>Optional: capture 1–2 more views only when the first photo is unclear or you want a cleaner model.</Text>

      <View style={styles.actions}>
        <Pressable style={styles.primaryButton} onPress={() => router.push('/snap/camera')}>
          <Text style={styles.buttonText}>Capture Another View</Text>
        </Pressable>

        <Pressable style={styles.secondaryButton} onPress={() => router.push('/snap/reconstruct')}>
          <Text style={styles.buttonText}>Use Current Photo</Text>
        </Pressable>

        <Pressable style={styles.darkButton} onPress={() => router.push('/snap/result')}>
          <Text style={styles.buttonText}>Back to Result</Text>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 24, alignItems: 'center', justifyContent: 'center', backgroundColor: '#fff' },
  title: { fontSize: 28, fontWeight: '800', marginBottom: 10, color: '#111' },
  subtitle: { color: '#555', marginBottom: 6, textAlign: 'center' },
  image: { width: 220, height: 220, marginTop: 18, marginBottom: 18, resizeMode: 'contain', backgroundColor: '#f7f7f7', borderRadius: 16 },
  help: { textAlign: 'center', color: '#333', maxWidth: 320, marginBottom: 20, lineHeight: 20 },
  actions: { width: 300, gap: 12 },
  primaryButton: { backgroundColor: '#18c6d1', paddingVertical: 15, borderRadius: 12, alignItems: 'center' },
  secondaryButton: { backgroundColor: '#5b5f97', paddingVertical: 15, borderRadius: 12, alignItems: 'center' },
  darkButton: { backgroundColor: '#444', paddingVertical: 15, borderRadius: 12, alignItems: 'center' },
  buttonText: { color: '#fff', fontWeight: '800', fontSize: 16 },
});
