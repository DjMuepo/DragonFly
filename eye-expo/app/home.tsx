import { View, Text, StyleSheet } from 'react-native';
import { useRouter } from 'expo-router';
import BigButton from '../src/components/BigButton';
import { useSnapStore } from '../src/lib/useSnapStore';

export default function Home() {
  const router = useRouter();
  const authToken = useSnapStore((state) => state.authToken);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>EYE</Text>
      <Text style={styles.tagline}>Capture, reconstruct and continue editing a 3D model.</Text>

      <View style={styles.buttons}>
        <BigButton
          title="Photo to 3D"
          subtitle="Capture one picture and review the generated model."
          onPress={() => router.push('/snap/camera')}
        />
        
        <BigButton
          title={authToken ? 'My Projects' : 'Sign In / My Projects'}
          subtitle="Save, reopen and continue editing your models."
          onPress={() => router.push('/account')}
        />
      </View>

      <Text style={styles.footer}>Printer ordering, public sharing, billing and admin tools are unavailable in this deployment.</Text>
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
