import * as React from 'react';
import { View, Text, StyleSheet, Pressable } from 'react-native';
import * as Location from 'expo-location';
import { useRouter } from 'expo-router';

export default function NearbyPrinters() {
  const router = useRouter();

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Nearby Printers</Text>
      <Text style={styles.subtitle}>Live printer discovery and ordering are unavailable. No location was requested and no printer lookup was performed.</Text>

      <Pressable style={styles.secondary} onPress={() => router.back()}>
        <Text style={styles.secondaryText}>Back</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  container:{ flex:1, backgroundColor:'#000', padding:16, gap:12 },
  title:{ color:'#fff', fontSize:24, fontWeight:'800' },
  subtitle:{ color:'#bdbdbd', fontSize:13, lineHeight:18 },
  secondary:{ borderRadius:14, paddingVertical:14, alignItems:'center', borderWidth:1, borderColor:'#2a2a2a' },
  secondaryText:{ color:'#fff', fontWeight:'800' },
});
