import { useRef, useState } from 'react';
import { View, Text, Pressable, StyleSheet, ActivityIndicator } from 'react-native';
import { CameraView, useCameraPermissions } from 'expo-camera';
import { useRouter } from 'expo-router';
import { useSnapStore } from '../../src/lib/useSnapStore';

const STEPS = ['Left side', 'Right side', 'Top view'];

export default function MultiCapture() {
  const router = useRouter();
  const cameraRef = useRef<CameraView | null>(null);
  const [permission, requestPermission] = useCameraPermissions();
  const [index, setIndex] = useState(0);
  const [capturing, setCapturing] = useState(false);
  const heroUri = useSnapStore((s:any) => s.heroUri);
  const burstUris = useSnapStore((s:any) => s.burstUris);
  const setCapture = useSnapStore((s:any) => s.setCapture);

  const snapNext = async () => {
    if (!cameraRef.current || capturing) return;
    setCapturing(true);
    try {
      const p = await cameraRef.current.takePictureAsync({ quality: 0.65, skipProcessing: false });
      const nextUris = [...(burstUris || []), p.uri];
      setCapture(heroUri, nextUris);
      if (index >= STEPS.length - 1) {
        router.push('/snap/cutout');
      } else {
        setIndex(index + 1);
      }
    } catch (e) {
      console.warn('multi capture failed', e);
    } finally {
      setCapturing(false);
    }
  };

  if (!permission) return <View style={styles.center}><ActivityIndicator /></View>;
  if (!permission.granted) {
    return (
      <View style={styles.center}>
        <Text style={styles.text}>We need camera access for guided multi-angle capture.</Text>
        <Pressable style={styles.primary} onPress={requestPermission}><Text style={styles.primaryText}>Allow Camera</Text></Pressable>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <CameraView ref={cameraRef} style={styles.camera} facing="back" />
      <View style={styles.overlayTop}>
        <Text style={styles.step}>Step {index + 2} of 4</Text>
        <Text style={styles.title}>{STEPS[index]}</Text>
        <Text style={styles.hint}>Move the phone slightly and capture this angle.</Text>
      </View>
      <View style={styles.overlayBottom}>
        <Pressable style={[styles.shutter, capturing && styles.shutterDisabled]} onPress={snapNext}>
          {capturing ? <ActivityIndicator /> : <View style={styles.shutterInner} />}
        </Pressable>
        <Text style={styles.small}>This improves reconstruction accuracy.</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#000' },
  camera: { flex: 1 },
  overlayTop: { position: 'absolute', top: 0, left: 0, right: 0, paddingTop: 16, paddingHorizontal: 16, gap: 4 },
  step: { color: '#bdbdbd', fontSize: 12 },
  title: { color: '#fff', fontSize: 24, fontWeight: '800' },
  hint: { color: '#fff', fontSize: 14, opacity: 0.92 },
  overlayBottom: { position: 'absolute', left: 0, right: 0, bottom: 0, paddingBottom: 28, paddingHorizontal: 16, alignItems: 'center', gap: 10 },
  shutter: { width: 78, height: 78, borderRadius: 39, borderWidth: 2, borderColor: '#fff', alignItems: 'center', justifyContent: 'center', backgroundColor: 'rgba(0,0,0,0.2)' },
  shutterDisabled: { opacity: 0.6 },
  shutterInner: { width: 58, height: 58, borderRadius: 29, backgroundColor: '#fff' },
  small: { color: '#cfcfcf', fontSize: 12, opacity: 0.9, textAlign: 'center' },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: '#000', padding: 24, gap: 16 },
  text: { color: '#fff', textAlign: 'center' },
  primary: { backgroundColor: '#fff', paddingVertical: 12, paddingHorizontal: 16, borderRadius: 12 },
  primaryText: { color: '#000', fontWeight: '700' }
});
