import { useRef, useState } from 'react';
import { ActivityIndicator, Linking, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
import { calibrateGeometry, editGeometry } from '../lib/geometryApi';
import { useSnapStore } from '../lib/useSnapStore';

const EXAMPLES = [
  'Make it 20% larger',
  'Make it 100 mm tall',
  'Rotate 90 degrees around z',
  'Move 10 mm right',
  'Add a 5 mm base',
  'Make it blue',
];

export function AiMeshEditor() {
  const targetLabel = useSnapStore((state) => state.targetLabel);
  const generatedModelUrl = useSnapStore((state) => state.generatedModelUrl);
  const generatedModelName = useSnapStore((state) => state.generatedModelName);
  const generatedStlUrl = useSnapStore((state) => state.generatedStlUrl);
  const generatedProviderKind = useSnapStore((state) => state.generatedProviderKind);
  const modelHistory = useSnapStore((state) => state.modelHistory);
  const modelHistoryIndex = useSnapStore((state) => state.modelHistoryIndex);
  const applyModelRevision = useSnapStore((state) => state.applyModelRevision);
  const initializeModelHistory = useSnapStore((state) => state.initializeModelHistory);
  const undoModelEdit = useSnapStore((state) => state.undoModelEdit);
  const redoModelEdit = useSnapStore((state) => state.redoModelEdit);
  const resetModelEdits = useSnapStore((state) => state.resetModelEdits);
  const [prompt, setPrompt] = useState('');
  const [measurement, setMeasurement] = useState('');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const submitting = useRef(false);
  const revision = modelHistory[modelHistoryIndex];

  const applyEdit = async (instruction = prompt) => {
    if (!generatedModelUrl || !instruction.trim() || submitting.current) return;
    submitting.current = true;
    try {
      if (!modelHistory.length) {
        initializeModelHistory({ url: generatedModelUrl, name: generatedModelName || 'original.glb', stlUrl: generatedStlUrl, providerKind: generatedProviderKind || 'ai', summary: 'Original reconstructed model', scaleStatus: 'unknown' });
      }
      setBusy(true);
      setMessage('Applying geometry edit...');
      const result = await editGeometry({ label: targetLabel || 'Object', modelUrl: generatedModelUrl, prompt: instruction.trim() });
      applyModelRevision({
        url: result.model_url,
        name: result.model_name,
        stlUrl: result.stl_download_url,
        providerKind: result.provider_kind,
        changeKind: result.change_kind,
        summary: result.edit_summary || result.notes,
        scaleStatus: result.scale_status,
        calibration: result.calibration,
        validation: result.validation,
      });
      setPrompt('');
      setMessage(result.change_kind === 'visual_only' ? `${result.edit_summary} Visual only; mesh dimensions are unchanged.` : result.edit_summary || 'Geometry updated.');
    } catch (error: any) {
      setMessage(error?.message || 'The edit could not be applied. Try a supported instruction.');
    } finally {
      submitting.current = false;
      setBusy(false);
    }
  };

  const calibrate = async () => {
    if (!generatedModelUrl || !measurement.trim() || submitting.current) return;
    submitting.current = true;
    try {
      if (!modelHistory.length) {
        initializeModelHistory({ url: generatedModelUrl, name: generatedModelName || 'original.glb', stlUrl: generatedStlUrl, providerKind: generatedProviderKind || 'ai', summary: 'Original reconstructed model', scaleStatus: 'unknown' });
      }
      setBusy(true);
      setMessage('Calibrating physical scale...');
      const result = await calibrateGeometry({ label: targetLabel || 'Object', modelUrl: generatedModelUrl, measurement: measurement.trim() });
      applyModelRevision({ url: result.model_url, name: result.model_name, stlUrl: result.stl_download_url, providerKind: result.provider_kind, changeKind: 'geometry', summary: result.edit_summary || result.notes, scaleStatus: result.scale_status, calibration: result.calibration, validation: result.validation });
      setMeasurement('');
      setMessage(result.edit_summary || 'Model calibrated.');
    } catch (error: any) {
      setMessage(error?.message || 'Calibration failed. Enter one known dimension and try again.');
    } finally {
      submitting.current = false;
      setBusy(false);
    }
  };

  const openExport = async (url?: string) => {
    if (!url) return;
    try {
      await Linking.openURL(url);
    } catch {
      setMessage('Could not open the export. Check your connection and try again.');
    }
  };

  return (
    <View style={styles.panel}>
      <Text style={styles.title}>Edit with AI guidance</Text>
      <Text style={styles.help}>Describe a measurable change. Geometry edits alter exports; color changes are visual only.</Text>
      <View style={styles.scalePanel}>
        <Text style={styles.scaleTitle}>Dimensions &amp; Scale</Text>
        <Text style={revision?.scaleStatus === 'calibrated' ? styles.calibrated : styles.estimated}>
          {revision?.scaleStatus === 'calibrated' ? 'Calibrated physical dimensions' : 'Estimated proportions — physical scale unknown'}
        </Text>
        {revision?.validation?.dimensions_mm ? (
          <Text style={styles.validationText}>W {revision.validation.dimensions_mm.width} × D {revision.validation.dimensions_mm.depth} × H {revision.validation.dimensions_mm.height} mm</Text>
        ) : revision?.validation?.dimensions_model_units ? (
          <Text style={styles.validationText}>Model-unit bounds: W {revision.validation.dimensions_model_units.width} × D {revision.validation.dimensions_model_units.depth} × H {revision.validation.dimensions_model_units.height}</Text>
        ) : null}
        <TextInput style={styles.measurementInput} value={measurement} onChangeText={setMeasurement} placeholder="This bottle is 180 mm tall" placeholderTextColor="#7c8499" editable={!busy} returnKeyType="done" onSubmitEditing={() => void calibrate()} accessibilityLabel="Known physical dimension" />
        <Pressable style={[styles.calibrateButton, (busy || !measurement.trim()) && styles.disabled]} onPress={() => void calibrate()} disabled={busy || !measurement.trim()}><Text style={styles.calibrateText}>Calibrate Model</Text></Pressable>
      </View>
      <TextInput
        style={styles.input}
        value={prompt}
        onChangeText={setPrompt}
        placeholder="Example: make it 100 mm tall"
        placeholderTextColor="#7c8499"
        multiline
        editable={!busy}
        returnKeyType="send"
        submitBehavior="blurAndSubmit"
        onSubmitEditing={(event) => void applyEdit(event.nativeEvent.text)}
        onKeyPress={(event) => {
          if (event.nativeEvent.key === 'Enter') {
            event.preventDefault();
            void applyEdit(prompt);
          }
        }}
        accessibilityLabel="Editing instruction"
      />
      <View style={styles.examples}>
        {EXAMPLES.map((example) => (
          <Pressable key={example} style={styles.example} onPress={() => { setPrompt(example); void applyEdit(example); }} disabled={busy}>
            <Text style={styles.exampleText}>{example}</Text>
          </Pressable>
        ))}
      </View>
      <Pressable style={[styles.apply, (busy || !prompt.trim()) && styles.disabled]} onPress={() => void applyEdit()} disabled={busy || !prompt.trim()}>
        {busy ? <ActivityIndicator color="#071519" /> : <Text style={styles.applyText}>Apply Edit</Text>}
      </Pressable>
      <View style={styles.history}>
        <Pressable style={[styles.historyButton, modelHistoryIndex <= 0 && styles.disabled]} onPress={undoModelEdit} disabled={modelHistoryIndex <= 0}><Text style={styles.historyText}>Undo</Text></Pressable>
        <Pressable style={[styles.historyButton, modelHistoryIndex >= modelHistory.length - 1 && styles.disabled]} onPress={redoModelEdit} disabled={modelHistoryIndex >= modelHistory.length - 1}><Text style={styles.historyText}>Redo</Text></Pressable>
        <Pressable style={[styles.historyButton, modelHistoryIndex <= 0 && styles.disabled]} onPress={resetModelEdits} disabled={modelHistoryIndex <= 0}><Text style={styles.historyText}>Reset</Text></Pressable>
      </View>
      {message ? <Text style={styles.message}>{message}</Text> : null}
      {revision?.validation ? (
        <View style={styles.validation}>
          <Text style={styles.validationTitle}>Print validation</Text>
          <Text style={styles.validationText}>{revision.validation.watertight ? 'Watertight mesh' : 'Not watertight'}</Text>
          <Text style={styles.validationText}>{revision.validation.scale_status === 'calibrated' && revision.validation.dimensions_mm ? `W ${revision.validation.dimensions_mm.width} × D ${revision.validation.dimensions_mm.depth} × H ${revision.validation.dimensions_mm.height} mm` : 'Physical dimensions unknown until calibrated'}</Text>
          <Text style={styles.validationText}>Minimum feature thickness: {revision.validation.minimum_feature_thickness_status === 'measured' ? `${revision.validation.minimum_feature_thickness_mm} mm` : 'not measured'}</Text>
          {revision.validation.warnings.map((warning) => <Text key={warning} style={styles.warning}>{warning}</Text>)}
        </View>
      ) : null}
      <Text style={styles.capability}>Feature edits: add/remove base. Holes, handles, and freeform parts are reported as unsupported.</Text>
      <View style={styles.exports}>
        <Pressable style={styles.exportButton} onPress={() => void openExport(revision?.url || generatedModelUrl)}><Text style={styles.exportText}>Export GLB</Text></Pressable>
        {revision?.stlUrl ? <Pressable style={styles.exportButton} onPress={() => void openExport(revision.stlUrl)}><Text style={styles.exportText}>Export STL</Text></Pressable> : null}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  panel: { width: '100%', maxWidth: 420, marginTop: 22, padding: 14, backgroundColor: '#141b34', borderRadius: 8, borderWidth: 1, borderColor: '#26385f' },
  title: { color: '#fff', fontSize: 20, fontWeight: '900', textAlign: 'center' },
  help: { color: '#c8d0e7', textAlign: 'center', marginTop: 6, lineHeight: 19 },
  scalePanel: { marginTop: 12, padding: 10, borderRadius: 8, backgroundColor: '#0b1020' },
  scaleTitle: { color: '#fff', fontWeight: '900', fontSize: 16 },
  calibrated: { color: '#63d69b', marginTop: 4, fontWeight: '800' },
  estimated: { color: '#ffcf70', marginTop: 4, fontWeight: '800' },
  measurementInput: { minHeight: 44, marginTop: 10, paddingHorizontal: 10, borderRadius: 8, backgroundColor: '#141b34', borderWidth: 1, borderColor: '#31456f', color: '#fff' },
  calibrateButton: { minHeight: 44, marginTop: 8, borderRadius: 8, alignItems: 'center', justifyContent: 'center', backgroundColor: '#5b5f97' },
  calibrateText: { color: '#fff', fontWeight: '900' },
  input: { minHeight: 82, marginTop: 12, padding: 12, borderRadius: 8, backgroundColor: '#0b1020', borderWidth: 1, borderColor: '#31456f', color: '#fff', textAlignVertical: 'top' },
  examples: { marginTop: 10, gap: 7 },
  example: { paddingVertical: 9, paddingHorizontal: 10, borderRadius: 8, backgroundColor: '#1d2a4d' },
  exampleText: { color: '#e8edff', textAlign: 'center', fontWeight: '700' },
  apply: { minHeight: 48, marginTop: 12, borderRadius: 8, alignItems: 'center', justifyContent: 'center', backgroundColor: '#18c6d1' },
  applyText: { color: '#071519', fontWeight: '900' },
  disabled: { opacity: 0.4 },
  history: { flexDirection: 'row', gap: 8, marginTop: 10 },
  historyButton: { flex: 1, minHeight: 44, borderRadius: 8, backgroundColor: '#39405a', alignItems: 'center', justifyContent: 'center' },
  historyText: { color: '#fff', fontWeight: '800' },
  message: { color: '#e8edff', textAlign: 'center', marginTop: 12, lineHeight: 19 },
  validation: { marginTop: 12, padding: 10, backgroundColor: '#0b1020', borderRadius: 8 },
  validationTitle: { color: '#fff', fontWeight: '900', marginBottom: 4 },
  validationText: { color: '#d9e2f7', marginTop: 2 },
  warning: { color: '#ffcf70', marginTop: 5 },
  capability: { color: '#9ba7c5', textAlign: 'center', fontSize: 12, lineHeight: 17, marginTop: 12 },
  exports: { flexDirection: 'row', gap: 8, marginTop: 12 },
  exportButton: { flex: 1, minHeight: 46, borderRadius: 8, backgroundColor: '#5b5f97', alignItems: 'center', justifyContent: 'center' },
  exportText: { color: '#fff', fontWeight: '900' },
});
