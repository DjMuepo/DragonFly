import { View, Text, StyleSheet, Pressable, ActivityIndicator, Image } from 'react-native';
import { useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import { useSnapStore } from '../../src/lib/useSnapStore';
import { draftPhoto, previewPhoto, geometryPreviewPhoto, reconstructPhoto, reconstructPhotoSet, logEvent, applyLearnedDefaults } from '../../src/lib/api';

export default function DraftModel() {
  const router = useRouter();
  const heroUri = useSnapStore((s) => s.heroUri);
  const sessionId = useSnapStore((s:any) => s.sessionId);
  const burstUris = useSnapStore((s:any) => s.burstUris);
  const captureMode = useSnapStore((s:any) => s.captureMode);
  const setVisionDraft = useSnapStore((s) => (s as any).setVisionDraft);
  const setVisionReconstruct = useSnapStore((s) => (s as any).setVisionReconstruct);
  const visionReconstruct = useSnapStore((s) => (s as any).visionReconstruct);
  const visionPreviewUrl = useSnapStore((s) => (s as any).visionPreviewUrl);
  const setVisionPreviewUrl = useSnapStore((s) => (s as any).setVisionPreviewUrl);
  const visionDraft = useSnapStore((s) => (s as any).visionDraft);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let alive = true;
    (async () => {
      if (!heroUri || visionDraft) return;
      try {
        setLoading(true);
        const d = await previewPhoto(heroUri);
        if (!alive) return;
        const g = await geometryPreviewPhoto(heroUri);
        if (!alive) return;
        const r = captureMode === 'multi' && burstUris?.length ? await reconstructPhotoSet([heroUri, ...burstUris]) : await reconstructPhoto(heroUri);
        if (!alive) return;
        setVisionReconstruct(r);
        setVisionDraft({ classification: d.classification, draft: d.draft, geometry: g.geometry, parametric: r.parametric_draft });
        setVisionPreviewUrl((process.env.EXPO_PUBLIC_API_BASE || 'http://localhost:8000').replace(/\/$/, '') + d.preview_url);
      } catch (e) {
        // ignore
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => { alive = false; };
  }, [heroUri]);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>One-snap Draft</Text>
      <Text style={styles.subtitle}>
        We’ll generate a printable draft even with one photo. The back side may be estimated.
      </Text>

      <View style={styles.panel}>
        <Text style={styles.panelTitle}>Draft summary</Text>
        {loading ? <ActivityIndicator /> : null}
        {visionPreviewUrl ? <Image source={{ uri: visionPreviewUrl }} style={{ width: '100%', height: 220, borderRadius: 14, marginBottom: 12, borderWidth: 1, borderColor: '#1f1f1f' }} resizeMode='contain' /> : null}
        {visionReconstruct?.parametric_draft ? (
          <>
            <Text style={[styles.panelHint, { marginBottom: 6 }]}>Parametric family draft: <Text style={{ color: '#fff', fontWeight: '800' }}>{visionReconstruct.family}</Text></Text>
            <Text style={styles.panelHint}>Supported family: <Text style={{ color: '#fff', fontWeight: '800' }}>{visionReconstruct.supported_family ? 'Yes' : 'Limited fallback'}</Text></Text>
            <Text style={styles.panelHint}>Draft confidence: <Text style={{ color: '#fff', fontWeight: '800' }}>{Math.round((visionReconstruct.parametric_draft.confidence || 0) * 100)}%</Text></Text>
            {visionReconstruct.views_used ? <Text style={styles.panelHint}>Views used: <Text style={{ color: '#fff', fontWeight: '800' }}>{visionReconstruct.views_used}</Text></Text> : null}
          </>
        ) : null}
        {visionDraft?.classification ? (
          <>
            <Text style={styles.panelHint}>Detected family: <Text style={{ color: '#fff', fontWeight: '800' }}>{visionDraft.classification.object_family}</Text></Text>
            <Text style={styles.panelHint}>Draft strategy: <Text style={{ color: '#fff', fontWeight: '800' }}>{visionDraft.draft.strategy}</Text></Text>
            <Text style={styles.panelHint}>Estimated depth ratio: <Text style={{ color: '#fff', fontWeight: '800' }}>{visionDraft.draft.estimated_depth_ratio}</Text></Text>
            <Text style={styles.panelHint}>Draft confidence: <Text style={{ color: '#fff', fontWeight: '800' }}>{Math.round((visionDraft.draft.confidence || 0) * 100)}%</Text></Text>
          </>
        ) : (
          <>
            <Text style={styles.panelHint}>You can adjust these in Edit next:</Text>
            <Text style={styles.bullet}>• Thickness</Text>
            <Text style={styles.bullet}>• Height</Text>
            <Text style={styles.bullet}>• Roundness</Text>
          </>
        )}
      </View>

      <View style={[styles.panel, { gap: 10 }]}> 
        <Text style={styles.panelTitle}>Was this draft close?</Text>
        <View style={{ flexDirection: 'row', gap: 10 }}>
          <Pressable style={[styles.secondary, { flex: 1 }]} onPress={() => logEvent({ event: 'draft_accept', session_id: sessionId, payload: { family: visionReconstruct?.family, confidence: visionReconstruct?.parametric_draft?.confidence } })}><Text style={styles.secondaryText}>👍 Good draft</Text></Pressable>
          <Pressable style={[styles.secondary, { flex: 1 }]} onPress={() => logEvent({ event: 'draft_reject', session_id: sessionId, payload: { family: visionReconstruct?.family, confidence: visionReconstruct?.parametric_draft?.confidence } })}><Text style={styles.secondaryText}>👎 Needs work</Text></Pressable>
        </View>
      </View>

      {visionReconstruct?.parametric_draft?.learned_defaults ? <View style={styles.panel}>
        <Text style={styles.panelTitle}>Learned Defaults Applied</Text>
        <Text style={styles.panelHint}>Min thickness: <Text style={{ color: '#fff', fontWeight: '800' }}>{visionReconstruct.parametric_draft.learned_defaults.min_thickness ?? 'n/a'}</Text></Text>
        <Text style={styles.panelHint}>Preferred material: <Text style={{ color: '#fff', fontWeight: '800' }}>{visionReconstruct.parametric_draft.learned_defaults.preferred_material || 'PLA'}</Text></Text>
        <Text style={styles.panelHint}>Reinforcement bias: <Text style={{ color: '#fff', fontWeight: '800' }}>{visionReconstruct.parametric_draft.learned_defaults.reinforcement_bias ?? 0}</Text></Text>
      </View> : null}

      <View style={[styles.panel, { gap: 10 }]}>
        <Text style={styles.panelTitle}>Learning Tools</Text>
        <View style={{ flexDirection: 'row', gap: 10 }}>
          <Pressable style={[styles.secondary, { flex: 1 }]} onPress={async () => {
            try {
              const r = await applyLearnedDefaults(visionReconstruct?.parametric_draft);
              setVisionReconstruct({ ...(visionReconstruct || {}), parametric_draft: r.parametric_draft, learning_applied: true });
            } catch (e) {
              console.warn('apply learned defaults failed', e);
            }
          }}><Text style={styles.secondaryText}>Apply learned defaults</Text></Pressable>
          <Pressable style={[styles.secondary, { flex: 1 }]} onPress={() => router.push('/training/insights' as any)}><Text style={styles.secondaryText}>Training insights</Text></Pressable>
        </View>
      </View>

      <View style={styles.actions}>
        <Pressable style={styles.secondary} onPress={() => router.push('/snap/suggested-actions')}>
          <Text style={styles.secondaryText}>Edit more actions?</Text>
        </Pressable>
        <Pressable style={styles.secondary} onPress={() => router.push('/snap/rotatable')}>
          <Text style={styles.secondaryText}>Open rotatable preview</Text>
        </Pressable>
        <Pressable style={styles.primary} onPress={() => router.push('/snap/edit?mode=unique')}>
          <Text style={styles.primaryText}>Continue</Text>
        </Pressable>
        <Pressable style={styles.secondary} onPress={() => router.push('/snap/camera')}>
          <Text style={styles.secondaryText}>Boost accuracy (optional): retake</Text>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#000', padding: 16, gap: 12 },
  title: { color: '#fff', fontSize: 24, fontWeight: '800' },
  subtitle: { color: '#bdbdbd', fontSize: 13, lineHeight: 18 },
  panel: {
    borderWidth: 1,
    borderColor: '#1f1f1f',
    backgroundColor: '#0b0b0b',
    borderRadius: 18,
    padding: 14,
    gap: 6,
  },
  panelTitle: { color: '#fff', fontSize: 16, fontWeight: '700' },
  panelHint: { color: '#bdbdbd', fontSize: 12 },
  bullet: { color: '#fff', opacity: 0.9 },
  actions: { marginTop: 'auto', gap: 10, paddingBottom: 8 },
  primary: { backgroundColor: '#fff', borderRadius: 14, paddingVertical: 14, alignItems: 'center' },
  primaryText: { color: '#000', fontWeight: '800', fontSize: 16 },
  secondary: { borderRadius: 14, paddingVertical: 14, alignItems: 'center', borderWidth: 1, borderColor: '#2a2a2a' },
  secondaryText: { color: '#fff', fontWeight: '700', fontSize: 14 },
});
