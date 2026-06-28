import { View, Text, StyleSheet } from 'react-native';
import { Novelty } from '../lib/useSnapStore';

export default function ConfidenceBadge({ novelty }: { novelty: Novelty }) {
  const label = novelty === 'COMMON'
    ? 'Common (high match)'
    : novelty === 'SOMEWHAT_UNIQUE'
    ? 'Somewhat unique'
    : 'Likely unique';

  return (
    <View style={styles.badge}>
      <Text style={styles.text}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: '#1f1f1f',
    backgroundColor: '#0b0b0b',
  },
  text: { color: '#fff', fontSize: 12, fontWeight: '700' },
});
