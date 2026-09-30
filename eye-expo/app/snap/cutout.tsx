import { View, Text, Image, Pressable, StyleSheet } from 'react-native';
import { useRouter } from 'expo-router';
import { useSnapStore } from '../../src/lib/useSnapStore';

export default function CutoutScreen() {
  const router = useRouter();
  const heroUri = useSnapStore((s) => s.heroUri);
  const clear = useSnapStore((s) => s.clear);

  if (!heroUri) {
    return (
      <View style={styles.center}>
        <Text style={styles.title}>No Photo Found</Text>
        <Pressable style={styles.primaryButton} onPress={() => router.push('/snap/camera')}>
          <Text style={styles.buttonText}>Open Camera</Text>
        </Pressable>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Review Photo</Text>
      <Text style={styles.subtitle}>Check that the object is visible and in focus.</Text>
      <Image source={{ uri: heroUri }} style={styles.image} />

      <View style={styles.actions}>
        <Pressable style={styles.secondaryButton} onPress={() => router.push('/snap/process')}>
          <Text style={styles.buttonText}>Continue</Text>
        </Pressable>

        <Pressable style={styles.darkButton} onPress={() => router.push('/snap/camera')}>
          <Text style={styles.buttonText}>Retake</Text>
        </Pressable>

        <Pressable
          style={styles.darkButton}
          onPress={() => {
            clear();
            router.push('/');
          }}
        >
          <Text style={styles.buttonText}>Home</Text>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 16, justifyContent: 'center', backgroundColor: '#fff' },
  title: { fontSize: 28, fontWeight: '800', textAlign: 'center', marginBottom: 8, color: '#111' },
  subtitle: { textAlign: 'center', color: '#555', marginBottom: 16, fontSize: 15 },
  image: { width: '100%', maxHeight: 320, height: '42%', resizeMode: 'contain', marginBottom: 20, backgroundColor: '#f7f7f7', borderRadius: 8 },
  actions: { gap: 10 },
  primaryButton: { backgroundColor: '#18c6d1', paddingVertical: 15, borderRadius: 12, alignItems: 'center' },
  secondaryButton: { backgroundColor: '#5b5f97', paddingVertical: 15, borderRadius: 12, alignItems: 'center' },
  darkButton: { backgroundColor: '#444', paddingVertical: 15, borderRadius: 12, alignItems: 'center' },
  buttonText: { color: '#fff', fontWeight: '800' },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 16, padding: 24, backgroundColor: '#fff' },
});
