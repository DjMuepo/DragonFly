import React from 'react';
import { View, Text, StyleSheet, Pressable } from 'react-native';
import * as Linking from 'expo-linking';
import { useRouter } from 'expo-router';

export default function DeepLinkTool() {
  const router = useRouter();
  const sample = 'eyeplatform://design/sample-design-123';

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Deep Link Tool</Text>
      <Text style={styles.subtitle}>Test the app scheme before universal links go live.</Text>

      <View style={styles.panel}>
        <Text style={styles.meta}>Sample link</Text>
        <Text style={styles.value}>{sample}</Text>
        <Pressable style={styles.primary} onPress={() => Linking.openURL(sample)}>
          <Text style={styles.primaryText}>Open sample deep link</Text>
        </Pressable>
      </View>

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
  panel:{ borderWidth:1, borderColor:'#1f1f1f', backgroundColor:'#0b0b0b', borderRadius:18, padding:14, gap:10 },
  meta:{ color:'#8f8f8f' },
  value:{ color:'#fff', fontWeight:'700' },
  primary:{ backgroundColor:'#fff', borderRadius:14, paddingVertical:14, alignItems:'center', marginTop:8 },
  primaryText:{ color:'#000', fontWeight:'800' },
  secondary:{ borderRadius:14, paddingVertical:14, alignItems:'center', borderWidth:1, borderColor:'#2a2a2a' },
  secondaryText:{ color:'#fff', fontWeight:'800' },
});
