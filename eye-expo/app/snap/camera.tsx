import { View, Text, Pressable, StyleSheet, ActivityIndicator } from 'react-native';
import { CameraView, useCameraPermissions } from 'expo-camera';
import * as ImagePicker from 'expo-image-picker';
import { useRef, useState } from 'react';
import { useRouter } from 'expo-router';
import { useSnapStore } from '../../src/lib/useSnapStore';

export default function SnapCamera() {
  const router = useRouter();
  const [permission, requestPermission] = useCameraPermissions();
  const cameraRef = useRef<CameraView | null>(null);
  const [isCapturing, setIsCapturing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const setHeroUri = useSnapStore((s) => s.setHeroUri);
  const setCutoutUri = useSnapStore((s) => s.setCutoutUri);

  const onUpload = async () => {
    try {
      setError(null);
      const selection = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ImagePicker.MediaTypeOptions.Images, quality: 0.85 });
      if (selection.canceled || !selection.assets[0]?.uri) return;
      setHeroUri(selection.assets[0].uri);
      setCutoutUri(undefined);
      router.push('/snap/cutout');
    } catch {
      setError('Unable to open your photos. Please try again.');
    }
  };

  if (!permission) {
    return (
      <View style={styles.center}>
        <ActivityIndicator />
        <Text style={styles.centerText}>Opening camera...</Text>
        <Pressable style={styles.primary} onPress={onUpload}><Text style={styles.primaryText}>Upload Photo</Text></Pressable>
      </View>
    );
  }

  if (!permission.granted) {
    return (
      <View style={styles.center}>
        <Text style={styles.title}>Camera Permission Required</Text>
        <Text style={styles.centerText}>Allow camera access to scan an object.</Text>
        <Pressable style={styles.primary} onPress={requestPermission}>
          <Text style={styles.primaryText}>Grant Camera Access</Text>
        </Pressable>
        <Pressable style={styles.primary} onPress={onUpload}><Text style={styles.primaryText}>Upload Photo</Text></Pressable>
        {error ? <Text style={styles.centerText}>{error}</Text> : null}
      </View>
    );
  }

  const onCapture = async () => {
    if (!cameraRef.current || isCapturing) return;

    try {
      setIsCapturing(true);
      const photo = await cameraRef.current.takePictureAsync({ quality: 0.72, skipProcessing: false });

      if (!photo?.uri) return;
      setHeroUri(photo.uri);
      setCutoutUri(undefined);
      router.push('/snap/cutout');
    } catch (error) {
      console.warn('Capture failed:', error);
      setError('Could not capture a photo. Try again or upload one.');
    } finally {
      setIsCapturing(false);
    }
  };

  return (
    <View style={styles.container}>
      <CameraView ref={cameraRef} style={styles.camera} facing="back" />

      <View style={styles.topOverlay}>
        <Text style={styles.overlayTitle}>One-Photo Scan</Text>
        <Text style={styles.overlayText}>Center one object. Good light gives better 3D results.</Text>
        {error ? <Text style={styles.overlayText}>{error}</Text> : null}
      </View>

      <View style={styles.controls}>
        <Pressable style={styles.secondary} onPress={() => router.push('/')}>
          <Text style={styles.secondaryText}>Home</Text>
        </Pressable>

        <Pressable style={[styles.shutter, isCapturing && styles.disabled]} onPress={onCapture}>
          {isCapturing ? <ActivityIndicator color="#111" /> : <View style={styles.shutterInner} />}
        </Pressable>

        <Pressable style={styles.secondary} onPress={onUpload} accessibilityLabel="Upload photo">
          <Text style={styles.secondaryText}>Upload</Text>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#000' },
  camera: { flex: 1 },
  topOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    paddingTop: 18,
    paddingHorizontal: 18,
    paddingBottom: 16,
    backgroundColor: 'rgba(0,0,0,0.35)',
  },
  overlayTitle: { color: '#fff', fontSize: 24, fontWeight: '800' },
  overlayText: { color: '#e6e6e6', marginTop: 4 },
  controls: {
    position: 'absolute',
    left: 0,
    right: 0,
    bottom: 0,
    paddingBottom: 30,
    paddingHorizontal: 18,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  shutter: {
    width: 82,
    height: 82,
    borderRadius: 41,
    backgroundColor: '#fff',
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 4,
    borderColor: '#d8d8d8',
  },
  shutterInner: { width: 58, height: 58, borderRadius: 29, backgroundColor: '#fff' },
  disabled: { opacity: 0.55 },
  secondary: {
    width: 84,
    paddingVertical: 12,
    borderRadius: 12,
    backgroundColor: 'rgba(255,255,255,0.18)',
    alignItems: 'center',
  },
  secondaryText: { color: '#fff', fontWeight: '700' },
  center: { flex: 1, backgroundColor: '#050505', alignItems: 'center', justifyContent: 'center', padding: 24, gap: 14 },
  title: { color: '#fff', fontSize: 24, fontWeight: '800', textAlign: 'center' },
  centerText: { color: '#cfcfcf', textAlign: 'center' },
  primary: { backgroundColor: '#18c6d1', paddingVertical: 14, paddingHorizontal: 18, borderRadius: 14 },
  primaryText: { color: '#fff', fontWeight: '800' },
});
