import { View, Text, StyleSheet, Image, Pressable, ActivityIndicator } from 'react-native';
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
  const setJobResultLinks = useSnapStore((s) => s.setJobResultLinks);
  const imageUri = cutoutUri || heroUri;

  const [stage, setStage] = useState<'preparing' | 'analyzing' | 'building' | 'ready' | 'error'>('preparing');
  const [error, setError] = useState<string | null>(null);
  const [modelName, setModelName] = useState<string | null>(null);
  const [engine, setEngine] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;

    async function run() {
      if (!imageUri) {
        setStage('error');
        setError('No image found. Start a new scan and try again.');
        return;
      }

      try {
        setStage('preparing');
        await new Promise((resolve) => setTimeout(resolve, 250));
        if (!alive) return;

        setStage('analyzing');
        await new Promise((resolve) => setTimeout(resolve, 350));
        if (!alive) return;

        setStage('building');
        const result = await generateGeometryFromImage({
          imageUri,
          label: targetLabel || 'Object',
          confidence: 0.7,
        });
        if (!alive) return;

        setGeneratedModel(result.model_url, result.model_name);
        setJobResultLinks(result.model_url, result.download_url);
        setModelName(result.model_name);
        setEngine(result.engine);
        setStage('ready');
      } catch (err: any) {
        if (!alive) return;
        setGeneratedModel(undefined, undefined);
        setJobResultLinks(undefined, undefined);
        setError(err?.message || '3D generation failed. Check that the geometry backend is running on port 8010.');
        setStage('error');
      }
    }

    run();

    return () => {
      alive = false;
    };
  }, [imageUri, targetLabel, setGeneratedModel, setJobResultLinks]);

  if (!imageUri) {
    return (
      <View style={styles.center}>
        <Text>No image found.</Text>
      </View>
    );
  }

  const progress = stage === 'preparing' ? 25 : stage === 'analyzing' ? 55 : stage === 'building' ? 82 : stage === 'ready' ? 100 : 0;
  const statusText =
    stage === 'preparing'
      ? 'Preparing source image...'
      : stage === 'analyzing'
        ? 'Analyzing object shape...'
        : stage === 'building'
          ? 'Generating GLB model...'
          : stage === 'ready'
            ? '3D result ready'
            : 'Generation error';

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Generating 3D</Text>
      <Image source={{ uri: imageUri }} style={styles.image} />
      <Text style={styles.objectLabel}>Object: {targetLabel || 'Unknown object'}</Text>

      {stage !== 'ready' && stage !== 'error' ? (
        <>
          <ActivityIndicator size="large" />
          <Text style={styles.status}>{statusText}</Text>
          <View style={styles.progressTrack}>
            <View style={[styles.progressFill, { width: `${progress}%` }]} />
          </View>
          <Text style={styles.progressText}>{progress}% complete</Text>
          <Text style={styles.note}>Creating a one-photo GLB draft. More angles can improve accuracy, but they are optional.</Text>
        </>
      ) : (
        <>
          <View style={stage === 'error' ? styles.errorCard : styles.readyCard}>
            <Text style={styles.readyTitle}>{stage === 'error' ? 'Generation Needs Backend' : '3D Draft Ready'}</Text>
            <Text style={styles.readyText}>
              {stage === 'error'
                ? 'The app is stable, but the geometry backend did not return a model. Start port 8010 and try again.'
                : 'Your initial GLB result has been prepared from a single photo.'}
            </Text>
            {modelName ? <Text style={styles.readySubtext}>Model: {modelName}</Text> : null}
            {engine ? <Text style={styles.readySubtext}>Engine: {engine}</Text> : null}
            {error ? <Text style={styles.warning}>{error}</Text> : null}
          </View>

          <View style={styles.actions}>
            <Pressable style={styles.primaryButton} onPress={() => router.push('/snap/viewer')}>
              <Text style={styles.buttonText}>View 3D</Text>
            </Pressable>

            <Pressable style={styles.secondaryButton} onPress={() => router.push('/snap/result')}>
              <Text style={styles.buttonText}>Save / Finish</Text>
            </Pressable>

            <Pressable style={styles.darkButton} onPress={() => router.push('/snap/more-angles')}>
              <Text style={styles.buttonText}>Improve Model</Text>
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
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 24, alignItems: 'center', justifyContent: 'center', backgroundColor: '#fff' },
  image: { width: 240, height: 240, marginBottom: 18, resizeMode: 'contain', backgroundColor: '#f7f7f7', borderRadius: 16 },
  title: { fontSize: 28, fontWeight: '800', marginBottom: 16, color: '#111' },
  objectLabel: { fontSize: 20, fontWeight: '700', marginBottom: 16, textAlign: 'center', color: '#111' },
  status: { marginTop: 12, color: '#444', fontSize: 16, textAlign: 'center' },
  progressTrack: { width: 280, height: 12, backgroundColor: '#d9d9d9', borderRadius: 999, overflow: 'hidden', marginTop: 18 },
  progressFill: { height: '100%', backgroundColor: '#18c6d1', borderRadius: 999 },
  progressText: { marginTop: 10, color: '#666', fontWeight: '700' },
  note: { marginTop: 18, textAlign: 'center', color: '#666', maxWidth: 320 },
  readyCard: { width: '100%', maxWidth: 340, backgroundColor: '#f5f7fb', borderRadius: 16, padding: 18, marginTop: 10, marginBottom: 18 },
  errorCard: { width: '100%', maxWidth: 340, backgroundColor: '#fff5dd', borderRadius: 16, padding: 18, marginTop: 10, marginBottom: 18 },
  readyTitle: { fontSize: 20, fontWeight: '800', marginBottom: 8, textAlign: 'center' },
  readyText: { textAlign: 'center', color: '#333', marginBottom: 8 },
  readySubtext: { textAlign: 'center', color: '#666', fontSize: 14, marginBottom: 4 },
  warning: { textAlign: 'center', color: '#9a5a00', marginTop: 8, fontSize: 12 },
  actions: { width: 300, gap: 12 },
  primaryButton: { backgroundColor: '#18c6d1', paddingVertical: 15, borderRadius: 12, alignItems: 'center' },
  secondaryButton: { backgroundColor: '#5b5f97', paddingVertical: 15, borderRadius: 12, alignItems: 'center' },
  darkButton: { backgroundColor: '#444', paddingVertical: 15, borderRadius: 12, alignItems: 'center' },
  buttonText: { color: '#fff', fontWeight: '800', fontSize: 16 },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: '#fff' },
});
