import { View, Text, StyleSheet, Pressable } from 'react-native';
import { useRouter } from 'expo-router';
import { useSnapStore } from '../../src/lib/useSnapStore';
import { logEvent } from '../../src/lib/api';

type ActionCard = {
  title: string;
  hint: string;
  apply: (params: any) => any;
};

const ACTION_MAP: Record<string, ActionCard[]> = {
  hook: [
    {
      title: 'Make it stronger',
      hint: 'Increase strength for hanging weight.',
      apply: (p) => ({ ...p, thickness: Math.max(1.0, (p?.thickness ?? 1.0) * 1.12), has_rib: true }),
    },
    {
      title: 'Wall mount it',
      hint: 'Prepare it for mounting to a surface.',
      apply: (p) => ({ ...p, hole_count: Math.max(2, p?.hole_count ?? 0), joint_type: 'bolt-through' }),
    },
    {
      title: 'Make it bigger',
      hint: 'Fit bulkier items.',
      apply: (p) => ({ ...p, aspect_ratio: Math.max(1.1, (p?.aspect_ratio ?? 1.0) * 1.08) }),
    },
  ],
  bracket: [
    {
      title: 'Make it stronger',
      hint: 'Reinforce for support loads.',
      apply: (p) => ({ ...p, thickness: Math.max(1.0, (p?.thickness ?? 1.0) * 1.15), has_rib: true }),
    },
    {
      title: 'Add mounting holes',
      hint: 'Prep it for screws or bolts.',
      apply: (p) => ({ ...p, hole_count: Math.max(2, p?.hole_count ?? 0), joint_type: 'bolt-through' }),
    },
    {
      title: 'Fit it tighter',
      hint: 'Adjust dimensions for a closer fit.',
      apply: (p) => ({ ...p, aspect_ratio: Math.max(0.9, (p?.aspect_ratio ?? 1.0) * 0.96) }),
    },
  ],
  clip: [
    {
      title: 'Tighten grip',
      hint: 'Increase holding strength.',
      apply: (p) => ({ ...p, thickness: Math.max(0.95, (p?.thickness ?? 1.0) * 1.08), cantilever: Math.max(0, (p?.cantilever ?? 0) - 0.05) }),
    },
    {
      title: 'Make it smoother',
      hint: 'Reduce sharp edges.',
      apply: (p) => ({ ...p, has_fillet: true }),
    },
    {
      title: 'Resize it',
      hint: 'Adapt to different cables or objects.',
      apply: (p) => ({ ...p, aspect_ratio: Math.max(0.8, (p?.aspect_ratio ?? 1.0) * 1.05) }),
    },
  ],
  handle: [
    {
      title: 'Improve comfort',
      hint: 'Refine grip and ergonomics.',
      apply: (p) => ({ ...p, has_fillet: true, thickness: Math.max(1.0, (p?.thickness ?? 1.0) * 1.06) }),
    },
    {
      title: 'Make it thicker',
      hint: 'Increase durability and hold.',
      apply: (p) => ({ ...p, thickness: Math.max(1.0, (p?.thickness ?? 1.0) * 1.12) }),
    },
    {
      title: 'Keep it simple',
      hint: 'Start with the basic editing controls.',
      apply: (p) => ({ ...p }),
    },
  ],
};

export default function SuggestedActions() {
  const router = useRouter();
  const visionDraft = useSnapStore((s) => (s as any).visionDraft);
  const family = (visionDraft?.classification?.object_family || 'object').toLowerCase();
  const actions = ACTION_MAP[family] || [
    {
      title: 'Make it stronger',
      hint: 'Improve durability.',
      apply: (p: any) => ({ ...p, thickness: Math.max(1.0, (p?.thickness ?? 1.0) * 1.1), has_rib: true }),
    },
    {
      title: 'Make it fit',
      hint: 'Adjust size and tolerance.',
      apply: (p: any) => ({ ...p, aspect_ratio: Math.max(0.9, (p?.aspect_ratio ?? 1.0) * 0.98) }),
    },
    {
      title: 'Keep it simple',
      hint: 'Start editing with the basic controls.',
      apply: (p: any) => ({ ...p }),
    },
  ];

  const sessionId = useSnapStore((s) => (s as any).sessionId);
  const structuralParams = useSnapStore((s) => (s as any).structuralParams);
  const setStructuralParams = useSnapStore((s) => (s as any).setStructuralParams);

  const chooseAction = (card: ActionCard) => {
    const next = card.apply(structuralParams || {});
    setStructuralParams(next);
    logEvent({
      event: 'suggested_action_apply',
      session_id: sessionId,
      payload: {
        family,
        action: card.title,
        before: structuralParams,
        after: next,
      },
    });
    router.push('/snap/edit?mode=unique');
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Edit more actions?</Text>
      <Text style={styles.subtitle}>
        Optional ideas based on what the app thinks you captured.
      </Text>

      <View style={styles.panel}>
        <Text style={styles.family}>Detected family: {family}</Text>
        {actions.map((a) => (
          <Pressable key={a.title} style={styles.card} onPress={() => chooseAction(a)}>
            <Text style={styles.cardTitle}>{a.title}</Text>
            <Text style={styles.cardHint}>{a.hint}</Text>
          </Pressable>
        ))}
      </View>

      <View style={styles.actions}>
        <Pressable style={styles.primary} onPress={() => router.push('/snap/edit?mode=unique')}>
          <Text style={styles.primaryText}>Continue editing</Text>
        </Pressable>
        <Pressable style={styles.secondary} onPress={() => router.back()}>
          <Text style={styles.secondaryText}>Back</Text>
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
    gap: 10,
  },
  family: { color: '#fff', fontWeight: '800', marginBottom: 4 },
  card: {
    borderWidth: 1,
    borderColor: '#1f1f1f',
    backgroundColor: '#060606',
    borderRadius: 14,
    padding: 12,
    gap: 4,
  },
  cardTitle: { color: '#fff', fontWeight: '800' },
  cardHint: { color: '#bdbdbd', fontSize: 12 },
  actions: { marginTop: 'auto', gap: 10, paddingBottom: 8 },
  primary: { backgroundColor: '#fff', borderRadius: 14, paddingVertical: 14, alignItems: 'center' },
  primaryText: { color: '#000', fontWeight: '800', fontSize: 16 },
  secondary: { borderRadius: 14, paddingVertical: 14, alignItems: 'center', borderWidth: 1, borderColor: '#2a2a2a' },
  secondaryText: { color: '#fff', fontWeight: '800' },
});
