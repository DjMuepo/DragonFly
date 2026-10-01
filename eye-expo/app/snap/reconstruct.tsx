import { View, Text, StyleSheet, Image, Pressable, ActivityIndicator, ScrollView } from 'react-native';
import { useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import { useSnapStore } from '../../src/lib/useSnapStore';
import { generateGeometryFromImage } from '../../src/lib/geometryApi';

export default function ReconstructScreen() {
  const router = useRouter();
  const heroUri = useSnapStore((s) => s.heroUri);
  const cutoutUri = useSnapStore((s) => s.cutoutUri);
  const targetLabel = useSnapStore((s) => s.targetLabel);
  const clear = useSnapStore((s) => s.clear);
  const setGeneratedModel = useSnapStore((s) => s.setGeneratedModel);
  const setGeneratedExport = useSnapStore((s) => s.setGeneratedExport);
  const initializeModelHistory = useSnapStore((s) => s.initializeModelHistory);
  const setJobResultLinks = useSnapStore((s) => s.setJobResultLinks);
  const imageUri = cutoutUri || heroUri;

  const [stage, setStage] = useState<'building' | 'ready' | 'error'>('building');
  const [error, setError] = useState<string | null>(null);
  const [modelName, setModelName] = useState<string | null>(null);
  const [engine, setEngine] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let alive = true;

    async function run() {
      if (!imageUri) {
        setStage('error');
        setError('No image found. Start a new scan and try again.');
        return;
      }

      try {
        setStage('building');
        setError(null);
        setProgress(0);
        setEngine(null);
        setGeneratedModel(undefined, undefined);
        setGeneratedExport(undefined, undefined);
        setJobResultLinks(undefined, undefined);
        const result = await generateGeometryFromImage({
          imageUri,
          label: targetLabel || 'Object',
          confidence: 0.7,
          onProgress: (job) => {
            if (alive) {
              setProgress(job.progress);
              setEngine(`${job.provider} (${job.provider_kind})`);
            }
          },
        });
        if (!alive) return;

        setGeneratedModel(result.model_url, result.model_name);
        setGeneratedExport(result.stl_download_url, result.provider_kind);
        initializeModelHistory({ url: result.model_url, name: result.model_name, stlUrl: result.stl_download_url, providerKind: result.provider_kind, summary: 'Original reconstructed model' });
        setJobResultLinks(result.model_url, result.download_url);
        setModelName(result.model_name);
        setEngine(`${result.engine} (${result.provider_kind})`);
        setStage('ready');
      } catch (err: any) {
        if (!alive) return;
        setGeneratedModel(undefined, undefined);
        setGeneratedExport(undefined, undefined);
        setJobResultLinks(undefined, undefined);
        setError(err?.message || '3D generation failed. Check your connection and try again.');
        setStage('error');
      }
    }

    run();

    return () => {
      alive = false;
    };
  }, [attempt, imageUri, targetLabel, setGeneratedModel, setGeneratedExport, initializeModelHistory, setJobResultLinks]);

  if (!imageUri) {
    return (
      <View style={styles.center}>
        <Text>No image found.</Text>
      </View>
    );
  }

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.title}>Generating 3D</Text>
      <Image source={{ uri: imageUri }} style={styles.image} />
      <Text style={styles.objectLabel}>Object: {targetLabel || 'Unknown object'}</Text>

      {stage === 'building' ? (
        <>
          <ActivityIndicator size="large" />
          <Text style={styles.status}>{engine ? `Generating with ${engine}: ${progress}%` : 'Submitting image reconstruction job...'}</Text>
          <Text style={styles.note}>This can take a moment. The model actions appear only after the backend returns a valid URL.</Text>
        </>
      ) : stage === 'error' ? (
        <>
          <View style={styles.errorCard}>
            <Text style={styles.readyTitle}>Generation Failed</Text>
            <Text style={styles.readyText}>The backend did not return a usable model.</Text>
            {error ? <Text style={styles.warning}>{error}</Text> : null}
          </View>
          <View style={styles.actions}>
            <Pressable style={styles.primaryButton} onPress={() => setAttempt((value) => value + 1)}>
              <Text style={styles.buttonText}>Try Again</Text>
            </Pressable>
            <Pressable style={styles.darkButton} onPress={() => router.push('/snap/camera')}>
              <Text style={styles.buttonText}>Retake Photo</Text>
            </Pressable>
          </View>
        </>
      ) : (
        <>
          <View style={styles.readyCard}>
            <Text style={styles.readyTitle}>3D Model Ready</Text>
            <Text style={styles.readyText}>Your GLB was generated from this photo.</Text>
            {modelName ? <Text style={styles.readySubtext}>Model: {modelName}</Text> : null}
            {engine ? <Text style={styles.readySubtext}>Engine: {engine}</Text> : null}
          </View>
          <View style={styles.actions}>
            <Pressable style={styles.primaryButton} onPress={() => router.push('/snap/viewer')}>
              <Text style={styles.buttonText}>View 3D</Text>
            </Pressable>
            <Pressable style={styles.secondaryButton} onPress={() => router.push('/snap/result')}>
              <Text style={styles.buttonText}>Save / Finish</Text>
            </Pressable>

            <Pressable
              style={styles.darkButton}
              onPress={() => {
                clear();
                router.push('/');
              }}
            >
              <Text style={styles.buttonText}>Start New Scan</Text>
            </Pressable>
          </View>
        </>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flexGrow: 1, padding: 16, alignItems: 'center', justifyContent: 'center', backgroundColor: '#fff' },
  image: { width: '70%', maxWidth: 240, aspectRatio: 1, marginBottom: 18, resizeMode: 'contain', backgroundColor: '#f7f7f7', borderRadius: 8 },
  title: { fontSize: 28, fontWeight: '800', marginBottom: 16, color: '#111' },
  objectLabel: { fontSize: 20, fontWeight: '700', marginBottom: 16, textAlign: 'center', color: '#111' },
  status: { marginTop: 12, color: '#444', fontSize: 16, textAlign: 'center' },
  note: { marginTop: 18, textAlign: 'center', color: '#666', maxWidth: 320 },
  readyCard: { width: '100%', maxWidth: 340, backgroundColor: '#f5f7fb', borderRadius: 16, padding: 18, marginTop: 10, marginBottom: 18 },
  errorCard: { width: '100%', maxWidth: 340, backgroundColor: '#fff5dd', borderRadius: 16, padding: 18, marginTop: 10, marginBottom: 18 },
  readyTitle: { fontSize: 20, fontWeight: '800', marginBottom: 8, textAlign: 'center' },
  readyText: { textAlign: 'center', color: '#333', marginBottom: 8 },
  readySubtext: { textAlign: 'center', color: '#666', fontSize: 14, marginBottom: 4 },
  warning: { textAlign: 'center', color: '#9a5a00', marginTop: 8, fontSize: 12 },
  actions: { width: '100%', maxWidth: 300, gap: 12 },
  primaryButton: { backgroundColor: '#18c6d1', paddingVertical: 15, borderRadius: 12, alignItems: 'center' },
  secondaryButton: { backgroundColor: '#5b5f97', paddingVertical: 15, borderRadius: 12, alignItems: 'center' },
  darkButton: { backgroundColor: '#444', paddingVertical: 15, borderRadius: 12, alignItems: 'center' },
  buttonText: { color: '#fff', fontWeight: '800', fontSize: 16 },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: '#fff' },
});
