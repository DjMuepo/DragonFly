import * as React from 'react';
import { View, Text, StyleSheet, Pressable, ScrollView } from 'react-native';
import { checkAutoSaveSubscription } from '../src/lib/api';

export default function AutoSaveScreen() {
  const [paid, setPaid] = React.useState(false);
  const [status, setStatus] = React.useState<any>(null);

  const check = async (nextPaid: boolean) => {
    try { setStatus(await checkAutoSaveSubscription({ is_paid: nextPaid })); } catch (e) { console.warn(e); }
  };

  React.useEffect(() => { check(paid); }, [paid]);

  return (
    <ScrollView style={styles.container} contentContainerStyle={{ padding:16, gap:12 }}>
      <Text style={styles.title}>Premium Auto-Save</Text>
      <Text style={styles.subtitle}>Reserve automatic Object DNA save behavior for subscribed accounts.</Text>

      <View style={styles.panel}>
        <Text style={styles.meta}>Subscription: {paid ? 'Pro' : 'Free'}</Text>
        <Pressable style={styles.secondary} onPress={() => setPaid(!paid)}>
          <Text style={styles.secondaryText}>{paid ? 'Switch to Free' : 'Switch to Pro'}</Text>
        </Pressable>
        {status ? (
          <>
            <Text style={styles.meta}>Allowed: {status.allowed ? 'Yes' : 'No'}</Text>
            <Text style={styles.body}>{status.message || ''}</Text>
          </>
        ) : null}
      </View>

      <View style={styles.panel}>
        <Text style={styles.sectionTitle}>Upgrade value</Text>
        <Text style={styles.meta}>• Accepted scan prompts can save automatically</Text>
        <Text style={styles.meta}>• Accepted repair plans can save automatically</Text>
        <Text style={styles.meta}>• Confirmed AR fit can save automatically</Text>
        <Text style={styles.meta}>• Long-term structured memory becomes a premium benefit</Text>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container:{ flex:1, backgroundColor:'#000' },
  title:{ color:'#fff', fontSize:24, fontWeight:'800' },
  subtitle:{ color:'#bdbdbd', fontSize:13, lineHeight:18 },
  panel:{ borderWidth:1, borderColor:'#1f1f1f', backgroundColor:'#0b0b0b', borderRadius:18, padding:14, gap:10 },
  sectionTitle:{ color:'#fff', fontSize:16, fontWeight:'800' },
  meta:{ color:'#bdbdbd', fontSize:12, lineHeight:18 },
  body:{ color:'#fff', lineHeight:20 },
  secondary:{ borderRadius:14, paddingVertical:12, paddingHorizontal:12, alignItems:'center', borderWidth:1, borderColor:'#2a2a2a' },
  secondaryText:{ color:'#fff', fontWeight:'800' },
});
