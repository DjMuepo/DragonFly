import { View, Text, StyleSheet, Image, Pressable } from 'react-native';
import { useRouter } from 'expo-router';
import { useSnapStore } from '../../src/lib/useSnapStore';

export default function ViewerScreen() {
  const router = useRouter();
  const heroUri = useSnapStore((s) => s.heroUri);
  const cutoutUri = useSnapStore((s) => s.cutoutUri);
  const targetLabel = useSnapStore((s) => s.targetLabel);
  const imageUri = cutoutUri || heroUri;

  return (
    <View style={styles.container}>
      <Text style={styles.title}>3D Preview</Text>
      <View style={styles.viewerBox}>
        <View style={styles.cubeShadow} />
        <View style={styles.cube}>
          {imageUri ? <Image source={{ uri: imageUri }} style={styles.previewImage} /> : <Text style={styles.cubeText}>3D</Text>}
        </View>
      </View>
      <Text style={styles.label}>{targetLabel || 'Object'} draft preview</Text>
      <Text style={styles.note}>MVP preview is live. The next backend pass swaps this visual draft for a real GLB mesh viewer.</Text>

      <View style={styles.actions}>
        <Pressable style={styles.primaryButton} onPress={() => router.push('/snap/result')}>
          <Text style={styles.buttonText}>Back to Result</Text>
        </Pressable>
        <Pressable style={styles.secondaryButton} onPress={() => router.push('/snap/more-angles')}>
          <Text style={styles.buttonText}>Improve Model</Text>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 24, alignItems: 'center', justifyContent: 'center', backgroundColor: '#0b1020' },
  title: { color: '#fff', fontSize: 30, fontWeight: '900', marginBottom: 18 },
  viewerBox: { width: 290, height: 290, borderRadius: 24, backgroundColor: '#141b34', alignItems: 'center', justifyContent: 'center', marginBottom: 18, overflow: 'hidden' },
  cubeShadow: { position: 'absolute', width: 150, height: 36, borderRadius: 18, backgroundColor: 'rgba(0,0,0,0.35)', bottom: 44, transform: [{ scaleX: 1.2 }] },
  cube: { width: 160, height: 190, borderRadius: 20, backgroundColor: '#18c6d1', transform: [{ perspective: 800 }, { rotateY: '-18deg' }, { rotateX: '8deg' }], alignItems: 'center', justifyContent: 'center', borderWidth: 2, borderColor: 'rgba(255,255,255,0.45)' },
  previewImage: { width: 130, height: 150, resizeMode: 'contain', borderRadius: 14 },
  cubeText: { color: '#fff', fontSize: 42, fontWeight: '900' },
  label: { color: '#fff', fontSize: 20, fontWeight: '800', textAlign: 'center' },
  note: { color: '#c8d0e7', textAlign: 'center', marginTop: 10, maxWidth: 340, lineHeight: 20 },
  actions: { width: 300, gap: 12, marginTop: 24 },
  primaryButton: { backgroundColor: '#18c6d1', paddingVertical: 15, borderRadius: 12, alignItems: 'center' },
  secondaryButton: { backgroundColor: '#5b5f97', paddingVertical: 15, borderRadius: 12, alignItems: 'center' },
  buttonText: { color: '#fff', fontWeight: '800', fontSize: 16 },
});
