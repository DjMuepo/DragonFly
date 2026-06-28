import * as React from 'react';
import { View, Text, StyleSheet, Pressable, PanResponder } from 'react-native';
import { useRouter } from 'expo-router';
import { useSnapStore } from '../../src/lib/useSnapStore';


function FamilyShape({
  family,
  shape,
  width,
  height,
  depth,
  rotY,
  rotX,
}: {
  family?: string;
  shape: string;
  width: number;
  height: number;
  depth: number;
  rotY: number;
  rotX: number;
}) {
  const scale = 120;
  const w = Math.max(60, width * scale);
  const h = Math.max(36, height * scale);
  const d = Math.max(16, depth * scale);

  const common = {
    transform: [{ perspective: 800 }, { rotateY: `${rotY}deg` }, { rotateX: `${rotX}deg` }],
    shadowColor: '#ffffff',
    shadowOpacity: 0.18,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 0 },
  } as const;

  if (family === 'hook') {
    return (
      <View style={{ width: w, height: h + 30, alignItems: 'center', justifyContent: 'center', ...common }}>
        <View style={{ width: Math.max(18, d * 0.7), height: h * 0.8, backgroundColor: '#f4f4f4', borderRadius: 12, borderWidth: 1, borderColor: '#d0d0d0' }} />
        <View style={{ position: 'absolute', right: w * 0.18, top: h * 0.28, width: w * 0.42, height: h * 0.42, borderWidth: Math.max(8, d * 0.22), borderColor: '#f4f4f4', borderLeftColor: 'transparent', borderTopColor: 'transparent', borderRadius: 999 }} />
      </View>
    );
  }

  if (family === 'bracket') {
    return (
      <View style={{ width: w, height: h + 24, alignItems: 'flex-start', justifyContent: 'flex-end', ...common }}>
        <View style={{ width: w * 0.72, height: Math.max(14, d * 0.35), backgroundColor: '#f4f4f4', borderWidth: 1, borderColor: '#d0d0d0' }} />
        <View style={{ position: 'absolute', left: 0, bottom: 0, width: Math.max(14, d * 0.35), height: h * 0.9, backgroundColor: '#e8e8e8', borderWidth: 1, borderColor: '#d0d0d0' }} />
      </View>
    );
  }

  if (family === 'clip') {
    return (
      <View style={{ width: w * 0.78, height: h + 24, alignItems: 'center', justifyContent: 'center', ...common }}>
        <View style={{ width: Math.max(16, d * 0.4), height: h * 0.84, backgroundColor: '#f4f4f4', borderRadius: 10, borderWidth: 1, borderColor: '#d0d0d0' }} />
        <View style={{ position: 'absolute', right: 2, top: 8, width: w * 0.38, height: h * 0.3, borderWidth: Math.max(8, d * 0.18), borderColor: '#f4f4f4', borderLeftColor: 'transparent', borderBottomColor: 'transparent', borderRadius: 18 }} />
      </View>
    );
  }

  if (family === 'handle' || shape === 'capsule') {
    return (
      <View
        style={{
          width: w,
          height: h,
          borderRadius: h / 2,
          backgroundColor: '#f4f4f4',
          borderWidth: 1,
          borderColor: '#d0d0d0',
          ...common,
        }}
      />
    );
  }

  if (family === 'adapter') {
    return (
      <View style={{ width: w, height: h + 10, alignItems: 'center', justifyContent: 'center', ...common }}>
        <View style={{ width: w * 0.78, height: h * 0.72, borderRadius: h * 0.36, backgroundColor: '#f4f4f4', borderWidth: 1, borderColor: '#d0d0d0' }} />
        <View style={{ position: 'absolute', width: w * 0.3, height: h * 0.28, borderRadius: 999, backgroundColor: '#08080a', borderWidth: 1, borderColor: '#cfcfcf' }} />
      </View>
    );
  }

  if (family === 'enclosure') {
    return (
      <View style={{ width: w, height: h, backgroundColor: '#f4f4f4', borderWidth: 1, borderColor: '#d0d0d0', ...common }}>
        <View style={{ position: 'absolute', left: 10, top: 10, right: 10, bottom: 10, borderWidth: 1, borderColor: '#c8c8c8' }} />
      </View>
    );
  }

  if (shape === 'wedge') {
    return (
      <View
        style={{
          width: w,
          height: h,
          backgroundColor: '#f4f4f4',
          borderWidth: 1,
          borderColor: '#d0d0d0',
          transform: [{ perspective: 800 }, { skewX: '-18deg' }, { rotateY: `${rotY}deg` }, { rotateX: `${rotX}deg` }],
          shadowColor: '#ffffff',
          shadowOpacity: 0.18,
          shadowRadius: 10,
          shadowOffset: { width: 0, height: 0 },
        }}
      />
    );
  }

  return (
    <View
      style={{
        width: w,
        height: h,
        backgroundColor: '#f4f4f4',
        borderWidth: 1,
        borderColor: '#d0d0d0',
        ...common,
      }}
    >
      <View
        style={{
          position: 'absolute',
          right: -d * 0.12,
          top: 6,
          width: Math.max(12, d * 0.2),
          height: Math.max(24, h * 0.82),
          backgroundColor: '#d9d9d9',
          borderLeftWidth: 1,
          borderColor: '#c8c8c8',
          opacity: 0.8,
        }}
      />
      <View
        style={{
          position: 'absolute',
          left: 6,
          top: -Math.max(8, d * 0.1),
          width: Math.max(24, w * 0.92),
          height: Math.max(12, d * 0.16),
          backgroundColor: '#ececec',
          borderBottomWidth: 1,
          borderColor: '#d0d0d0',
          opacity: 0.9,
        }}
      />
    </View>
  );
}


