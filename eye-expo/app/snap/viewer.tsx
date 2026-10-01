import React from 'react';
import { View, Text, StyleSheet, Pressable, Platform, Linking, ScrollView } from 'react-native';
import { useRouter } from 'expo-router';
import { useSnapStore } from '../../src/lib/useSnapStore';
import { AiMeshEditor } from '../../src/components/AiMeshEditor';

function WebGlbViewer({ url }: { url: string }) {
  const safeUrl = url.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;');
  const html = `<!doctype html><html><head><meta name="viewport" content="width=device-width, initial-scale=1" />
<script type="module" src="https://unpkg.com/@google/model-viewer/dist/model-viewer.min.js"></script>
<style>html,body{margin:0;height:100%;background:#141b34;overflow:hidden}model-viewer{width:100%;height:100%;touch-action:pan-y}#status{position:absolute;left:0;right:0;bottom:12px;color:#fff;text-align:center;font:14px sans-serif;background:#141b34;padding:8px}</style>
</head><body><model-viewer id="model" src="${safeUrl}" camera-controls auto-rotate shadow-intensity="1" exposure="1.1" camera-target="auto auto auto"></model-viewer><div id="status" role="status">Loading model...</div><script>const model=document.getElementById('model');const status=document.getElementById('status');model.addEventListener('load',()=>{status.hidden=true});model.addEventListener('error',()=>{status.textContent='Model unavailable. Return to result and retry generation.'});setTimeout(()=>{if(!status.hidden)status.textContent='Model is taking longer than expected. Check your connection.'},30000);</script></body></html>`;
  return React.createElement('iframe', { srcDoc: html, style: { border: 0, width: '100%', height: '100%' }, title: 'DragonFly 3D Model Viewer', allow: 'xr-spatial-tracking; fullscreen' } as any);
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
      <View style={styles.viewerBox}>
        {modelUrl && Platform.OS === 'web' ? <WebGlbViewer url={modelUrl} /> : <View style={styles.unavailable}><Text style={styles.unavailableText}>{modelUrl ? 'Interactive 3D viewing is available on web.' : 'No generated model is available.'}</Text></View>}
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
