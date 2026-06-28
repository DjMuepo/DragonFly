import { View, Text, StyleSheet } from 'react-native';
import { LicenseStatus } from '../lib/useSnapStore';

export default function LicenseBadge({ status }: { status: LicenseStatus }) {
  const label = status === 'OK' ? 'License OK' : status === 'RESTRICTED' ? 'Restricted' : 'Unknown';
  const style = status === 'OK' ? styles.ok : status === 'RESTRICTED' ? styles.restricted : styles.unknown;
  return (
    <View style={[styles.badge, style]}>
      <Text style={styles.text}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    paddingVertical: 6,
    paddingHorizontal: 10,
    borderRadius: 999,
    borderWidth: 1,
  },
  text: { color: '#fff', fontSize: 12, fontWeight: '700' },
  ok: { borderColor: 'rgba(255,255,255,0.25)', backgroundColor: 'rgba(255,255,255,0.08)' },
  unknown: { borderColor: 'rgba(255,255,255,0.18)', backgroundColor: 'rgba(255,255,255,0.04)' },
  restricted: { borderColor: 'rgba(255,255,255,0.28)', backgroundColor: 'rgba(255,255,255,0.02)' }
});
