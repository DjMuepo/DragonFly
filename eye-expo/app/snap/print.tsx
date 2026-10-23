import * as React from 'react';
import { View, Text, StyleSheet, Pressable, Linking } from 'react-native';
import { useRouter } from 'expo-router';
import { useSnapStore } from '../../src/lib/useSnapStore';
import { logEvent, exportDraftStl, analyzePrintability, publishDesign, hostDesignPreview } from '../../src/lib/api';

export default function PrintReady() {
  const router = useRouter();
  const sessionId = useSnapStore((s) => (s as any).sessionId);
  const selectedMatchId = useSnapStore((s) => s.selectedMatchId);
  const structuralReport = useSnapStore((s) => (s as any).structuralReport);
  const visionReconstruct = useSnapStore((s) => (s as any).visionReconstruct);
  const [exportState, setExportState] = React.useState<any>(null);
  const [printability, setPrintability] = React.useState<any>(null);
  const [printabilityError] = React.useState<string | null>('Slicer-based printability analysis is unavailable. No check was run.');
  const [exportError, setExportError] = React.useState<string | null>(null);
  const [shareError, setShareError] = React.useState<string | null>(null);
  const setSharedDesign = useSnapStore((s:any) => s.setSharedDesign);
  const userProfile = useSnapStore((s:any) => s.userProfile);
  const authToken = useSnapStore((s:any) => s.authToken);
  const currentUser = useSnapStore((s:any) => s.currentUser);
  const [shareState, setShareState] = React.useState<any>(null);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Print Preparation Preview</Text>
      <Text style={styles.subtitle}>Draft-only heuristic checks; slicer validation, print estimates and 3MF export are not integrated.</Text>

      <View style={styles.panel}>
        <Text style={styles.row}><Text style={styles.label}>Draft heuristic: </Text><Text style={styles.value}>{printability ? `${printability.print_confidence}% (${printability.band})` : 'Unavailable'}</Text></Text>
        <Text style={styles.row}><Text style={styles.label}>Print time: </Text><Text style={styles.value}>Not measured</Text></Text>
        {printability?.recommended_material ? <Text style={styles.row}><Text style={styles.label}>Suggested material: </Text><Text style={styles.value}>{printability.recommended_material}</Text></Text> : null}
        {printabilityError ? <Text accessibilityRole="alert" style={styles.error}>{printabilityError}</Text> : null}
      </View>


      <View style={styles.panel}>
        <Text style={[styles.row, { fontWeight: '800' }]}>Review & Grade</Text>
            <Text style={styles.subtitle}>Feedback collection is unavailable; no event will be recorded.</Text>

        <View style={{ flexDirection: 'row', gap: 10, marginTop: 8 }}>
          <Pressable
            disabled
            style={[styles.secondary, { flex: 1, borderWidth: 1, borderColor: '#2a2a2a', backgroundColor: '#0b0b0b' }]}
            onPress={() => logEvent({ event: 'useful_yes', session_id: sessionId, model_id: selectedMatchId ?? undefined, payload: { confidence: structuralReport?.confidence } })}
          >
            <Text style={styles.secondaryText}>👍 Helpful</Text>
          </Pressable>
          <Pressable
            disabled
            style={[styles.secondary, { flex: 1, borderWidth: 1, borderColor: '#2a2a2a', backgroundColor: '#0b0b0b' }]}
            onPress={() => logEvent({ event: 'useful_no', session_id: sessionId, model_id: selectedMatchId ?? undefined, payload: { confidence: structuralReport?.confidence } })}
          >
            <Text style={styles.secondaryText}>👎 Not helpful</Text>
          </Pressable>
        </View>

        <Text style={[styles.row, { marginTop: 12 }]}><Text style={styles.label}>Self-reported print outcome:</Text></Text>
        <View style={{ flexDirection: 'row', gap: 10, marginTop: 8 }}>
          <Pressable
            disabled
            style={[styles.secondary, { flex: 1, borderWidth: 1, borderColor: '#2a2a2a', backgroundColor: '#0b0b0b' }]}
            onPress={() => logEvent({ event: 'print_outcome_success', session_id: sessionId, model_id: selectedMatchId ?? undefined, payload: { confidence: structuralReport?.confidence } })}
          >
            <Text style={styles.secondaryText}>I printed successfully</Text>
          </Pressable>
          <Pressable
            disabled
            style={[styles.secondary, { flex: 1, borderWidth: 1, borderColor: '#2a2a2a', backgroundColor: '#0b0b0b' }]}
            onPress={() => logEvent({ event: 'print_outcome_fail', session_id: sessionId, model_id: selectedMatchId ?? undefined, payload: { confidence: structuralReport?.confidence } })}
          >
            <Text style={styles.secondaryText}>My print failed</Text>
          </Pressable>
        </View>

        <Pressable
          disabled
          style={[styles.secondary, { marginTop: 10, borderWidth: 1, borderColor: '#2a2a2a', backgroundColor: '#0b0b0b' }]}
          onPress={() => router.push('/snap/feedback')}
        >
          <Text style={styles.secondaryText}>Leave a review (optional)</Text>
        </Pressable>
      </View>


      {printability ? <View style={styles.panel}>
        <Text style={[styles.row, { fontWeight: '800' }]}>Printability Analyzer</Text>
        {printability.suggestions?.map((s:any, i:number) => <Text key={i} style={styles.row}>• {s}</Text>)}
        {printability.risks?.length ? <Text style={[styles.row, { marginTop: 8 }]}><Text style={styles.label}>Risks: </Text><Text style={styles.value}>{printability.risks.join(', ')}</Text></Text> : null}
      </View> : null}

      <View style={styles.panel}>
        <Text style={[styles.row, { fontWeight: '800' }]}>STL Export</Text>
        <Text style={styles.subtitle}>Export a parametric draft STL. This is separate from any reconstructed GLB.</Text>
        <Pressable
          disabled
          style={[styles.primary, { marginTop: 10 }]}
          onPress={async () => {
            try {
              const res = await exportDraftStl(visionReconstruct?.parametric_draft);
              setExportState(res);
              setExportError(null);
              logEvent({ event: 'stl_export', session_id: sessionId, model_id: selectedMatchId ?? undefined, payload: { family: visionReconstruct?.family, watertight: res?.meta?.is_watertight, faces: res?.meta?.faces } });
            } catch (e) {
              console.warn('stl export failed', e);
              setExportError('STL export is unavailable from this service. No file was created.');
            }
          }}
        >
          <Text style={styles.primaryText}>Parametric STL export unavailable</Text>
        </Pressable>
        {exportState ? <Text style={[styles.row, { marginTop: 10 }]}><Text style={styles.label}>Watertight: </Text><Text style={styles.value}>{exportState.meta?.is_watertight ? 'Yes' : 'Needs review'}</Text></Text> : null}
        {exportState ? <Text style={styles.row}><Text style={styles.label}>Faces: </Text><Text style={styles.value}>{exportState.meta?.faces}</Text></Text> : null}
        {exportState ? <Text style={styles.row}><Text style={styles.label}>STL URL: </Text><Text style={styles.value}>{exportState.download_url}</Text></Text> : null}
        {exportError ? <Text accessibilityRole="alert" style={styles.error}>{exportError}</Text> : null}
        {exportState?.download_url ? <Pressable style={[styles.secondary, { marginTop: 8 }]} onPress={async () => { try { await Linking.openURL(exportState.download_url); } catch { setExportError('Could not open the returned STL URL.'); } }}><Text style={styles.secondaryText}>Download STL</Text></Pressable> : null}
      </View>

      <View style={styles.panel}>
        <Text style={[styles.row, { fontWeight: '800' }]}>Nearby printing</Text>
        <Text style={styles.subtitle}>Printer discovery and ordering are unavailable in this deployment.</Text>
        <Pressable disabled style={[styles.primary, { marginTop: 10 }]}>
          <Text style={styles.primaryText}>Printer service unavailable</Text>
        </Pressable>
      </View>

      <View style={styles.panel}>
        <Text style={[styles.row, { fontWeight: '800' }]}>Share Design</Text>
        <Text style={styles.subtitle}>Public sharing is unavailable in this deployment. No design will be published.</Text>
        <Pressable
          disabled
          style={[styles.primary, { marginTop: 10 }]}
          onPress={async () => {
            try {
              setShareError(null);
              const res = await publishDesign({
                title: `${visionReconstruct?.family || 'Design'} Concept`,
                description: `Shared from the AI-guided design workflow.`,
                creator: currentUser?.name || userProfile?.name || 'Anonymous',
                owner_id: currentUser?.id,
                family: visionReconstruct?.family || 'object',
                print_confidence: printability?.print_confidence,
                is_public: true,
                tags: userProfile?.interests || [],
                preview_url: undefined,
                stl_url: exportState?.download_url,
              });
              try { const hosted = await hostDesignPreview(res.design.slug); res.design.preview_url = hosted.preview_url || res.design.preview_url; } catch {}
              setSharedDesign(res.design);
              setShareState(res);
              logEvent({ event: 'design_publish', session_id: sessionId, payload: { slug: res.design?.slug, family: visionReconstruct?.family } });
            } catch (e) {
              console.warn('design publish failed', e);
              setShareError('Sharing is unavailable. No design was published.');
            }
          }}
        >
          <Text style={styles.primaryText}>Sharing service unavailable</Text>
        </Pressable>
        {shareError ? <Text accessibilityRole="alert" style={styles.error}>{shareError}</Text> : null}
        {shareState ? <Text style={[styles.row, { marginTop: 10 }]}><Text style={styles.label}>Share page: </Text><Text style={styles.value}>{shareState.share_url}</Text></Text> : null}
        {shareState ? <Text style={styles.row}><Text style={styles.label}>App link: </Text><Text style={styles.value}>{shareState.app_deep_link}</Text></Text> : null}
        {shareState?.design?.preview_url ? <Text style={styles.row}><Text style={styles.label}>Preview URL: </Text><Text style={styles.value}>{shareState.design.preview_url}</Text></Text> : null}
        {shareState ? <Pressable style={[styles.secondary, { marginTop: 10 }]} onPress={() => router.push(`/design/${shareState.design.slug}` as any)}><Text style={styles.secondaryText}>Open design page</Text></Pressable> : null}
      </View>

      <View style={styles.actions}>
        <Pressable style={styles.secondary} onPress={() => router.replace('/home')}>
          <Text style={styles.secondaryText}>Done</Text>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#000', padding: 16, gap: 12 },
  title: { color: '#fff', fontSize: 24, fontWeight: '800' },
  subtitle: { color: '#bdbdbd', fontSize: 13, lineHeight: 18 },
  error: { color: '#ffb1a8', fontSize: 13, lineHeight: 18 },
  panel: {
    borderWidth: 1,
    borderColor: '#1f1f1f',
    backgroundColor: '#0b0b0b',
    borderRadius: 18,
    padding: 14,
    gap: 8,
  },
  row: { color: '#fff' },
  label: { color: '#bdbdbd' },
  value: { color: '#fff', fontWeight: '800' },
  actions: { marginTop: 'auto', gap: 10, paddingBottom: 8 },
  primary: { backgroundColor: '#fff', borderRadius: 14, paddingVertical: 14, alignItems: 'center' },
  primaryText: { color: '#000', fontWeight: '800', fontSize: 16 },
  secondary: { borderRadius: 14, paddingVertical: 14, alignItems: 'center', borderWidth: 1, borderColor: '#2a2a2a' },
  secondaryText: { color: '#fff', fontWeight: '700', fontSize: 16 },
});
