import { View, Text, StyleSheet } from 'react-native';
import { useRouter } from 'expo-router';
import BigButton from '../src/components/BigButton';

export default function Home() {
  const router = useRouter();

  return (
    <View style={styles.container}>
      <Text style={styles.title}>EYE</Text>
      <Text style={styles.tagline}>The fastest path from photo to printable model.</Text>

      <View style={styles.buttons}>
        <BigButton
          title="Snap & Copy"
          subtitle="Take one picture. Find or generate a model."
          onPress={() => router.push('/snap/camera')}
        />
        
        <BigButton
          title="Start Simple"
          subtitle="Shapes & everyday objects, ready to modify."
          onPress={() => router.push('/start-simple')}
        />

        <BigButton
          title="Template"
          subtitle="Start from common parts and customize."
          onPress={() => router.push('/snap/edit?mode=template')}
        />
        <BigButton
          title="Build Blocks"
          subtitle="Drag-and-snap building blocks. Toddler simple."
          onPress={() => router.push('/snap/edit?mode=blocks')}
        />
      </View>

      <Text style={styles.footer}>Muepo Operations</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000',
    paddingHorizontal: 20,
    paddingTop: 28,
  },
  title: {
    color: '#fff',
    fontSize: 44,
    fontWeight: '800',
    letterSpacing: 4,
  },
  tagline: {
    color: '#bdbdbd',
    marginTop: 8,
    marginBottom: 18,
  },
  buttons: {
    gap: 14,
    marginTop: 12,
  },
  footer: {
    marginTop: 'auto',
    color: '#666',
    paddingVertical: 16,
  }
});
