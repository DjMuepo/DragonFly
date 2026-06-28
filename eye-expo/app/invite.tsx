import * as React from 'react';
import { View, Text, TextInput, Pressable, StyleSheet } from 'react-native';
import { useRouter } from 'expo-router';
import { validateInviteCode, redeemInviteCode } from '../src/lib/api';

export default function InviteScreen() {
  const router = useRouter();
  const [code, setCode] = React.useState('');
  const [email, setEmail] = React.useState('');
  const [status, setStatus] = React.useState<any>(null);

  const submit = async () => {
    try {
      const valid = await validateInviteCode({ code, email });
      setStatus(valid);
      if (valid.valid) {
        const redeemed = await redeemInviteCode({ code, email, user_id: 'early_user' });
        setStatus(redeemed);
        if (redeemed.redeemed) router.push('/onboarding');
      }
    } catch (e) { console.warn(e); }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>You’re early.</Text>
      <Text style={styles.subtitle}>Enter your invite code to access the beta.</Text>
      <TextInput style={styles.input} value={email} onChangeText={setEmail} placeholder="Email (optional)" placeholderTextColor="#666" />
      <TextInput style={styles.input} value={code} onChangeText={setCode} placeholder="Invite code" placeholderTextColor="#666" />
      <Pressable style={styles.primary} onPress={submit}><Text style={styles.primaryText}>Enter</Text></Pressable>
      {status ? <Text style={styles.meta}>{JSON.stringify(status)}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container:{ flex:1, justifyContent:'center', padding:20, backgroundColor:'#000', gap:10 },
  title:{ color:'#fff', fontSize:24, fontWeight:'800' },
  subtitle:{ color:'#aaa', fontSize:13, lineHeight:18 },
  input:{ borderWidth:1, borderColor:'#222', borderRadius:12, padding:12, color:'#fff' },
  primary:{ backgroundColor:'#fff', borderRadius:14, paddingVertical:14, alignItems:'center' },
  primaryText:{ color:'#000', fontWeight:'800' },
  meta:{ color:'#bdbdbd', fontSize:12, lineHeight:18 }
});