export default function RotatablePreview() {
  const router = useRouter();
  const visionDraft = useSnapStore((s) => (s as any).visionDraft);
  const visionReconstruct = useSnapStore((s) => (s as any).visionReconstruct);
  const geometry = visionDraft?.geometry;
  const family = visionReconstruct?.family || visionDraft?.parametric?.family || visionDraft?.classification?.object_family;
  const [rotY, setRotY] = React.useState(18);
  const [rotX, setRotX] = React.useState(-8);

  const panResponder = React.useMemo(
    () =>
      PanResponder.create({
        onStartShouldSetPanResponder: () => true,
        onPanResponderMove: (_, g) => {
          setRotY(18 + g.dx * 0.25);
          setRotX(-8 - g.dy * 0.12);
        },
      }),
    []
  );

  if (!geometry) {
    return (
      <View style={styles.container}>
        <Text style={styles.title}>Rotatable Preview</Text>
        <Text style={styles.subtitle}>No generated geometry yet.</Text>
        <Pressable style={styles.secondary} onPress={() => router.back()}>
          <Text style={styles.secondaryText}>Back</Text>
        </Pressable>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Rotatable Preview</Text>
      <Text style={styles.subtitle}>Drag to rotate the generated family-aware preview.</Text>

      <View style={styles.stage} {...panResponder.panHandlers}>
        <FamilyShape
          family={family}
          shape={geometry.shape}
          width={geometry.width}
          height={geometry.height}
          depth={geometry.depth}
          rotY={rotY}
          rotX={rotX}
        />
      </View>

      <View style={styles.panel}>
        <Text style={styles.panelTitle}>Preview Geometry</Text>
        {family ? <Text style={styles.panelHint}>Family: <Text style={styles.white}>{family}</Text></Text> : null}
        <Text style={styles.panelHint}>Shape: <Text style={styles.white}>{geometry.shape}</Text></Text>
        {visionReconstruct?.parametric_draft?.params?.prior ? <Text style={styles.panelHint}>Prior: <Text style={styles.white}>{visionReconstruct.parametric_draft.params.prior}</Text></Text> : null}
        <Text style={styles.panelHint}>W × H × D: <Text style={styles.white}>{geometry.width} × {geometry.height} × {geometry.depth}</Text></Text>
        {geometry.notes?.map((n: string, idx: number) => (
          <Text key={idx} style={styles.note}>• {n}</Text>
        ))}
      </View>

      <View style={styles.actions}>
        <Pressable style={styles.primary} onPress={() => router.push('/snap/edit?mode=unique')}>
          <Text style={styles.primaryText}>Use this draft</Text>
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
  stage: {
    flex: 1,
    minHeight: 280,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: '#1f1f1f',
    backgroundColor: '#08080a',
    alignItems: 'center',
    justifyContent: 'center',
    overflow: 'hidden',
  },
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
  white: { color: '#fff', fontWeight: '800' },
  note: { color: '#fff', opacity: 0.88, fontSize: 12 },
  actions: { gap: 10, paddingBottom: 8 },
  primary: { backgroundColor: '#fff', borderRadius: 14, paddingVertical: 14, alignItems: 'center' },
  primaryText: { color: '#000', fontWeight: '800', fontSize: 16 },
  secondary: { borderRadius: 14, paddingVertical: 14, alignItems: 'center', borderWidth: 1, borderColor: '#2a2a2a' },
  secondaryText: { color: '#fff', fontWeight: '800' },
});
