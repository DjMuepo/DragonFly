import { View, Text, Image, StyleSheet, ActivityIndicator, Pressable } from 'react-native';
import { useEffect, useState } from 'react';
import { useRouter } from 'expo-router';
import { useSnapStore } from '../../src/lib/useSnapStore';
import { classifyImage, DetectionResult } from '../../src/lib/classifyImage';

export default function ProcessScreen() {
  const router = useRouter();
  const heroUri = useSnapStore((s) => s.heroUri);
  const cutoutUri = useSnapStore((s) => s.cutoutUri);
  const imageUri = cutoutUri || heroUri;
  const setTargetLabel = useSnapStore((s) => s.setTargetLabel);
  const addCaptured = useSnapStore((s) => s.addCaptured);

  const [loading, setLoading] = useState(true);
  const [result, setResult] = useState<DetectionResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;

    async function run() {
      if (!imageUri) {
        setError('No image found.');
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError(null);
        const detection = await classifyImage(imageUri);
        if (!alive) return;
        setResult(detection);
        setTargetLabel(detection.label);
        addCaptured({ uri: imageUri, label: detection.label, confidence: detection.confidence });
      } catch (err: any) {
        if (!alive) return;
        setError(err?.message || 'Detection failed.');
      } finally {
        if (alive) setLoading(false);
      }
    }

    run();
    return () => {
      alive = false;
    };
  }, [imageUri, addCaptured, setTargetLabel]);

  if (!imageUri) {
    return (
      <View style={styles.center}>
        <Text>No image found.</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Photo Ready</Text>
      <Image source={{ uri: imageUri }} style={styles.image} />

      {loading ? (
        <>
          <ActivityIndicator size="large" />
          <Text style={styles.subtitle}>Preparing photo...</Text>
        </>
      ) : error ? (
        <>
          <Text style={styles.error}>Photo unavailable</Text>
          <Text style={styles.subtitle}>{error}</Text>
          <Pressable style={styles.primaryButton} onPress={() => router.replace('/snap/process')}>
            <Text style={styles.buttonText}>Try Again</Text>
          </Pressable>
        </>
      ) : (
        <>
          <Text style={styles.next}>Ready to generate a 3D model from this photo.</Text>

          <View style={styles.actions}>
            <Pressable style={styles.primaryButton} onPress={() => router.push('/snap/reconstruct')}>
              <Text style={styles.buttonText}>Generate 3D</Text>
            </Pressable>

          </View>
        </>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 16, alignItems: 'center', justifyContent: 'center', backgroundColor: '#fff' },
  image: { width: '75%', maxWidth: 260, aspectRatio: 1, marginBottom: 20, resizeMode: 'contain', backgroundColor: '#f7f7f7', borderRadius: 8 },
  title: { fontSize: 24, fontWeight: '800', marginBottom: 18, color: '#111' },
  result: { fontSize: 24, fontWeight: '800', marginTop: 10, textAlign: 'center', color: '#111' },
  subtitle: { color: '#666', marginTop: 10, textAlign: 'center' },
  next: { marginTop: 14, textAlign: 'center', color: '#222', maxWidth: 330, fontSize: 16 },
  optionalNote: { marginTop: 10, textAlign: 'center', color: '#666', maxWidth: 330, fontSize: 14 },
  error: { color: '#c62828', fontWeight: '800', fontSize: 18, marginTop: 8, textAlign: 'center' },
  actions: { marginTop: 24, gap: 12, width: '100%', maxWidth: 300 },
  primaryButton: { backgroundColor: '#18c6d1', paddingVertical: 15, paddingHorizontal: 16, borderRadius: 12, alignItems: 'center' },
  secondaryButton: { backgroundColor: '#5b5f97', paddingVertical: 15, paddingHorizontal: 16, borderRadius: 12, alignItems: 'center' },
  buttonText: { color: '#fff', fontWeight: '800', fontSize: 16 },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: '#fff' },
});
