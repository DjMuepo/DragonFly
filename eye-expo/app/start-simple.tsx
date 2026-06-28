import { View, Text, StyleSheet, FlatList, Pressable } from 'react-native';
import { useRouter } from 'expo-router';
import { useSnapStore } from '../src/lib/useSnapStore';
import { logEvent } from '../src/lib/api';

type Item = { id: string; title: string; kind: 'shape'|'object'; icon: string; };

const SHAPES: Item[] = [
  { id: 'cube', title: 'Cube / Box', kind: 'shape', icon: '⬛' },
  { id: 'sphere', title: 'Sphere', kind: 'shape', icon: '⚪' },
  { id: 'cylinder', title: 'Cylinder', kind: 'shape', icon: '🟦' },
  { id: 'cone', title: 'Cone', kind: 'shape', icon: '🔺' },
  { id: 'pyramid', title: 'Pyramid', kind: 'shape', icon: '🔻' },
  { id: 'torus', title: 'Torus', kind: 'shape', icon: '🛟' },
];

const OBJECTS: Item[] = [
  { id: 'hook', title: 'Hook', kind: 'object', icon: '🪝' },
  { id: 'bracket', title: 'Bracket', kind: 'object', icon: '🧩' },
  { id: 'clip', title: 'Clip', kind: 'object', icon: '📎' },
  { id: 'phone-stand', title: 'Phone Stand', kind: 'object', icon: '📱' },
  { id: 'chair', title: 'Chair', kind: 'object', icon: '🪑' },
  { id: 'desk', title: 'Desk / Table', kind: 'object', icon: '🧰' },
  { id: 'toy-car', title: 'Toy Car', kind: 'object', icon: '🚗' },
];

export default function StartSimple() {
  const router = useRouter();
  const sessionId = useSnapStore((s) => s.sessionId);
  const reset = useSnapStore((s) => s.reset);
  const setMatches = useSnapStore((s) => s.setMatches);
  const selectMatch = useSnapStore((s) => s.selectMatch);

  const items = [
    { section: 'Shapes', data: SHAPES },
    { section: 'Everyday Objects', data: OBJECTS },
  ];

  const onPick = (it: Item) => {
    // Treat templates as "selected match" to reuse Edit flow.
    // We store it in matches with high similarity and OK license.
    reset();
    logEvent({ event: 'template_select', session_id: sessionId, model_id: it.id, payload: { title: it.title, kind: it.kind } });
    const fakeId = `template:${it.id}`;
    setMatches([{ id: fakeId, title: it.title, similarity: 1, license: 'OK', hosted: true } as any], 'COMMON');
    selectMatch(fakeId);
    router.push('/snap/edit?mode=template');
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Start Simple</Text>
      <Text style={styles.subtitle}>Pick a shape or common object. Then modify it.</Text>

      <FlatList
        data={items.flatMap((s) => [{ id: `h-${s.section}`, title: s.section, kind: 'shape', icon: '' } as any].concat(s.data as any))}
        keyExtractor={(i: any) => i.id}
        renderItem={({ item }: any) => {
          if (item.id.startsWith('h-')) {
            return <Text style={styles.section}>{item.title}</Text>;
          }
          return (
            <Pressable style={styles.card} onPress={() => onPick(item)}>
              <Text style={styles.icon}>{item.icon}</Text>
              <View style={{ flex: 1 }}>
                <Text style={styles.cardTitle}>{item.title}</Text>
                <Text style={styles.cardHint}>Tap to start editing</Text>
              </View>
            </Pressable>
          );
        }}
        contentContainerStyle={{ paddingBottom: 18 }}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#000', padding: 16, gap: 8 },
  title: { color: '#fff', fontSize: 24, fontWeight: '800' },
  subtitle: { color: '#bdbdbd', fontSize: 13, marginBottom: 6 },
  section: { color: '#888', fontWeight: '700', marginTop: 14, marginBottom: 8 },
  card: {
    flexDirection: 'row',
    gap: 12,
    borderWidth: 1,
    borderColor: '#1f1f1f',
    backgroundColor: '#0b0b0b',
    borderRadius: 18,
    padding: 14,
    alignItems: 'center',
    marginBottom: 10,
  },
  icon: { fontSize: 22, width: 32, textAlign: 'center' },
  cardTitle: { color: '#fff', fontSize: 16, fontWeight: '700' },
  cardHint: { color: '#bdbdbd', fontSize: 12, marginTop: 2 },
});
