import { View, Text, StyleSheet, Image, Pressable, Linking } from 'react-native';
import { useRouter } from 'expo-router';
import { useState } from 'react';
import { useSnapStore } from '../../src/lib/useSnapStore';

export default function ResultScreen() {
  const router = useRouter();
  const heroUri = useSnapStore((s) => s.heroUri);
  const cutoutUri = useSnapStore((s) => s.cutoutUri);
  const targetLabel = useSnapStore((s) => s.targetLabel);
  const generatedModelName = useSnapStore((s) => s.generatedModelName);
  const generatedModelUrl = useSnapStore((s) => s.generatedModelUrl);
  const modelDownloadUrl = useSnapStore((s) => s.modelDownloadUrl);
  const clear = useSnapStore((s) => s.clear);
  const imageUri = cutoutUri || heroUri;
  const [message, setMessage] = useState<string | null>(null);

  if (!imageUri) {
    return (
      <View style={styles.center}>
        <Text style={styles.title}>No result found.</Text>
        <Pressable style={styles.primaryButton} onPress={() => router.push('/snap/camera')}>
          <Text style={styles.buttonText}>Start Scan</Text>
        </Pressable>
      </View>
    );
  }

  const downloadUrl = modelDownloadUrl || generatedModelUrl;

  const onNewScan = () => {
    clear();
    router.push('/');
  };

  const onDownload = () => {
    if (downloadUrl?.startsWith('http')) {
      Linking.openURL(downloadUrl);
    } else {
      setMessage('No downloadable GLB is available yet. Run Generate 3D with the geometry backend active on port 8010.');
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>3D Result</Text>
      <Image source={{ uri: imageUri }} style={styles.image} />
      <Text style={styles.label}>Object: {targetLabel || 'Unknown object'}</Text>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Preview Ready</Text>
        <Text style={styles.cardText}>Your one-photo 3D draft has been prepared.</Text>
        <Text style={styles.cardSubtext}>Model: {generatedModelName || 'not generated yet'}</Text>
        <Text style={styles.cardSubtext}>{downloadUrl ? 'GLB export connected' : 'Fallback preview only'}</Text>
      </View>

      {message ? <Text style={styles.message}>{message}</Text> : null}

      <View style={styles.actions}>
        <Pressable style={styles.primaryButton} onPress={() => router.push('/snap/viewer')}>
          <Text style={styles.buttonText}>View 3D</Text>
        </Pressable>

        <Pressable style={styles.secondaryButton} onPress={onDownload}>
          <Text style={styles.buttonText}>Download Model</Text>
        </Pressable>

        <Pressable style={styles.secondaryButton} onPress={() => router.push('/snap/nearby-printers')}>
          <Text style={styles.buttonText}>Find Printer</Text>
        </Pressable>

        <Pressable style={styles.darkButton} onPress={onNewScan}>
          <Text style={styles.buttonText}>New Scan</Text>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 24, alignItems: 'center', justifyContent: 'center', backgroundColor: '#fff' },
  image: { width: 240, height: 240, marginBottom: 16, resizeMode: 'contain', backgroundColor: '#f7f7f7', borderRadius: 16 },
  title: { fontSize: 28, fontWeight: '800', marginBottom: 16, color: '#111', textAlign: 'center' },
  label: { fontSize: 20, fontWeight: '700', marginBottom: 16, textAlign: 'center', color: '#111' },
  card: { width: '100%', maxWidth: 340, backgroundColor: '#f5f7fb', borderRadius: 16, padding: 18, marginBottom: 14 },
  cardTitle: { fontSize: 20, fontWeight: '800', marginBottom: 8, textAlign: 'center' },
  cardText: { textAlign: 'center', color: '#333', marginBottom: 8 },
  cardSubtext: { textAlign: 'center', color: '#666', fontSize: 14, marginBottom: 3 },
  message: { width: '100%', maxWidth: 340, textAlign: 'center', color: '#333', backgroundColor: '#e9fbfd', padding: 10, borderRadius: 10, marginBottom: 12 },
  actions: { width: 300, gap: 12 },
  primaryButton: { backgroundColor: '#18c6d1', paddingVertical: 15, borderRadius: 12, alignItems: 'center' },
  secondaryButton: { backgroundColor: '#5b5f97', paddingVertical: 15, borderRadius: 12, alignItems: 'center' },
  darkButton: { backgroundColor: '#444', paddingVertical: 15, borderRadius: 12, alignItems: 'center' },
  buttonText: { color: '#fff', fontWeight: '800', fontSize: 16 },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 24, gap: 14, backgroundColor: '#fff' },
});
