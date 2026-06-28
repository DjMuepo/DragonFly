import { View, Text, StyleSheet, Pressable, Animated } from 'react-native';
import { useRouter } from 'expo-router';
import * as React from 'react';
import { useSnapStore } from '../../src/lib/useSnapStore';
import { IS_PRO } from '../../src/lib/config';
import { logEvent, simulateBasic } from '../../src/lib/api';

export default function Demo() {
  const router = useRouter();
  const [force, setForce] = React.useState(1);
  const [mode, setMode] = React.useState<'custom'|'drop'|'side_load'|'twist'>('custom');
  const sessionId = useSnapStore((s) => (s as any).sessionId);
  const structuralParams = useSnapStore((s) => (s as any).structuralParams);
  const [simResult, setSimResult] = React.useState<{deflection_score:number; risk:string; force:number} | null>(null);
  const [loading, setLoading] = React.useState(false);
  const riskColor = (r?: string) => (r === 'LOW' ? '#2bd576' : r === 'MED' ? '#f2c94c' : '#eb5757');
  const loadAccent = (lt?: string) => {
    const s = (lt || '').toLowerCase();
    if (s.includes('shear')) return '#56ccf2';
    if (s.includes('torsion')) return '#bb6bd9';
    if (s.includes('compression')) return '#2d9cdb';
    if (s.includes('tension')) return '#f2994a';
    if (s.includes('bending')) return '#27ae60';
    return '#888';
  };

  const deflectAnim = React.useRef(new Animated.Value(0)).current;

  const bump = (d: number) => setForce((f) => Math.max(0.5, Math.min(10, Math.round((f + d) * 10) / 10)));

  const runSim = async () => {
    try {
      setLoading(true);
      const r = await simulateBasic(structuralParams, force, mode);
      setSimResult(r);
      Animated.timing(deflectAnim, { toValue: Math.max(0, Math.min(100, r.deflection_score || 0)), duration: 450, useNativeDriver: false }).start();
      logEvent({ event: 'demo_simulate', session_id: sessionId, payload: { mode, force, result: r, params: structuralParams } });
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  // Auto-run sim when force/params change
  React.useEffect(() => {
    if (!IS_PRO) return;
    runSim();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, force, structuralParams?.thickness, structuralParams?.has_rib, structuralParams?.has_fillet, structuralParams?.hole_count, structuralParams?.cantilever, structuralParams?.aspect_ratio, structuralParams?.joint_type]);

  const openPro = () => {
    logEvent({ event: 'pro_gate_demo', session_id: sessionId, payload: { wanted: true } });
    router.back();
  };

  if (!IS_PRO) {
    return (
      <View style={styles.container}>
        <Text style={styles.title}>Demo Mode</Text>
        <Text style={styles.subtitle}>Virtual testing is a Pro feature.</Text>

        <View style={styles.panel}>
          <Text style={styles.label}>What you’ll get:</Text>
          <Text style={styles.bullet}>• Apply force + see deflection</Text>
          <Text style={styles.bullet}>• Risk level (LOW / MED / HIGH)</Text>
          <Text style={styles.bullet}>• Future: real physics + collision</Text>
        </View>

        <View style={styles.actions}>
          <Pressable style={styles.primary} onPress={openPro}>
            <Text style={styles.primaryText}>Unlock Pro</Text>
          </Pressable>
          <Pressable style={styles.secondary} onPress={() => router.back()}>
            <Text style={styles.secondaryText}>Back</Text>
          </Pressable>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Demo Mode</Text>
      <Text style={styles.subtitle}>Apply a force and estimate deflection (basic sim).</Text>

      <View style={styles.panel}>
        <Text style={styles.label}>Presets</Text>
        <View style={{ flexDirection: 'row', gap: 10, marginTop: 10 }}>
          <Pressable style={styles.secondary} onPress={() => { setMode('drop'); logEvent({ event: 'demo_preset', session_id: sessionId, payload: { preset: 'drop' } }); }}>
            <Text style={styles.secondaryText}>Drop Test</Text>
          </Pressable>
          <Pressable style={styles.secondary} onPress={() => { setMode('side_load'); logEvent({ event: 'demo_preset', session_id: sessionId, payload: { preset: 'side_load' } }); }}>
            <Text style={styles.secondaryText}>Side Load</Text>
          </Pressable>
        </View>
        <View style={{ flexDirection: 'row', gap: 10, marginTop: 10 }}>
          <Pressable style={styles.secondary} onPress={() => { setMode('twist'); logEvent({ event: 'demo_preset', session_id: sessionId, payload: { preset: 'twist' } }); }}>
            <Text style={styles.secondaryText}>Twist</Text>
          </Pressable>
          <Pressable style={styles.secondary} onPress={() => { setMode('custom'); logEvent({ event: 'demo_preset', session_id: sessionId, payload: { preset: 'custom' } }); }}>
            <Text style={styles.secondaryText}>Custom</Text>
          </Pressable>
        </View>

        <Text style={[styles.label, { marginTop: 12 }]}>Force</Text>
        <Text style={styles.big}>{force.toFixed(1)}</Text>

        <View style={{ flexDirection: 'row', gap: 10, marginTop: 10 }}>
          <Pressable style={styles.secondary} onPress={() => bump(-0.5)}><Text style={styles.secondaryText}>-</Text></Pressable>
          <Pressable style={styles.secondary} onPress={() => bump(+0.5)}><Text style={styles.secondaryText}>+</Text></Pressable>
        </View>

        <Text style={[styles.label, { marginTop: 14 }]}>Simulation</Text>
        <View style={{ borderWidth: 1, borderColor: '#222', backgroundColor: '#060606', borderRadius: 14, padding: 12, marginTop: 8 }}>
          <Text style={{ color: '#fff', fontWeight: '800' }}>{loading ? 'Running…' : (simResult ? `Risk: ${simResult.risk} • ${simResult.load_type ?? ''}` : 'No result')}</Text>
          {simResult ? (
            <>
              <Text style={{ color: '#bdbdbd', marginTop: 6 }}>Deflection score: {Math.round(simResult.deflection_score)} / 100</Text>
              <Text style={{ color: '#bdbdbd', marginTop: 10, fontSize: 12 }}>Deflection Visual</Text>
              <View style={{ height: 14, borderRadius: 999, backgroundColor: '#111', overflow: 'hidden', marginTop: 6 }}>
                <Animated.View
                  style={{
                    height: 14,
                    width: deflectAnim.interpolate({ inputRange: [0, 100], outputRange: ['0%', '100%'] }),
                    backgroundColor: simResult.risk === 'LOW' ? '#2bd576' : simResult.risk === 'MED' ? '#f2c94c' : '#eb5757',
                  }}
                />
              </View>
              <View style={{ marginTop: 12, alignItems: 'center' }}>
                <View style={{ width: '100%', height: 86, borderRadius: 16, borderWidth: 1, borderColor: simResult ? riskColor(simResult.risk) : '#1f1f1f', backgroundColor: '#050505', padding: 14, shadowColor: simResult ? riskColor(simResult.risk) : '#000', shadowOpacity: simResult ? 0.35 : 0, shadowRadius: 14, shadowOffset: { width: 0, height: 0 } }}>
                  <Text style={{ color: '#bdbdbd', fontSize: 12 }}>Bend preview (toy)</Text>
                  <Animated.View
                    style={{
                      width: 160,
                      height: 14,
                      borderRadius: 10,
                      backgroundColor: simResult ? loadAccent(simResult.load_type) : '#fff',
                      shadowColor: simResult ? loadAccent(simResult.load_type) : '#fff',
                      shadowOpacity: simResult ? (simResult.risk === 'HIGH' ? 0.5 : simResult.risk === 'MED' ? 0.35 : 0.2) : 0.15,
                      shadowRadius: 12,
                      shadowOffset: { width: 0, height: 0 },
                      marginTop: 12,
                      transform: [
                        {
                          rotateZ: deflectAnim.interpolate({ inputRange: [0, 100], outputRange: ['0deg', '12deg'] }),
                        },
                        {
                          translateX: deflectAnim.interpolate({ inputRange: [0, 100], outputRange: [0, 10] }),
                        },
                      ],
                      opacity: 0.9,
                    }}
                  />
                </View>
              </View>
            </>
          ) : null}
          <Pressable style={[styles.secondary, { marginTop: 10, flex: undefined }]} onPress={runSim}>
            <Text style={styles.secondaryText}>{loading ? 'Working…' : 'Re-run simulation'}</Text>
          </Pressable>
        </View>

        <Text style={[styles.label, { marginTop: 14 }]}>Params snapshot</Text>
        <Text style={styles.mono}>{JSON.stringify(structuralParams, null, 2)}</Text>
      </View>

      <View style={styles.actions}>
        <Pressable style={styles.primary} onPress={() => router.back()}>
          <Text style={styles.primaryText}>Done</Text>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#000', padding: 16, gap: 12 },
  title: { color: '#fff', fontSize: 24, fontWeight: '800' },
  subtitle: { color: '#bdbdbd', fontSize: 13, lineHeight: 18 },
  panel: { borderWidth: 1, borderColor: '#1f1f1f', backgroundColor: '#0b0b0b', borderRadius: 18, padding: 14 },
  label: { color: '#bdbdbd' },
  bullet: { color: '#fff', marginTop: 6 },
  big: { color: '#fff', fontSize: 40, fontWeight: '900', marginTop: 6 },
  mono: { color: '#bdbdbd', fontFamily: 'Courier', fontSize: 12, marginTop: 8 },
  actions: { marginTop: 'auto', gap: 10, paddingBottom: 8 },
  primary: { backgroundColor: '#fff', borderRadius: 14, paddingVertical: 14, alignItems: 'center' },
  primaryText: { color: '#000', fontWeight: '800', fontSize: 16 },
  secondary: { borderRadius: 14, paddingVertical: 14, alignItems: 'center', backgroundColor: '#0b0b0b', borderWidth: 1, borderColor: '#2a2a2a', flex: 1 },
  secondaryText: { color: '#fff', fontWeight: '800' },
});
