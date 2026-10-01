import React, { useEffect, useRef, useState } from 'react';
import { View, Text, StyleSheet, Pressable, Platform, Linking, ScrollView } from 'react-native';
import { useRouter } from 'expo-router';
import { useSnapStore } from '../../src/lib/useSnapStore';
import { AiMeshEditor } from '../../src/components/AiMeshEditor';

function WebGlbViewer({ url }: { url: string }) {
  const viewerRef = useRef<any>(null);
  const [status, setStatus] = useState('Loading model...');

  useEffect(() => {
    if (typeof document === 'undefined') return;
    if (!document.querySelector('script[data-dragonfly-model-viewer]')) {
      const script = document.createElement('script');
      script.type = 'module';
      script.src = 'https://unpkg.com/@google/model-viewer/dist/model-viewer.min.js';
      script.dataset.dragonflyModelViewer = 'true';
      document.head.appendChild(script);
    }
  }, []);

  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer) return;
    let cancelled = false;
    setStatus('Loading model...');
    const loaded = () => setStatus('');
    const failed = () => setStatus('Model unavailable. Return to result and retry generation.');
    viewer.addEventListener('load', loaded);
    viewer.addEventListener('error', failed);
    if (typeof customElements !== 'undefined') {
      customElements.whenDefined('model-viewer').then(() => {
        if (cancelled || !viewerRef.current) return;
        viewerRef.current.removeAttribute('src');
        requestAnimationFrame(() => {
          if (!cancelled && viewerRef.current) viewerRef.current.setAttribute('src', url);
        });
      });
    }
    const timeout = setTimeout(() => setStatus((current) => current ? 'Model is taking longer than expected. Check your connection.' : ''), 30000);
    return () => {
      cancelled = true;
      clearTimeout(timeout);
      viewer.removeEventListener('load', loaded);
      viewer.removeEventListener('error', failed);
    };
  }, [url]);

  return (
    <View style={styles.webViewer}>
      {React.createElement('model-viewer', { key: url, ref: viewerRef, src: url, loading: 'eager', 'camera-controls': true, 'auto-rotate': true, 'shadow-intensity': '1', exposure: '1.1', 'camera-target': 'auto auto auto', style: { width: '100%', height: '100%', touchAction: 'pan-y' } } as any)}
      {status ? <View style={styles.viewerStatus}><Text style={styles.viewerStatusText}>{status}</Text></View> : null}
    </View>
  );
}

export default function ViewerScreen() {
  const router = useRouter();
  const targetLabel = useSnapStore((s) => s.targetLabel);
  const generatedModelUrl = useSnapStore((s) => s.generatedModelUrl);
  const generatedModelName = useSnapStore((s) => s.generatedModelName);
  const modelDownloadUrl = useSnapStore((s) => s.modelDownloadUrl);
  const modelUrl = generatedModelUrl?.startsWith('http') ? generatedModelUrl : undefined;
  const downloadUrl = modelDownloadUrl?.startsWith('http') ? modelDownloadUrl : modelUrl;

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.title}>3D Preview</Text>
      <Text style={styles.subtitle}>{generatedModelName || `${targetLabel || 'Object'} model`}</Text>
      <View key={modelUrl || 'unavailable'} style={styles.viewerBox}>
        {modelUrl && Platform.OS === 'web' ? <WebGlbViewer key={modelUrl} url={modelUrl} /> : <View style={styles.unavailable}><Text style={styles.unavailableText}>{modelUrl ? 'Interactive 3D viewing is available on web.' : 'No generated model is available.'}</Text></View>}
      </View>
      <Text style={styles.label}>{targetLabel || 'Object'} {modelUrl ? '3D model' : 'model unavailable'}</Text>
      <Text style={styles.note}>{modelUrl ? 'Drag to rotate. Pinch or scroll to zoom.' : 'Return to generation and retry.'}</Text>
      {modelUrl ? <AiMeshEditor /> : null}
      <View style={styles.actions}>
        {downloadUrl ? <Pressable style={styles.primaryButton} onPress={() => Linking.openURL(downloadUrl)}><Text style={styles.buttonText}>Open / Download GLB</Text></Pressable> : null}
        {!modelUrl ? <Pressable style={styles.primaryButton} onPress={() => router.replace('/snap/reconstruct')}><Text style={styles.buttonText}>Retry Generation</Text></Pressable> : null}
        <Pressable style={styles.primaryButton} onPress={() => router.push('/snap/result')}><Text style={styles.buttonText}>Back to Result</Text></Pressable>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0b1020' },
  content: { flexGrow: 1, alignItems: 'center', justifyContent: 'center', padding: 16 },
  title: { color: '#fff', fontSize: 30, fontWeight: '900', marginBottom: 8 },
  subtitle: { color: '#c8d0e7', marginBottom: 14, textAlign: 'center' },
  viewerBox: { width: '100%', maxWidth: 420, aspectRatio: 1, borderRadius: 8, backgroundColor: '#141b34', marginBottom: 18, overflow: 'hidden' },
  webViewer: { flex: 1, backgroundColor: '#141b34' },
  viewerStatus: { position: 'absolute', left: 0, right: 0, bottom: 12, padding: 8, backgroundColor: '#141b34' },
  viewerStatusText: { color: '#fff', textAlign: 'center' },
  unavailable: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 28 },
  unavailableText: { color: '#c8d0e7', textAlign: 'center', fontWeight: '700' },
  label: { color: '#fff', fontSize: 20, fontWeight: '800', textAlign: 'center' },
  note: { color: '#c8d0e7', textAlign: 'center', marginTop: 10, maxWidth: 360, lineHeight: 20 },
  actions: { width: '100%', maxWidth: 310, gap: 12, marginTop: 24 },
  primaryButton: { backgroundColor: '#18c6d1', paddingVertical: 15, borderRadius: 12, alignItems: 'center' },
  secondaryButton: { backgroundColor: '#5b5f97', paddingVertical: 15, borderRadius: 12, alignItems: 'center' },
  darkButton: { backgroundColor: '#444', paddingVertical: 15, borderRadius: 12, alignItems: 'center' },
  buttonText: { color: '#fff', fontWeight: '800', fontSize: 16 },
});
