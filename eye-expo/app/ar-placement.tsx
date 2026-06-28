import * as React from 'react';
import { View, Text, StyleSheet, Pressable, ScrollView, TextInput } from 'react-native';
import { useRouter } from 'expo-router';
import { generateArPlacementPlan } from '../src/lib/api';

const SURFACES = ['desk', 'wall', 'floor', 'shelf'];
const FAMILIES = ['hook', 'bracket', 'container', 'support', 'clip'];

export default function ARPlacementScreen() {
  const router = useRouter();
  const [surface, setSurface] = React.useState('desk');
  const [family, setFamily] = React.useState('container');
  const [title, setTitle] = React.useState('My Design');
  const [result, setResult] = React.useState<any>(null);

  const runPlan = async () => {
    try {
      const res = await generateArPlacementPlan({
        design_title: title,
        family,
        surface,
        width_mm: 120,
        height_mm: 90,
        depth_mm: 80,
      });
      setResult(res);
    } catch (e) {
      console.warn(e);
    }
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={{ padding:16, gap:12 }}>
      <Text style={styles.title}>AR Object Placement</Text>
      <Text style={styles.subtitle}>Preview how a design fits in the real world before printing.</Text>

      <View style={styles.panel}>
        <Text style={styles.meta}>Design title</Text>
        <TextInput
          style={styles.input}
          value={title}
          onChangeText={setTitle}
          placeholder="My Design"
          placeholderTextColor="#666"
        />
      </View>

      <View style={styles.panel}>
        <Text style={styles.sectionTitle}>Select family</Text>
        {FAMILIES.map((item) => (
          <Pressable key={item} style={styles.secondary} onPress={() => setFamily(item)}>
            <Text style={styles.secondaryText}>{family === item ? `✓ ${item}` : item}</Text>
          </Pressable>
        ))}
      </View>

      <View style={styles.panel}>
        <Text style={styles.sectionTitle}>Select surface</Text>
        {SURFACES.map((item) => (
          <Pressable key={item} style={styles.secondary} onPress={() => setSurface(item)}>
            <Text style={styles.secondaryText}>{surface === item ? `✓ ${item}` : item}</Text>
          </Pressable>
        ))}
      </View>

      <Pressable style={styles.primary} onPress={runPlan}>
        <Text style={styles.primaryText}>Generate AR placement plan</Text>
      </Pressable>

      {result ? (
        <View style={styles.panel}>
          <Text style={styles.sectionTitle}>Placement Plan</Text>
          <Text style={styles.meta}>Surface: {result.surface}</Text>
          <Text style={styles.meta}>Placement mode: {result.placement_mode}</Text>
          <Text style={styles.sectionTitle}>Instructions</Text>
          {(result.instructions || []).map((item:string, idx:number) => (
            <Text key={idx} style={styles.meta}>• {item}</Text>
          ))}
          <Text style={styles.sectionTitle}>Fit checks</Text>
          {((result.fit_checks || []).length ? result.fit_checks : ['No special checks']).map((item:string, idx:number) => (
            <Text key={idx} style={styles.meta}>• {item}</Text>
          ))}
          <Text style={styles.sectionTitle}>AR preview controls</Text>
          <Text style={styles.meta}>Bounding box: {result.ar_preview?.show_bounding_box ? 'On' : 'Off'}</Text>
          <Text style={styles.meta}>Shadow: {result.ar_preview?.show_shadow ? 'On' : 'Off'}</Text>
          <Text style={styles.meta}>Rotation: {result.ar_preview?.allow_rotation ? 'On' : 'Off'}</Text>
          <Text style={styles.meta}>Scaling: {result.ar_preview?.allow_scaling ? 'On' : 'Off'}</Text>
        </View>
      ) : null}

      <Pressable style={styles.secondaryBottom} onPress={() => router.back()}>
        <Text style={styles.secondaryText}>Back</Text>
      </Pressable>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container:{ flex:1, backgroundColor:'#000' },
  title:{ color:'#fff', fontSize:24, fontWeight:'800' },
  subtitle:{ color:'#bdbdbd', fontSize:13, lineHeight:18 },
  panel:{ borderWidth:1, borderColor:'#1f1f1f', backgroundColor:'#0b0b0b', borderRadius:18, padding:14, gap:10 },
  input:{ borderWidth:1, borderColor:'#222', borderRadius:12, padding:12, color:'#fff' },
  sectionTitle:{ color:'#fff', fontSize:16, fontWeight:'800' },
  meta:{ color:'#bdbdbd', fontSize:12, lineHeight:18 },
  primary:{ backgroundColor:'#fff', borderRadius:14, paddingVertical:14, alignItems:'center' },
  primaryText:{ color:'#000', fontWeight:'800' },
  secondary:{ borderRadius:14, paddingVertical:12, paddingHorizontal:12, alignItems:'center', borderWidth:1, borderColor:'#2a2a2a' },
  secondaryBottom:{ borderRadius:14, paddingVertical:14, alignItems:'center', borderWidth:1, borderColor:'#2a2a2a', marginBottom:24 },
  secondaryText:{ color:'#fff', fontWeight:'800' },
});
