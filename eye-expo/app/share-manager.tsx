import * as React from 'react';
import { View, Text, StyleSheet, Pressable, ScrollView, TextInput } from 'react-native';
import { createShareLink, listShareLinks } from '../src/lib/api';

export default function ShareManagerScreen() {
  const [title, setTitle] = React.useState('Chair Remix');
  const [creator, setCreator] = React.useState('Muepo');
  const [data, setData] = React.useState<any[]>([]);

  const load = async () => {
    try {
      const res = await listShareLinks(50);
      setData(res.links || []);
    } catch (e) { console.warn(e); }
  };

  React.useEffect(() => { load(); }, []);

  const createLink = async () => {
    try {
      await createShareLink({
        title,
        creator,
        preview_url: 'https://example.com/preview/chair-remix.png',
      });
      await load();
    } catch (e) { console.warn(e); }
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={{ padding:16, gap:12 }}>
      <Text style={styles.title}>Share Manager</Text>
      <View style={styles.panel}>
        <TextInput style={styles.input} value={title} onChangeText={setTitle} placeholder="Title" placeholderTextColor="#666" />
        <TextInput style={styles.input} value={creator} onChangeText={setCreator} placeholder="Creator" placeholderTextColor="#666" />
        <Pressable style={styles.primary} onPress={createLink}><Text style={styles.primaryText}>Create Share Link</Text></Pressable>
      </View>
      {data.map((item:any) => (
        <View key={item.id} style={styles.card}>
          <Text style={styles.cardTitle}>{item.title}</Text>
          <Text style={styles.meta}>Slug: {item.slug}</Text>
          <Text style={styles.meta}>Deep Link: {item.deep_link}</Text>
          <Text style={styles.meta}>Creator: {item.creator}</Text>
        </View>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container:{ flex:1, backgroundColor:'#000' },
  title:{ color:'#fff', fontSize:24, fontWeight:'800' },
  panel:{ borderWidth:1, borderColor:'#1f1f1f', backgroundColor:'#0b0b0b', borderRadius:18, padding:14, gap:10 },
  card:{ borderWidth:1, borderColor:'#1f1f1f', backgroundColor:'#0b0b0b', borderRadius:18, padding:14, gap:6 },
  cardTitle:{ color:'#fff', fontSize:16, fontWeight:'800' },
  meta:{ color:'#bdbdbd', fontSize:12, lineHeight:18 },
  input:{ borderWidth:1, borderColor:'#222', borderRadius:12, padding:12, color:'#fff' },
  primary:{ backgroundColor:'#fff', borderRadius:14, paddingVertical:14, alignItems:'center' },
  primaryText:{ color:'#000', fontWeight:'800' },
});
