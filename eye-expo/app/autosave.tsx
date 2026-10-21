import * as React from 'react';
import { View, Text, StyleSheet, ScrollView } from 'react-native';

export default function AutoSaveScreen() {
  return (
    <ScrollView style={styles.container} contentContainerStyle={{ padding:16, gap:12 }}>
      <Text style={styles.title}>Auto-Save Unavailable</Text>
      <Text style={styles.subtitle}>Billing entitlements and durable project auto-save are not connected in this deployment. No subscription state has been changed.</Text>

      <View style={styles.panel}>
        <Text style={styles.meta}>Plan: Not verified</Text>
        <Text style={styles.body}>You can continue using the core scan and local model history. Permanent cloud project storage is not available here.</Text>
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
});
