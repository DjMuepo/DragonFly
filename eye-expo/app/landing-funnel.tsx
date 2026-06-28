import * as React from 'react';
import { View, Text, StyleSheet, Pressable } from 'react-native';
import { useRouter } from 'expo-router';

export default function LandingFunnelScreen() {
  const router = useRouter();
  return (
    <View style={styles.container}>
      <Text style={styles.title}>View This Design</Text>
      <Text style={styles.body}>Preview shared designs, then open them in the app to modify, print, or remix.</Text>
      <Pressable style={styles.primary} onPress={() => router.push('/invite')}>
        <Text style={styles.primaryText}>Open in App</Text>
      </Pressable>
      <Pressable style={styles.secondary}>
        <Text style={styles.secondaryText}>Download App</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  container:{ flex:1, justifyContent:'center', alignItems:'center', backgroundColor:'#000', padding:20, gap:12 },
  title:{ color:'#fff', fontSize:24, fontWeight:'800' },
  body:{ color:'#aaa', lineHeight:20, textAlign:'center' },
  primary:{ backgroundColor:'#fff', borderRadius:14, paddingVertical:14, paddingHorizontal:18 },
  primaryText:{ color:'#000', fontWeight:'800' },
  secondary:{ borderWidth:1, borderColor:'#2a2a2a', borderRadius:14, paddingVertical:12, paddingHorizontal:18 },
  secondaryText:{ color:'#fff', fontWeight:'800' },
});
