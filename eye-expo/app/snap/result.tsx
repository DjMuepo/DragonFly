import { View, Text, StyleSheet, Image, Pressable, Linking, ScrollView } from 'react-native';
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
  const generatedStlUrl = useSnapStore((s) => s.generatedStlUrl);
  const generatedProviderKind = useSnapStore((s) => s.generatedProviderKind);
  const reconstructionQuality = useSnapStore((s) => s.reconstructionQuality);
  const preprocessingReport = useSnapStore((s) => s.preprocessingReport);
  const hiddenSurfaceUncertainty = useSnapStore((s) => s.hiddenSurfaceUncertainty);
  const reconstructionWarnings = useSnapStore((s) => s.reconstructionWarnings);
  const modelDownloadUrl = useSnapStore((s) => s.modelDownloadUrl);
  const clear = useSnapStore((s) => s.clear);
  const imageUri = cutoutUri || heroUri;
  const [message, setMessage] = useState<string | null>(null);
  const downloadUrl = modelDownloadUrl || generatedModelUrl;
  const hasModel = /^https?:\/\//i.test(downloadUrl || '');

  if (!imageUri && !hasModel) {
    return <View style={styles.center}><Text style={styles.title}>No result found.</Text><Pressable style={styles.primaryButton} onPress={() => router.push('/snap/camera')}><Text style={styles.buttonText}>Start Scan</Text></Pressable></View>;
  }

  const onDownload = async (url?: string) => {
    if (!url || !/^https?:\/\//i.test(url)) {
      setMessage('No export is available yet. Retry generation.');
      return;
    }
    try {
      await Linking.openURL(url);
    } catch {
      setMessage('Could not open the export. Check your connection and try again.');
    }
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.title}>3D Result</Text>
      {imageUri ? <Image source={{ uri: imageUri }} style={styles.image} /> : null}
      <Text style={styles.label}>Object: {targetLabel || 'Unknown object'}</Text>
      <View style={styles.card}>
        <Text style={styles.cardTitle}>{hasModel ? 'Review Reconstruction' : 'Model Unavailable'}</Text>
        <Text style={styles.cardText}>{hasModel ? 'Compare the shape with your photo before accepting it.' : 'Generation has not completed. Retry to create a model.'}</Text>
        <Text style={styles.cardSubtext}>Model: {generatedModelName || 'not generated yet'}</Text>
        {hasModel ? <Text style={styles.cardSubtext}>{generatedProviderKind === 'ai' ? 'AI reconstruction' : 'Procedural fallback (not AI)'}</Text> : null}
        {hasModel && reconstructionQuality ? <Text style={styles.cardSubtext}>Input mode: {reconstructionQuality.replace('_', ' ')}</Text> : null}
        {hasModel && preprocessingReport ? <Text style={styles.cardSubtext}>{preprocessingReport.foreground_segmenter} segmentation · object crop {preprocessingReport.object_crop_applied ? 'applied' : 'not applied'}</Text> : null}
        {hasModel && hiddenSurfaceUncertainty ? <Text style={styles.cardSubtext}>{hiddenSurfaceUncertainty}</Text> : null}
        {hasModel ? reconstructionWarnings.map((warning) => <Text key={warning} style={styles.cardSubtext}>{warning}</Text>) : null}
      </View>
      {message ? <Text style={styles.message}>{message}</Text> : null}
      <View style={styles.actions}>
        {hasModel ? <Pressable style={styles.primaryButton} onPress={() => router.push('/snap/viewer')}><Text style={styles.buttonText}>View 3D</Text></Pressable> : <Pressable style={styles.primaryButton} onPress={() => router.replace('/snap/reconstruct')}><Text style={styles.buttonText}>Retry Generation</Text></Pressable>}
        {hasModel ? <Pressable style={styles.secondaryButton} onPress={() => onDownload(downloadUrl)}><Text style={styles.buttonText}>Download GLB</Text></Pressable> : null}
        {hasModel && generatedStlUrl ? <Pressable style={styles.secondaryButton} onPress={() => onDownload(generatedStlUrl)}><Text style={styles.buttonText}>Download STL</Text></Pressable> : null}
        {hasModel && reconstructionWarnings.length ? <Pressable style={styles.darkButton} onPress={() => router.replace('/snap/reconstruct')}><Text style={styles.buttonText}>Retry Reconstruction</Text></Pressable> : null}
        <Pressable style={styles.darkButton} onPress={() => { clear(); router.push('/'); }}><Text style={styles.buttonText}>New Scan</Text></Pressable>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flexGrow: 1, padding: 16, alignItems: 'center', justifyContent: 'center', backgroundColor: '#fff' },
  image: { width: '65%', maxWidth: 220, aspectRatio: 1, marginBottom: 16, resizeMode: 'contain', backgroundColor: '#f7f7f7', borderRadius: 8 },
  title: { fontSize: 28, fontWeight: '800', marginBottom: 16, color: '#111', textAlign: 'center' },
  label: { fontSize: 20, fontWeight: '700', marginBottom: 16, textAlign: 'center', color: '#111' },
  card: { width: '100%', maxWidth: 340, backgroundColor: '#f5f7fb', borderRadius: 16, padding: 18, marginBottom: 14 },
  cardTitle: { fontSize: 20, fontWeight: '800', marginBottom: 8, textAlign: 'center' },
  cardText: { textAlign: 'center', color: '#333', marginBottom: 8 },
  cardSubtext: { textAlign: 'center', color: '#666', fontSize: 14, marginBottom: 3 },
  message: { width: '100%', maxWidth: 340, textAlign: 'center', color: '#333', backgroundColor: '#e9fbfd', padding: 10, borderRadius: 10, marginBottom: 12 },
  actions: { width: '100%', maxWidth: 300, gap: 12 },
  primaryButton: { backgroundColor: '#18c6d1', paddingVertical: 15, borderRadius: 12, alignItems: 'center' },
  secondaryButton: { backgroundColor: '#5b5f97', paddingVertical: 15, borderRadius: 12, alignItems: 'center' },
  darkButton: { backgroundColor: '#444', paddingVertical: 15, borderRadius: 12, alignItems: 'center' },
  buttonText: { color: '#fff', fontWeight: '800', fontSize: 16 },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 24, gap: 14, backgroundColor: '#fff' },
});
