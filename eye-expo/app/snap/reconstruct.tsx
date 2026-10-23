import { Alert, Platform, View, Text, StyleSheet, Image, Pressable, ActivityIndicator, ScrollView } from 'react-native';
import { useRouter } from 'expo-router';
import { useEffect, useRef, useState } from 'react';
import { useSnapStore } from '../../src/lib/useSnapStore';
import { revisionFromResult } from '../../src/lib/revisionFromResult';
import { ProjectPanel } from '../../src/components/ProjectPanel';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { findGeometryJobByKey, generateGeometryFromImage, GeometryJobFailed, newIdempotencyKey, resumeGeometryJob } from '../../src/lib/geometryApi';
import { reconstructionRecovery, requiresPaidRetryConfirmation } from '../../src/lib/betaRecovery';

export default function ReconstructScreen() {
  const router = useRouter();
  const heroUri = useSnapStore((s) => s.heroUri);
  const cutoutUri = useSnapStore((s) => s.cutoutUri);
  const targetLabel = useSnapStore((s) => s.targetLabel);
  const clear = useSnapStore((s) => s.clear);
  const setGeneratedModel = useSnapStore((s) => s.setGeneratedModel);
  const setGeneratedExport = useSnapStore((s) => s.setGeneratedExport);
  const setReconstructionDetails = useSnapStore((s) => s.setReconstructionDetails);
  const reconstructionWarnings = useSnapStore((s) => s.reconstructionWarnings);
  const initializeModelHistory = useSnapStore((s) => s.initializeModelHistory);
  const setJobResultLinks = useSnapStore((s) => s.setJobResultLinks);
  const setProject = useSnapStore((s) => s.setProject);
  const geometryJobId = useSnapStore((s) => s.geometryJobId);
  const geometryIdempotencyKey = useSnapStore((s) => s.geometryIdempotencyKey);
  const setGeometryJobId = useSnapStore((s) => s.setGeometryJobId);
  const setGeometryIdempotencyKey = useSnapStore((s) => s.setGeometryIdempotencyKey);
  const hasHydrated = useSnapStore((s) => s.hasHydrated);
  const authToken = useSnapStore((s) => s.authToken);
  const imageUri = cutoutUri || heroUri;

  const [stage, setStage] = useState<'building' | 'ready' | 'error'>('building');
  const [error, setError] = useState<string | null>(null);
  const [uncertainOutcome, setUncertainOutcome] = useState(false);
  const [modelName, setModelName] = useState<string | null>(null);
  const [engine, setEngine] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [qualityMode, setQualityMode] = useState<'FAST' | 'STANDARD' | 'HIGH_QUALITY'>('STANDARD');
  const [activeQualityMode, setActiveQualityMode] = useState<'FAST' | 'STANDARD' | 'HIGH_QUALITY'>('STANDARD');
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [stageDetail, setStageDetail] = useState('');
  const [attempt, setAttempt] = useState(0);
  const activeJobId = useRef<string | null>(null);

  useEffect(() => {
    let alive = true;

    async function run() {
      let savedJobId = useSnapStore.getState().geometryJobId;
      let savedKey = useSnapStore.getState().geometryIdempotencyKey;
      let savedImageUri = imageUri;
      if (!savedJobId && !savedKey) {
        try {
          const pending = await AsyncStorage.getItem('dragonfly.pending-reconstruction');
          if (pending) {
            const parsed = JSON.parse(pending);
            savedJobId = parsed.jobId || undefined;
            savedKey = parsed.idempotencyKey || undefined;
            savedImageUri = savedImageUri || parsed.imageUri || undefined;
            setGeometryIdempotencyKey(savedKey);
            setGeometryJobId(savedJobId);
          }
        } catch {
          setError('A saved reconstruction request could not be restored. Start a new scan.');
        }
      }
      if (!savedJobId && savedKey) {
        const accepted = await findGeometryJobByKey(savedKey);
        if (accepted) {
          savedJobId = accepted.job_id;
          setGeometryJobId(savedJobId);
        }
      }
      if (!savedImageUri && !savedJobId) {
        setStage('error');
        setError('No image found. Start a new scan and try again.');
        return;
      }

      try {
        setStage('building');
        setError(null);
        setProgress(0);
        setEngine(null);
        setStageDetail('');
        activeJobId.current = savedJobId || null;
        setGeneratedModel(undefined, undefined);
        setGeneratedExport(undefined, undefined);
        setReconstructionDetails(undefined, undefined, undefined);
        setJobResultLinks(undefined, undefined);
        const onProgress = (job: Parameters<typeof resumeGeometryJob>[1] extends ((value: infer J) => void) | undefined ? J : never) => {
          activeJobId.current = job.job_id;
          setGeometryJobId(job.job_id);
          if (alive) {
            setProgress(job.progress);
            setEngine(`${job.provider} (${job.provider_kind})`);
            setStageDetail(job.stage_detail || '');
          }
        };
        const recovery = reconstructionRecovery({ jobId: savedJobId, idempotencyKey: savedKey, serverJobAccepted: !!savedJobId });
        let result;
        if (recovery.action === 'resume-job') {
          result = await resumeGeometryJob(recovery.jobId, onProgress);
        } else if (recovery.action === 'resume-accepted') {
          const accepted = await findGeometryJobByKey(recovery.idempotencyKey);
          if (!accepted) throw new Error('The accepted job could not be found. Keep this request and retry status lookup.');
          result = await resumeGeometryJob(accepted.job_id, onProgress);
        } else {
          const idempotencyKey = recovery.action === 'submit-same-key' ? recovery.idempotencyKey : newIdempotencyKey();
          setGeometryIdempotencyKey(idempotencyKey);
          result = await generateGeometryFromImage({
              imageUri: savedImageUri,
              label: targetLabel || 'Object',
              confidence: 0.7,
              qualityMode: activeQualityMode,
              idempotencyKey,
              onProgress,
            });
        }
        if (!alive) return;

        setGeneratedModel(result.model_url, result.model_name);
        setGeneratedExport(result.stl_download_url, result.provider_kind);
        const warnings = result.reconstruction_quality ? [...result.reconstruction_quality.warnings, result.reconstruction_quality.limitation] : [];
        setReconstructionDetails(result.quality_mode, result.preprocessing, result.hidden_surface_uncertainty, warnings);
        initializeModelHistory({ ...revisionFromResult(result), summary: 'Original reconstructed model' });
        setProject(result.project_id, targetLabel || 'Object');
        setGeometryJobId(undefined);
        setGeometryIdempotencyKey(undefined);
        setJobResultLinks(result.model_url, result.download_url);
        setModelName(result.model_name);
        setEngine(`${result.engine} (${result.provider_kind})`);
        setStage('ready');
      } catch (err: any) {
        if (!alive) return;
        if (err instanceof GeometryJobFailed) {
          const uncertain = requiresPaidRetryConfirmation(err.code, err.providerKind);
          setUncertainOutcome(uncertain);
          if (!uncertain) {
            setGeometryJobId(undefined);
            setGeometryIdempotencyKey(undefined);
          }
        }
        setGeneratedModel(undefined, undefined);
        setGeneratedExport(undefined, undefined);
        setReconstructionDetails(undefined, undefined, undefined);
        setJobResultLinks(undefined, undefined);
        const message = err?.message || '3D generation failed. Check your connection and try again.';
        setError(activeJobId.current && !message.includes(activeJobId.current) ? `Generation failed — Job DF-${activeJobId.current}: ${message}` : message);
        setStage('error');
      }
    }

    run();

    return () => {
      alive = false;
    };
  }, [attempt, imageUri, targetLabel, activeQualityMode, hasHydrated, authToken, setGeneratedModel, setGeneratedExport, setReconstructionDetails, initializeModelHistory, setJobResultLinks, setProject, setGeometryJobId, setGeometryIdempotencyKey]);

  if (!imageUri && !geometryJobId) {
    return (
      <View style={styles.center}>
        <Text>No image found.</Text>
      </View>
    );
  }

  const retryGeneration = () => {
    if (!uncertainOutcome) {
      setAttempt((value) => value + 1);
      return;
    }
    const startNewAttempt = () => {
      setUncertainOutcome(false);
      setGeometryJobId(undefined);
      setGeometryIdempotencyKey(undefined);
      void AsyncStorage.removeItem('dragonfly.pending-reconstruction');
      setAttempt((value) => value + 1);
    };
    const title = 'Provider outcome is uncertain';
    const warning = 'The previous request may still have incurred an AI charge. Starting again may create a second prediction.';
    if (Platform.OS === 'web' && typeof window !== 'undefined') {
      if (window.confirm(`${title}\n\n${warning}`)) startNewAttempt();
      return;
    }
    Alert.alert(title, warning, [
      { text: 'Keep current request', style: 'cancel' },
      { text: 'Start a new attempt', style: 'destructive', onPress: startNewAttempt },
    ]);
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.title}>Generating 3D</Text>
      {imageUri ? <Image source={{ uri: imageUri }} style={styles.image} /> : <Text style={styles.note}>Reconnecting to the existing reconstruction job...</Text>}
      <Text style={styles.objectLabel}>Object: {targetLabel || 'Unknown object'}</Text>

      <Pressable style={styles.advancedToggle} onPress={() => setShowAdvanced((value) => !value)}>
        <Text style={styles.advancedText}>{showAdvanced ? 'Hide' : 'Advanced'} image preparation</Text>
      </Pressable>
      {showAdvanced ? (
        <>
          <View style={styles.qualityOptions}>
            {(['FAST', 'STANDARD', 'HIGH_QUALITY'] as const).map((mode) => (
              <Pressable key={mode} style={[styles.qualityButton, qualityMode === mode && styles.qualitySelected]} onPress={() => setQualityMode(mode)}>
                <Text style={styles.qualityText}>{mode === 'HIGH_QUALITY' ? 'HIGH QUALITY' : mode}</Text>
              </Pressable>
            ))}
          </View>
          {stage !== 'building' ? (
            <Pressable style={styles.qualityRegenerate} onPress={() => { setActiveQualityMode(qualityMode); setAttempt((value) => value + 1); }}>
              <Text style={styles.qualityRegenerateText}>Regenerate at this quality</Text>
            </Pressable>
          ) : null}
        </>
      ) : null}

      {stage === 'building' ? (
        <>
          <ActivityIndicator size="large" />
          <Text style={styles.status}>{engine ? `Generating with ${engine}: ${progress}%` : 'Preparing photo...'}</Text>
          {stageDetail ? <Text style={styles.note}>{stageDetail}</Text> : null}
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
            <Pressable style={styles.primaryButton} onPress={retryGeneration}>
              <Text style={styles.buttonText}>{uncertainOutcome ? 'Start a new AI attempt' : 'Try Again'}</Text>
            </Pressable>
            <Pressable style={styles.darkButton} onPress={() => router.push('/snap/camera')}>
              <Text style={styles.buttonText}>Retake Photo</Text>
            </Pressable>
          </View>
        </>
      ) : (
        <>
          <View style={styles.readyCard}>
            <Text style={styles.readyTitle}>3D Model Ready for Review</Text>
            <Text style={styles.readyText}>Compare the reconstructed shape with your photo before accepting it.</Text>
            {reconstructionWarnings.map((warning) => <Text key={warning} style={styles.warning}>{warning}</Text>)}
            {modelName ? <Text style={styles.readySubtext}>Model: {modelName}</Text> : null}
            {engine ? <Text style={styles.readySubtext}>Engine: {engine}</Text> : null}
          </View>
          <ProjectPanel refresh={false} />
          <View style={styles.actions}>
            <Pressable style={styles.primaryButton} onPress={() => router.push('/snap/viewer')}>
              <Text style={styles.buttonText}>View 3D</Text>
            </Pressable>
            <Pressable style={styles.secondaryButton} onPress={() => router.push('/snap/result')}>
              <Text style={styles.buttonText}>Save / Finish</Text>
            </Pressable>
            {reconstructionWarnings.length ? <Pressable style={styles.darkButton} onPress={() => router.push('/snap/camera')}><Text style={styles.buttonText}>Retake Photo</Text></Pressable> : null}

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
  advancedToggle: { width: '100%', maxWidth: 300, minHeight: 42, justifyContent: 'center', alignItems: 'center', marginBottom: 8 },
  advancedText: { color: '#5b5f97', fontWeight: '800' },
  qualityOptions: { width: '100%', maxWidth: 340, flexDirection: 'row', gap: 6, marginBottom: 10 },
  qualityButton: { flex: 1, paddingVertical: 10, paddingHorizontal: 4, alignItems: 'center', borderRadius: 8, backgroundColor: '#eef0f6' },
  qualitySelected: { backgroundColor: '#b8f1f2', borderWidth: 1, borderColor: '#18a8b2' },
  qualityText: { color: '#202436', fontSize: 11, fontWeight: '900' },
  qualityRegenerate: { width: '100%', maxWidth: 340, minHeight: 42, justifyContent: 'center', alignItems: 'center', marginBottom: 10, borderRadius: 8, backgroundColor: '#253b47' },
  qualityRegenerateText: { color: '#fff', fontWeight: '800' },
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
