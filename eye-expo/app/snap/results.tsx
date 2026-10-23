import { useEffect, useMemo, useState } from 'react';
import { View, Text, StyleSheet, FlatList, Pressable, ActivityIndicator, Linking } from 'react-native';
import { useRouter } from 'expo-router';
import { MatchCandidate, useSnapStore } from '../../src/lib/useSnapStore';
import LicenseBadge from '../../src/components/LicenseBadge';
import ConfidenceBadge from '../../src/components/ConfidenceBadge';
import { getJob, classifyPhoto, retrievePhoto, classifyPhotoSet, retrievePhotoSet } from '../../src/lib/api';

export default function Results() {
  const router = useRouter();
  const heroUri = useSnapStore((s) => s.heroUri);
  const burstUris = useSnapStore((s:any) => s.burstUris);
  const captureMode = useSnapStore((s:any) => s.captureMode);
  const matches = useSnapStore((s) => s.matches);
  const novelty = useSnapStore((s) => s.novelty);
  const setMatches = useSnapStore((s) => s.setMatches);
  const selectMatch = useSnapStore((s) => s.selectMatch);
  const jobId = useSnapStore((s) => s.jobId);
  const jobStatus = useSnapStore((s) => s.jobStatus);
  const setJobStatus = useSnapStore((s) => s.setJobStatus);
  const setJobResultLinks = useSnapStore((s) => s.setJobResultLinks);
  const setVisionClassify = useSnapStore((s) => (s as any).setVisionClassify);
  const visionClassify = useSnapStore((s) => (s as any).visionClassify);

  const [loading, setLoading] = useState(true);
  const [serviceError, setServiceError] = useState<string | null>(null);
  const canPoll = useMemo(() => !!jobId, [jobId]);

  useEffect(() => {
    let alive = true;

    const runVision = async () => {
      if (!heroUri) {
        setServiceError('No similarity search was performed. Generate a model from the current photo instead.');
        if (alive) setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setServiceError(null);
        const cls = captureMode === 'multi' && burstUris?.length ? await classifyPhotoSet([heroUri, ...burstUris]) : await classifyPhoto(heroUri);
        if (!alive) return;
        setVisionClassify(cls);

        const r = captureMode === 'multi' && burstUris?.length ? await retrievePhotoSet([heroUri, ...burstUris], 8) : await retrievePhoto(heroUri, 8);
        if (!alive) return;
        if (r?.matches && r?.novelty) {
          const mapped = r.matches.map((m: any) => ({
            id: m.id,
            title: m.title,
            similarity: m.similarity,
            license: m.license?.status ?? m.license ?? 'UNKNOWN',
            hosted: m.hosted ?? true,
            externalUrl: m.external_url ?? m.externalUrl,
            previewUrl: m.preview_url ?? m.previewUrl,
          }));
          setMatches(mapped as MatchCandidate[], r.novelty);
        }
      } catch (e) {
        console.warn('vision error', e);
        setServiceError('Similar-design search is unavailable in this deployment. No sample matches or license claims are shown.');
      } finally {
        if (alive) setLoading(false);
      }
    };

    runVision();
    return () => { alive = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [heroUri]);

  const onUseBest = () => {
    const best = [...matches].sort((a, b) => b.similarity - a.similarity)[0];
    if (best) {
      selectMatch(best.id);
      router.push('/snap/edit');
    }
  };

  const onMakeNew = () => router.push('/snap/draft');

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Matches</Text>
      {visionClassify ? <><Text style={[styles.subtitle, { marginBottom: 4 }]}>We think this is a <Text style={{ color: '#fff', fontWeight: '800' }}>{visionClassify.object_family}</Text> • {Math.round((visionClassify.confidence || 0) * 100)}% confidence</Text><Pressable style={styles.fixBtn} onPress={() => router.push('/snap/family-correction')}><Text style={styles.fixBtnText}>Wrong object?</Text></Pressable></> : null}
      <Text style={styles.subtitle}>
        {loading ? 'Checking for connected search service…' : serviceError || 'Search results are unavailable.'}
      </Text>

      <View style={styles.badges}>
        {novelty ? <ConfidenceBadge novelty={novelty} /> : null}
        {loading && (
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
            <ActivityIndicator />
            <Text style={{ color: '#bdbdbd', fontSize: 12 }}>
              {jobStatus === 'uploaded' ? 'Processing…' : jobStatus ? jobStatus : 'Loading…'}
            </Text>
          </View>
        )}
      </View>

      <FlatList
        data={matches}
        keyExtractor={(i) => i.id}
        contentContainerStyle={{ gap: 10, paddingBottom: 14 }}
        renderItem={({ item }) => (
          <Pressable style={styles.card} onPress={() => {
              selectMatch(item.id);
              if (item.hosted === false && item.externalUrl) {
                Linking.openURL(item.externalUrl);
              } else {
                router.push('/snap/edit');
              }
            }}>
            <View style={styles.cardTop}>
              <Text style={styles.cardTitle}>{item.title}</Text>
              <Text style={styles.sim}>{Math.round(item.similarity * 100)}%</Text>
            </View>
            <View style={styles.cardBottom}>
              <LicenseBadge status={item.license} />
              <Text style={styles.cardHint}>{item.hosted === false ? 'Opens external source' : 'Tap to edit this model'}</Text>
            </View>
          </Pressable>
        )}
      />

      <View style={styles.actions}>
        <Pressable style={styles.primary} onPress={onUseBest} disabled={!matches.length || loading}>
          <Text style={styles.primaryText}>Use best match</Text>
        </Pressable>
        <Pressable style={styles.secondary} onPress={onMakeNew}>
          <Text style={styles.secondaryText}>Make new from photo</Text>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#000', padding: 16, gap: 10 },
  title: { color: '#fff', fontSize: 24, fontWeight: '800' },
  subtitle: { color: '#bdbdbd', fontSize: 13, lineHeight: 18 },
  fixBtn:{ alignSelf:'flex-start', marginBottom:8, paddingHorizontal:12, paddingVertical:8, borderRadius:999, borderWidth:1, borderColor:'#2a2a2a' },
  fixBtnText:{ color:'#fff', fontWeight:'700' },
  badges: { flexDirection: 'row', gap: 8 },
  card: {
    borderWidth: 1,
    borderColor: '#1f1f1f',
    backgroundColor: '#0b0b0b',
    borderRadius: 18,
    padding: 14,
    gap: 10,
  },
  cardTop: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: 8 },
  cardTitle: { color: '#fff', fontSize: 16, fontWeight: '700', flex: 1 },
  sim: { color: '#fff', opacity: 0.85 },
  cardBottom: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  cardHint: { color: '#bdbdbd', fontSize: 12 },
  actions: { gap: 10, paddingBottom: 8 },
  primary: { backgroundColor: '#fff', borderRadius: 14, paddingVertical: 14, alignItems: 'center' },
  primaryText: { color: '#000', fontWeight: '800', fontSize: 16 },
  secondary: { borderRadius: 14, paddingVertical: 14, alignItems: 'center', borderWidth: 1, borderColor: '#2a2a2a' },
  secondaryText: { color: '#fff', fontWeight: '700', fontSize: 16 },
});
