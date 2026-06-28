import { View, Text, StyleSheet, Image, Pressable, ActivityIndicator } from 'react-native';
import { useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import { useSnapStore } from '../../src/lib/useSnapStore';

export default function ReconstructScreen() {
  const router = useRouter();
  const heroUri = useSnapStore((s) => s.heroUri);
  const cutoutUri = useSnapStore((s) => s.cutoutUri);
  const targetLabel = useSnapStore((s) => s.targetLabel);
  const clear = useSnapStore((s) => s.clear);
  const setGeneratedModel = useSnapStore((s) => s.setGeneratedModel);
  const imageUri = cutoutUri || heroUri;

  const [stage, setStage] = useState<'preparing' | 'analyzing' | 'building' | 'ready'>('preparing');

  useEffect(() => {
    const timers = [
      setTimeout(() => setStage('analyzing'), 750),
      setTimeout(() => setStage('building'), 1800),
      setTimeout(() => {
        setGeneratedModel('mvp://one-photo-draft.glb', `${targetLabel || 'object'}-draft.glb`);
        setStage('ready');
      }, 3300),
    ];
    return () => timers.forEach(clearTimeout);
  }, [setGeneratedModel, targetLabel]);

  if (!imageUri) {
    return (
      <View style={styles.center}>
        <Text>No image found.</Text>
      </View>
    );
  }

  const progress = stage === 'preparing' ? 25 : stage === 'analyzing' ? 55 : stage === 'building' ? 82 : 100;
  const statusText =
    stage === 'preparing'
      ? 'Preparing source image...'
      : stage === 'analyzing'
        ? 'Analyzing object shape...'
        : stage === 'building'
          ? 'Building 3D structure...'
          : '3D result ready';

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Generating 3D</Text>
      <Image source={{ uri: imageUri }} style={styles.image} />
      <Text style={styles.objectLabel}>Object: {targetLabel || 'Unknown object'}</Text>

      {stage !== 'ready' ? (
        <>
          <ActivityIndicator size="large" />
          <Text style={styles.status}>{statusText}</Text>
          <View style={styles.progressTrack}>
            <View style={[styles.progressFill, { width: `${progress}%` }]} />
          </View>
          <Text style={styles.progressText}>{progress}% complete</Text>
          <Text style={styles.note}>Creating a one-photo 3D draft. More angles can improve accuracy, but they are optional.</Text>
        </>
      ) : (
        <>
          <View style={styles.readyCard}>
            <Text style={styles.readyTitle}>3D Draft Ready</Text>
            <Text style={styles.readyText}>Your initial 3D result has been prepared from a single photo.</Text>
            <Text style={styles.readySubtext}>Continue to preview, export, or improve the model.</Text>
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
  readyTitle: { fontSize: 20, fontWeight: '800', marginBottom: 8, textAlign: 'center' },
  readyText: { textAlign: 'center', color: '#333', marginBottom: 8 },
  readySubtext: { textAlign: 'center', color: '#666', fontSize: 14 },
  actions: { width: 300, gap: 12 },
  primaryButton: { backgroundColor: '#18c6d1', paddingVertical: 15, borderRadius: 12, alignItems: 'center' },
  secondaryButton: { backgroundColor: '#5b5f97', paddingVertical: 15, borderRadius: 12, alignItems: 'center' },
  darkButton: { backgroundColor: '#444', paddingVertical: 15, borderRadius: 12, alignItems: 'center' },
  buttonText: { color: '#fff', fontWeight: '800', fontSize: 16 },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: '#fff' },
});
