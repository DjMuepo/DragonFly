import { useState } from 'react';
import { View, Text, StyleSheet, Pressable, TextInput, ActivityIndicator } from 'react-native';
import { useRouter } from 'expo-router';
import { useSnapStore } from '../../src/lib/useSnapStore';
import { editGeometry, preparePrint } from '../../src/lib/geometryApi';
import { calibrateGeometry } from '../../src/lib/geometryApi';

const QUICK_PROMPTS = [
  'Make it 20% larger',
  'Rotate 90 degrees around z',
  'Change its color to blue',
];

export default function AiEditScreen() {
  const router = useRouter();
  const targetLabel = useSnapStore((s) => s.targetLabel);
  const generatedModelUrl = useSnapStore((s) => s.generatedModelUrl);
  const generatedModelName = useSnapStore((s) => s.generatedModelName);
  const generatedStlUrl = useSnapStore((s) => s.generatedStlUrl);
  const generatedProviderKind = useSnapStore((s) => s.generatedProviderKind);
  const modelHistory = useSnapStore((s) => s.modelHistory);
  const applyModelRevision = useSnapStore((s) => s.applyModelRevision);
  const initializeModelHistory = useSnapStore((s) => s.initializeModelHistory);
  const [prompt, setPrompt] = useState('Make it 20% larger');
  const [measurement, setMeasurement] = useState('');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const runEdit = async (nextPrompt = prompt) => {
    if (!generatedModelUrl) {
      setMessage('Generate a model before editing it.');
      return;
    }
    try {
      setBusy(true);
      setMessage('Building edited model...');
      const result = await editGeometry({ label: targetLabel || 'Object', modelUrl: generatedModelUrl, prompt: nextPrompt });
      if (!modelHistory.length) initializeModelHistory({ url: generatedModelUrl, name: generatedModelName || 'original.glb', stlUrl: generatedStlUrl, providerKind: generatedProviderKind || 'ai', summary: 'Original reconstructed model', scaleStatus: 'unknown' });
      applyModelRevision({ url: result.model_url, name: result.model_name, stlUrl: result.stl_download_url, providerKind: result.provider_kind, changeKind: result.change_kind, summary: result.edit_summary || result.notes, scaleStatus: result.scale_status, calibration: result.calibration, validation: result.validation });
      setMessage(result.edit_summary || `Updated with ${result.engine}.`);
      router.push('/snap/viewer');
    } catch (err: any) {
      setMessage(err?.message || 'AI edit failed. Confirm backend port 8010 is public/running.');
    } finally {
      setBusy(false);
    }
  };

  const runPrintPrep = async () => {
    if (!generatedModelUrl) {
      setMessage('Generate a model before requesting print preparation.');
      return;
    }
    try {
      setBusy(true);
      const result = await preparePrint({ modelUrl: generatedModelUrl, material: 'PLA', infillPercent: 20 });
      setMessage(`Print estimate: ${result.estimated_weight_g}g, ${result.estimated_print_time_min} min. Checks: ${result.checks.join(', ')}`);
    } catch (err: any) {
      setMessage(err?.message || 'Print prep failed.');
    } finally {
      setBusy(false);
    }
  };

  const calibrateFromMeasurement = async () => {
    if (!generatedModelUrl) {
      setMessage('Generate a model before calibrating it.');
      return;
    }
    if (!measurement.trim()) {
      setMessage('Enter one known physical measurement before calibration.');
      return;
    }
    try {
      setBusy(true);
      setMessage('Calibrating physical scale...');
      const result = await calibrateGeometry({ label: targetLabel || 'Object', modelUrl: generatedModelUrl, measurement: measurement.trim() });
      if (!modelHistory.length) initializeModelHistory({ url: generatedModelUrl, name: generatedModelName || 'original.glb', stlUrl: generatedStlUrl, providerKind: generatedProviderKind || 'ai', summary: 'Original reconstructed model', scaleStatus: 'unknown' });
      applyModelRevision({ url: result.model_url, name: result.model_name, stlUrl: result.stl_download_url, providerKind: result.provider_kind, changeKind: 'geometry', summary: result.edit_summary || result.notes, scaleStatus: result.scale_status, calibration: result.calibration, validation: result.validation });
      setMessage(result.edit_summary || 'Physical scale calibrated.');
    } catch (err: any) {
      setMessage(err?.message || 'Calibration failed. Check the known measurement and try again.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Model Edit</Text>
      <Text style={styles.subtitle}>Describe a supported deterministic geometry or appearance change.</Text>
      <TextInput style={styles.input} value={measurement} onChangeText={setMeasurement} placeholder="Enter a known measurement, e.g. 100 mm tall" placeholderTextColor="#7c8499" editable={!busy} accessibilityLabel="Known physical measurement" />
      <Pressable style={styles.secondaryButton} onPress={() => void calibrateFromMeasurement()} disabled={busy || !measurement.trim()}><Text style={styles.buttonText}>Calibrate Model</Text></Pressable>
      <TextInput style={styles.input} value={prompt} onChangeText={setPrompt} multiline placeholder="Example: make it taller and add a base" placeholderTextColor="#7c8499" />
      <View style={styles.quickGrid}>{QUICK_PROMPTS.map((item) => <Pressable key={item} style={styles.quickButton} onPress={() => { setPrompt(item); runEdit(item); }}><Text style={styles.quickText}>{item}</Text></Pressable>)}</View>
      {message ? <Text style={styles.message}>{message}</Text> : null}
      {busy ? <ActivityIndicator size="large" /> : null}
      <View style={styles.actions}>
        <Pressable style={styles.primaryButton} onPress={() => runEdit()} disabled={busy}><Text style={styles.buttonText}>Apply AI Edit</Text></Pressable>
        <Pressable style={styles.secondaryButton} onPress={runPrintPrep} disabled={busy}><Text style={styles.buttonText}>Check print readiness</Text></Pressable>
        <Pressable style={styles.darkButton} onPress={() => router.push('/snap/viewer')}><Text style={styles.buttonText}>Back to Viewer</Text></Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 24, backgroundColor: '#0b1020', alignItems: 'center', justifyContent: 'center' },
  title: { color: '#fff', fontSize: 30, fontWeight: '900', marginBottom: 8 },
  subtitle: { color: '#c8d0e7', textAlign: 'center', marginBottom: 16 },
  input: { width: '100%', maxWidth: 380, minHeight: 110, backgroundColor: '#141b34', color: '#fff', borderRadius: 16, padding: 16, borderWidth: 1, borderColor: '#26385f', textAlignVertical: 'top', marginBottom: 14 },
  quickGrid: { width: '100%', maxWidth: 380, gap: 8, marginBottom: 14 },
  quickButton: { backgroundColor: '#1d2a4d', borderRadius: 12, padding: 12 },
  quickText: { color: '#e8edff', fontWeight: '700', textAlign: 'center' },
  message: { width: '100%', maxWidth: 380, color: '#e8edff', backgroundColor: '#162344', borderRadius: 12, padding: 12, textAlign: 'center', marginBottom: 12 },
  actions: { width: 310, gap: 12, marginTop: 16 },
  primaryButton: { backgroundColor: '#18c6d1', paddingVertical: 15, borderRadius: 12, alignItems: 'center' },
  secondaryButton: { backgroundColor: '#5b5f97', paddingVertical: 15, borderRadius: 12, alignItems: 'center' },
  darkButton: { backgroundColor: '#444', paddingVertical: 15, borderRadius: 12, alignItems: 'center' },
  buttonText: { color: '#fff', fontWeight: '800', fontSize: 16 },
});
