import React from 'react';
import { View, Text, StyleSheet, Image, Pressable, Platform, Linking } from 'react-native';
import { useRouter } from 'expo-router';
import { useSnapStore } from '../../src/lib/useSnapStore';

function WebGlbViewer({ url }: { url: string }) {
  const html = `<!doctype html>
<html>
  <head>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <script type="module" src="https://unpkg.com/@google/model-viewer/dist/model-viewer.min.js"></script>
    <style>
      html, body { margin: 0; height: 100%; background: #111827; overflow: hidden; }
      model-viewer { width: 100%; height: 100%; background: radial-gradient(circle at center, #1e2a52, #0b1020); }
    </style>
  </head>
  <body>
    <model-viewer src="${url}" camera-controls auto-rotate shadow-intensity="1" exposure="1" ar></model-viewer>
  </body>
</html>`;

  return React.createElement('iframe', {
    srcDoc: html,
    style: { border: 0, width: '100%', height: '100%' },
    title: 'DragonFly 3D Model Viewer',
    allow: 'xr-spatial-tracking; fullscreen',
  } as any);
}

export default function ViewerScreen() {
  const router = useRouter();
  const heroUri = useSnapStore((s) => s.heroUri);
  const cutoutUri = useSnapStore((s) => s.cutoutUri);
  const targetLabel = useSnapStore((s) => s.targetLabel);
  const generatedModelUrl = useSnapStore((s) => s.generatedModelUrl);
  const generatedModelName = useSnapStore((s) => s.generatedModelName);
  const modelDownloadUrl = useSnapStore((s) => s.modelDownloadUrl);
  const imageUri = cutoutUri || heroUri;

  const modelUrl = generatedModelUrl?.startsWith('http') ? generatedModelUrl : undefined;
  const downloadUrl = modelDownloadUrl?.startsWith('http') ? modelDownloadUrl : modelUrl;

  return (
    <View style={styles.container}>
      <Text style={styles.title}>3D Preview</Text>
      <Text style={styles.subtitle}>{generatedModelName || `${targetLabel || 'Object'} draft`}</Text>

      <View style={styles.viewerBox}>
        {modelUrl && Platform.OS === 'web' ? (
          <WebGlbViewer url={modelUrl} />
        ) : (
          <View style={styles.fallbackPreview}>
            <View style={styles.cubeShadow} />
            <View style={styles.cube}>
              {imageUri ? <Image source={{ uri: imageUri }} style={styles.previewImage} /> : <Text style={styles.cubeText}>3D</Text>}
            </View>
          </View>
        )}
      </View>

      <Text style={styles.label}>{targetLabel || 'Object'} {modelUrl ? 'GLB model' : 'draft preview'}</Text>
      <Text style={styles.note}>
        {modelUrl
          ? 'Live GLB viewer connected. Drag to rotate, zoom, and inspect the generated model.'
          : 'No GLB model URL found yet. Showing stable fallback preview instead of crashing.'}
      </Text>

      <View style={styles.actions}>
        {downloadUrl ? (
          <Pressable style={styles.primaryButton} onPress={() => Linking.openURL(downloadUrl)}>
            <Text style={styles.buttonText}>Open / Download GLB</Text>
          </Pressable>
        ) : null}

        <Pressable style={styles.primaryButton} onPress={() => router.push('/snap/result')}>
          <Text style={styles.buttonText}>Back to Result</Text>
        </Pressable>

        <Pressable style={styles.secondaryButton} onPress={() => router.push('/snap/more-angles')}>
          <Text style={styles.buttonText}>Improve Model</Text>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 24, alignItems: 'center', justifyContent: 'center', backgroundColor: '#0b1020' },
  title: { color: '#fff', fontSize: 30, fontWeight: '900', marginBottom: 8 },
  subtitle: { color: '#c8d0e7', marginBottom: 14, textAlign: 'center' },
  viewerBox: { width: 320, height: 320, borderRadius: 24, backgroundColor: '#141b34', marginBottom: 18, overflow: 'hidden' },
  fallbackPreview: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  cubeShadow: { position: 'absolute', width: 150, height: 36, borderRadius: 18, backgroundColor: 'rgba(0,0,0,0.35)', bottom: 44, transform: [{ scaleX: 1.2 }] },
  cube: { width: 160, height: 190, borderRadius: 20, backgroundColor: '#18c6d1', transform: [{ perspective: 800 }, { rotateY: '-18deg' }, { rotateX: '8deg' }], alignItems: 'center', justifyContent: 'center', borderWidth: 2, borderColor: 'rgba(255,255,255,0.45)' },
  previewImage: { width: 130, height: 150, resizeMode: 'contain', borderRadius: 14 },
  cubeText: { color: '#fff', fontSize: 42, fontWeight: '900' },
  label: { color: '#fff', fontSize: 20, fontWeight: '800', textAlign: 'center' },
  note: { color: '#c8d0e7', textAlign: 'center', marginTop: 10, maxWidth: 340, lineHeight: 20 },
  actions: { width: 300, gap: 12, marginTop: 24 },
  primaryButton: { backgroundColor: '#18c6d1', paddingVertical: 15, borderRadius: 12, alignItems: 'center' },
  secondaryButton: { backgroundColor: '#5b5f97', paddingVertical: 15, borderRadius: 12, alignItems: 'center' },
  buttonText: { color: '#fff', fontWeight: '800', fontSize: 16 },
});
