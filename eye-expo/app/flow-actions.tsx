import * as React from 'react';
import { View, Text, StyleSheet, Pressable, ScrollView, TextInput } from 'react-native';
import { acceptScanFlow, completePrintFlow, appendEditFlow } from '../src/lib/api';

export default function FlowActionsScreen() {
  const [record, setRecord] = React.useState<any>(null);
  const [notes, setNotes] = React.useState('strengthened corner');

  const scanAccept = async () => {
    try {
      const res = await acceptScanFlow({
        title: 'Scanned Hook',
        detected_label: 'hook',
        family: 'hook',
        confidence: 0.91,
        workflow: 'scan_world',
        dimensions_mm: { width: 80, height: 120, depth: 30 },
        tags: ['scan', 'hook', 'auto'],
      });
      setRecord(res.record);
    } catch (e) { console.warn(e); }
  };

  const appendEdit = async () => {
    if (!record?.id) return;
    try {
      const res = await appendEditFlow({
        record_id: record.id,
        type: 'reinforce_joint',
        before: { reinforcement: [] },
        after: { reinforcement: ['rib'] },
        reason: notes,
      });
      setRecord(res.record);
    } catch (e) { console.warn(e); }
  };

  const printComplete = async () => {
    if (!record?.id) return;
    try {
      const res = await completePrintFlow({
        record_id: record.id,
        printed: true,
        print_success: true,
        printer_id: 'prt_losangeles_1',
        material: 'PETG',
        rating: 5,
        notes: 'Printed successfully',
      });
      setRecord(res.record);
    } catch (e) { console.warn(e); }
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={{ padding:16, gap:12 }}>
      <Text style={styles.title}>Flow Actions</Text>
      <Text style={styles.subtitle}>Auto-write accepted scan, edits, and completed prints into Object DNA.</Text>
      <View style={styles.panel}>
        <Pressable style={styles.secondary} onPress={scanAccept}><Text style={styles.secondaryText}>Accepted Scan</Text></Pressable>
        <TextInput style={styles.input} value={notes} onChangeText={setNotes} placeholder="Edit reason" placeholderTextColor="#666" />
        <Pressable style={styles.secondary} onPress={appendEdit}><Text style={styles.secondaryText}>Append Edit</Text></Pressable>
        <Pressable style={styles.secondary} onPress={printComplete}><Text style={styles.secondaryText}>Complete Print</Text></Pressable>
      </View>
      {record ? (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>{record.title}</Text>
          <Text style={styles.meta}>ID: {record.id}</Text>
          <Text style={styles.meta}>Family: {record.object_dna?.geometry?.family || 'unknown'}</Text>
          <Text style={styles.meta}>Printed: {record.object_dna?.outcomes?.printed ? 'Yes' : 'No'}</Text>
          <Text style={styles.meta}>Print success: {record.object_dna?.outcomes?.print_success ? 'Yes' : 'No'}</Text>
          <Text style={styles.meta}>User edits: {(record.object_dna?.user_edits || []).length}</Text>
        </View>
      ) : null}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container:{ flex:1, backgroundColor:'#000' },
  title:{ color:'#fff', fontSize:24, fontWeight:'800' },
  subtitle:{ color:'#bdbdbd', fontSize:13, lineHeight:18 },
  panel:{ borderWidth:1, borderColor:'#1f1f1f', backgroundColor:'#0b0b0b', borderRadius:18, padding:14, gap:10 },
  card:{ borderWidth:1, borderColor:'#1f1f1f', backgroundColor:'#0b0b0b', borderRadius:18, padding:14, gap:6 },
  cardTitle:{ color:'#fff', fontSize:16, fontWeight:'800' },
  meta:{ color:'#bdbdbd', fontSize:12, lineHeight:18 },
  input:{ borderWidth:1, borderColor:'#222', borderRadius:12, padding:12, color:'#fff' },
  secondary:{ borderRadius:14, paddingVertical:12, paddingHorizontal:12, alignItems:'center', borderWidth:1, borderColor:'#2a2a2a' },
  secondaryText:{ color:'#fff', fontWeight:'800' },
});
