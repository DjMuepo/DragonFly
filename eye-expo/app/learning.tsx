import * as React from 'react';
import { View, Text, StyleSheet, Pressable, ScrollView } from 'react-native';
import { getAiLearningSummary } from '../src/lib/api';

export default function LearningScreen() {
  const [data, setData] = React.useState<any>(null);

  const load = async () => {
    try { setData(await getAiLearningSummary(500)); } catch (e) { console.warn(e); }
  };

  React.useEffect(() => { load(); }, []);

  return (
    <ScrollView style={styles.container} contentContainerStyle={{ padding:16, gap:12 }}>
      <Text style={styles.title}>AI Learning</Text>
      <Text style={styles.subtitle}>Summaries and recommendations learned from Object DNA records, edits, and print outcomes.</Text>
      <Pressable style={styles.secondary} onPress={load}><Text style={styles.secondaryText}>Refresh</Text></Pressable>
      {(data?.recommendations || []).map((item:any, idx:number) => (
        <View key={idx} style={styles.card}>
          <Text style={styles.cardTitle}>{item.family}</Text>
          <Text style={styles.meta}>Records: {item.records}</Text>
          <Text style={styles.meta}>Print rate: {item.print_rate}</Text>
          <Text style={styles.meta}>Success rate: {item.success_rate}</Text>
          <Text style={styles.meta}>Material: {item.recommended_material || 'n/a'}</Text>
          <Text style={styles.body}>{item.message}</Text>
        </View>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container:{ flex:1, backgroundColor:'#000' },
  title:{ color:'#fff', fontSize:24, fontWeight:'800' },
  subtitle:{ color:'#bdbdbd', fontSize:13, lineHeight:18 },
  card:{ borderWidth:1, borderColor:'#1f1f1f', backgroundColor:'#0b0b0b', borderRadius:18, padding:14, gap:6 },
  cardTitle:{ color:'#fff', fontSize:16, fontWeight:'800' },
  meta:{ color:'#bdbdbd', fontSize:12, lineHeight:18 },
  body:{ color:'#fff', lineHeight:20 },
  secondary:{ borderRadius:14, paddingVertical:12, alignItems:'center', borderWidth:1, borderColor:'#2a2a2a' },
  secondaryText:{ color:'#fff', fontWeight:'800' },
});
