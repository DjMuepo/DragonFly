import * as React from 'react';
import { View, Text, StyleSheet, Pressable, ScrollView, TextInput } from 'react-native';
import { getAdminFeatures, updateAdminFeature, setAdminFeatureOverride, getAdminFeatureAudit } from '../src/lib/api';

export default function AdminAccessScreen() {
  const [data, setData] = React.useState<any>(null);
  const [audit, setAudit] = React.useState<any[]>([]);
  const [userId, setUserId] = React.useState('beta_user_1');

  const load = async () => {
    try {
      const [features, log] = await Promise.all([getAdminFeatures(), getAdminFeatureAudit(20)]);
      setData(features.data);
      setAudit(log.audit_log || []);
    } catch (e) { console.warn(e); }
  };

  React.useEffect(() => { load(); }, []);

  const toggleEnabled = async (featureKey: string, enabled: boolean) => {
    await updateAdminFeature({ feature_key: featureKey, enabled: !enabled, actor: 'owner_admin' });
    await load();
  };

  const cycleTier = async (featureKey: string, tier: string) => {
    const next = tier === 'free' ? 'pro' : tier === 'pro' ? 'enterprise' : 'free';
    await updateAdminFeature({ feature_key: featureKey, default_tier: next, actor: 'owner_admin' });
    await load();
  };

  const overrideAllow = async (featureKey: string) => {
    await setAdminFeatureOverride({ feature_key: featureKey, user_id: userId, forced_access: 'allow', actor: 'owner_admin' });
    await load();
  };

  const overrideDeny = async (featureKey: string) => {
    await setAdminFeatureOverride({ feature_key: featureKey, user_id: userId, forced_access: 'deny', actor: 'owner_admin' });
    await load();
  };

  const clearOverride = async (featureKey: string) => {
    await setAdminFeatureOverride({ feature_key: featureKey, user_id: userId, forced_access: 'clear', actor: 'owner_admin' });
    await load();
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={{ padding:16, gap:12 }}>
      <Text style={styles.title}>Admin Access Control</Text>
      <Text style={styles.subtitle}>Control what is free, paid, off, or user-overridden at any time.</Text>

      <View style={styles.panel}>
        <Text style={styles.meta}>Target user override ID</Text>
        <TextInput style={styles.input} value={userId} onChangeText={setUserId} placeholder="beta_user_1" placeholderTextColor="#666" />
      </View>

      {Object.entries((data?.features || {})).map(([key, feature]: any) => (
        <View key={key} style={styles.card}>
          <Text style={styles.cardTitle}>{key}</Text>
          <Text style={styles.meta}>Enabled: {feature.enabled ? 'Yes' : 'No'}</Text>
          <Text style={styles.meta}>Default tier: {feature.default_tier}</Text>
          <Text style={styles.meta}>{feature.description}</Text>
          <View style={{ gap:8 }}>
            <Pressable style={styles.secondary} onPress={() => toggleEnabled(key, feature.enabled)}>
              <Text style={styles.secondaryText}>{feature.enabled ? 'Turn Off' : 'Turn On'}</Text>
            </Pressable>
            <Pressable style={styles.secondary} onPress={() => cycleTier(key, feature.default_tier)}>
              <Text style={styles.secondaryText}>Cycle Tier</Text>
            </Pressable>
            <Pressable style={styles.secondary} onPress={() => overrideAllow(key)}>
              <Text style={styles.secondaryText}>Allow For User</Text>
            </Pressable>
            <Pressable style={styles.secondary} onPress={() => overrideDeny(key)}>
              <Text style={styles.secondaryText}>Deny For User</Text>
            </Pressable>
            <Pressable style={styles.secondary} onPress={() => clearOverride(key)}>
              <Text style={styles.secondaryText}>Clear Override</Text>
            </Pressable>
          </View>
        </View>
      ))}

      <View style={styles.panel}>
        <Text style={styles.sectionTitle}>Audit Log</Text>
        {audit.map((item:any, idx:number) => (
          <Text key={idx} style={styles.meta}>• {item.type} — {item.feature_key} — {item.actor}</Text>
        ))}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container:{ flex:1, backgroundColor:'#000' },
  title:{ color:'#fff', fontSize:24, fontWeight:'800' },
  subtitle:{ color:'#bdbdbd', fontSize:13, lineHeight:18 },
  panel:{ borderWidth:1, borderColor:'#1f1f1f', backgroundColor:'#0b0b0b', borderRadius:18, padding:14, gap:10 },
  card:{ borderWidth:1, borderColor:'#1f1f1f', backgroundColor:'#0b0b0b', borderRadius:18, padding:14, gap:8 },
  cardTitle:{ color:'#fff', fontSize:16, fontWeight:'800' },
  sectionTitle:{ color:'#fff', fontSize:16, fontWeight:'800' },
  meta:{ color:'#bdbdbd', fontSize:12, lineHeight:18 },
  input:{ borderWidth:1, borderColor:'#222', borderRadius:12, padding:12, color:'#fff' },
  secondary:{ borderRadius:14, paddingVertical:10, paddingHorizontal:12, alignItems:'center', borderWidth:1, borderColor:'#2a2a2a' },
  secondaryText:{ color:'#fff', fontWeight:'800' },
});
