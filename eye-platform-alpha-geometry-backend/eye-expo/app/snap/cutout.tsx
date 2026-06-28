import { View, Text, Image, Pressable, StyleSheet, ActivityIndicator } from 'react-native';
import { useRouter } from 'expo-router';
import { useState } from 'react';
import { useSnapStore } from '../../src/lib/useSnapStore';
import { cutoutImage } from '../../src/lib/cutoutImage';

export default function CutoutScreen() {
  const router = useRouter();
  const heroUri = useSnapStore((s) => s.heroUri);
  const cutoutUri = useSnapStore((s) => s.cutoutUri);
  const setCutoutUri = useSnapStore((s) => s.setCutoutUri);
  const clear = useSnapStore((s) => s.clear);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | undefined>();

  if (!heroUri) {
    return (
      <View style={styles.center}>
        <Text style={styles.title}>No Photo Found</Text>
        <Pressable style={styles.primaryButton} onPress={() => router.push('/snap/camera')}>
          <Text style={styles.buttonText}>Open Camera</Text>
        </Pressable>
      </View>
    );
  }

  const onIsolate = async () => {
    try {
      setLoading(true);
      setError(undefined);
      const result = await cutoutImage(heroUri);
      setCutoutUri(result);
    } catch (e: any) {
      setError(e?.message || 'Cutout failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Cutout</Text>
      <Text style={styles.subtitle}>Review the image and isolate the main object before continuing.</Text>

      <Image source={{ uri: cutoutUri || heroUri }} style={styles.image} />

      {loading ? (
        <View style={styles.loadingWrap}>
          <ActivityIndicator size="large" />
          <Text style={styles.loadingText}>Isolating object...</Text>
        </View>
      ) : null}

      {error ? <Text style={styles.error}>{error}</Text> : null}

      <View style={styles.actions}>
        <Pressable style={styles.primaryButton} onPress={onIsolate}>
          <Text style={styles.buttonText}>{cutoutUri ? 'Re-run Cutout' : 'Isolate Object'}</Text>
        </Pressable>

        <Pressable style={styles.secondaryButton} onPress={() => router.push('/snap/process')}>
          <Text style={styles.buttonText}>Continue</Text>
        </Pressable>

        <Pressable style={styles.darkButton} onPress={() => router.push('/snap/camera')}>
          <Text style={styles.buttonText}>Retake</Text>
        </Pressable>

        <Pressable
          style={styles.darkButton}
          onPress={() => {
            clear();
            router.push('/');
          }}
        >
          <Text style={styles.buttonText}>Home</Text>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 20, justifyContent: 'center', backgroundColor: '#fff' },
  title: { fontSize: 28, fontWeight: '800', textAlign: 'center', marginBottom: 8, color: '#111' },
  subtitle: { textAlign: 'center', color: '#555', marginBottom: 16, fontSize: 15 },
  image: { width: '100%', height: 320, resizeMode: 'contain', marginBottom: 20, backgroundColor: '#f7f7f7', borderRadius: 16 },
  loadingWrap: { alignItems: 'center', marginBottom: 14 },
  loadingText: { marginTop: 10, color: '#666' },
  error: { color: '#c62828', textAlign: 'center', marginBottom: 12 },
  actions: { gap: 10 },
  primaryButton: { backgroundColor: '#18c6d1', paddingVertical: 15, borderRadius: 12, alignItems: 'center' },
  secondaryButton: { backgroundColor: '#5b5f97', paddingVertical: 15, borderRadius: 12, alignItems: 'center' },
  darkButton: { backgroundColor: '#444', paddingVertical: 15, borderRadius: 12, alignItems: 'center' },
  buttonText: { color: '#fff', fontWeight: '800' },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 16, padding: 24, backgroundColor: '#fff' },
});
