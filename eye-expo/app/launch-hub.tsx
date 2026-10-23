import * as React from 'react';
import { View, Text, StyleSheet, Pressable, ScrollView } from 'react-native';
import { useRouter } from 'expo-router';

export default function LaunchHubScreen() {
  const router = useRouter();
  return (
    <ScrollView style={styles.container} contentContainerStyle={{ padding:16, gap:12 }}>
      <Text style={styles.title}>DragonFly</Text>
      <Text style={styles.subtitle}>Core scan, reconstruction, editing and saved projects.</Text>

      <View style={styles.panel}>
        <Pressable style={styles.primary} onPress={() => router.push('/snap/camera')}><Text style={styles.primaryText}>Start Scan</Text></Pressable>
        <Pressable style={styles.secondary} onPress={() => router.push('/account')}><Text style={styles.secondaryText}>Sign In / My Projects</Text></Pressable>
        <Text style={styles.subtitle}>Sharing, billing, printer orders, invites and admin services are unavailable and not linked here.</Text>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container:{ flex:1, backgroundColor:'#000' },
  title:{ color:'#fff', fontSize:24, fontWeight:'800' },
  subtitle:{ color:'#bdbdbd', fontSize:13, lineHeight:18 },
  panel:{ borderWidth:1, borderColor:'#1f1f1f', backgroundColor:'#0b0b0b', borderRadius:18, padding:14, gap:10 },
  primary:{ backgroundColor:'#fff', borderRadius:14, paddingVertical:14, alignItems:'center' },
  primaryText:{ color:'#000', fontWeight:'800' },
  secondary:{ borderWidth:1, borderColor:'#2a2a2a', borderRadius:14, paddingVertical:12, alignItems:'center' },
  secondaryText:{ color:'#fff', fontWeight:'800' },
});
