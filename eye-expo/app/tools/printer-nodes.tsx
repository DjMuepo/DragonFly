import * as React from 'react';
import { View, Text, StyleSheet, Pressable, FlatList } from 'react-native';
import { useRouter } from 'expo-router';
import { listPrinterNodes, updatePrinterNodeStatus } from '../../src/lib/api';

export default function PrinterNodesTool() {
  const router = useRouter();
  const [nodes, setNodes] = React.useState<any[]>([]);

  const load = async () => {
    try {
      const res = await listPrinterNodes();
      setNodes(res.nodes || []);
    } catch (e) {
      console.warn(e);
    }
  };

  React.useEffect(() => { load(); }, []);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Printer Nodes</Text>
      <Text style={styles.subtitle}>Monitor online state and queue depth for nearby print partners.</Text>
      <FlatList
        data={nodes}
        keyExtractor={(item:any) => item.id}
        renderItem={({ item }: any) => (
          <View style={styles.card}>
            <Text style={styles.cardTitle}>{item.name}</Text>
            <Text style={styles.meta}>Online: {item.is_online ? 'Yes' : 'No'} • Queue: {item.queue_depth}</Text>
            <Text style={styles.meta}>Materials: {(item.materials || []).join(', ')}</Text>
            <View style={{ flexDirection:'row', gap:10, marginTop:8 }}>
              <Pressable style={styles.secondary} onPress={async () => { await updatePrinterNodeStatus(item.id, { is_online: !item.is_online }); await load(); }}>
                <Text style={styles.secondaryText}>{item.is_online ? 'Mark Offline' : 'Mark Online'}</Text>
              </Pressable>
              <Pressable style={styles.secondary} onPress={async () => { await updatePrinterNodeStatus(item.id, { queue_depth: Math.max(0, (item.queue_depth || 0) + 1) }); await load(); }}>
                <Text style={styles.secondaryText}>+ Queue</Text>
              </Pressable>
            </View>
          </View>
        )}
        contentContainerStyle={{ gap: 10, paddingBottom: 20 }}
      />
      <Pressable style={styles.primary} onPress={load}><Text style={styles.primaryText}>Refresh</Text></Pressable>
      <Pressable style={styles.secondaryBottom} onPress={() => router.back()}><Text style={styles.secondaryText}>Back</Text></Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  container:{ flex:1, backgroundColor:'#000', padding:16, gap:12 },
  title:{ color:'#fff', fontSize:24, fontWeight:'800' },
  subtitle:{ color:'#bdbdbd', fontSize:13, lineHeight:18 },
  card:{ borderWidth:1, borderColor:'#1f1f1f', backgroundColor:'#0b0b0b', borderRadius:18, padding:14, gap:6 },
  cardTitle:{ color:'#fff', fontWeight:'800', fontSize:16 },
  meta:{ color:'#bdbdbd', fontSize:12, lineHeight:18 },
  secondary:{ borderRadius:14, paddingVertical:10, paddingHorizontal:12, alignItems:'center', borderWidth:1, borderColor:'#2a2a2a' },
  primary:{ backgroundColor:'#fff', borderRadius:14, paddingVertical:14, alignItems:'center' },
  primaryText:{ color:'#000', fontWeight:'800' },
  secondaryBottom:{ borderRadius:14, paddingVertical:14, alignItems:'center', borderWidth:1, borderColor:'#2a2a2a', marginBottom:24 },
  secondaryText:{ color:'#fff', fontWeight:'800' },
});
