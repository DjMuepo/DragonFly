import * as React from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { useRouter } from 'expo-router';

export default function Onboarding(){
  const r = useRouter();
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Turn anything into a 3D model</Text>
      <Text style={styles.sub}>Scan → Modify → Print</Text>
      <Text style={styles.body}>See the value in seconds and jump straight into the camera.</Text>
      <Pressable onPress={() => r.push('/snap/camera')} style={styles.primary}>
        <Text style={styles.primaryText}>Let’s try it now</Text>
      </Pressable>
      <Pressable onPress={() => r.push('/invite')} style={styles.secondary}>
        <Text style={styles.secondaryText}>Back to Invite</Text>
      </Pressable>
    </View>
  )
}

const styles = StyleSheet.create({
  container:{ flex:1, justifyContent:'center', alignItems:'center', backgroundColor:'#000', padding:20, gap:12 },
  title:{ color:'#fff', fontSize:24, fontWeight:'800', textAlign:'center' },
  sub:{ color:'#d4d4d4', fontSize:15 },
  body:{ color:'#999', lineHeight:20, textAlign:'center' },
  primary:{ backgroundColor:'#fff', borderRadius:14, paddingVertical:14, paddingHorizontal:18 },
  primaryText:{ color:'#000', fontWeight:'800' },
  secondary:{ borderWidth:1, borderColor:'#2a2a2a', borderRadius:14, paddingVertical:12, paddingHorizontal:18 },
  secondaryText:{ color:'#fff', fontWeight:'800' },
});
