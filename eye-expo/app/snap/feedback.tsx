import { View, Text, StyleSheet, Pressable, TextInput, Image } from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import { useRouter } from 'expo-router';
import { useState } from 'react';
import { useSnapStore } from '../../src/lib/useSnapStore';
import { logEvent, uploadReviewPhoto } from '../../src/lib/api';


function Stars({ value, onChange }: { value: number; onChange: (v: number) => void }) {
  return (
    <View style={{ flexDirection: 'row', gap: 6, marginTop: 6 }}>
      {[1,2,3,4,5].map((n) => (
        <Pressable key={n} onPress={() => onChange(n)} style={{ padding: 6 }}>
          <Text style={{ fontSize: 20, color: n <= value ? '#fff' : '#555' }}>★</Text>
        </Pressable>
      ))}
    </View>
  );
}

function ScoreRow({ label, value, onChange }: { label: string; value: number; onChange: (v: number) => void }) {
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginTop: 10 }}>
      <Text style={{ color: '#bdbdbd' }}>{label}</Text>
      <View style={{ flexDirection: 'row', gap: 6 }}>
        {[1,2,3,4,5].map((n) => (
          <Pressable key={n} onPress={() => onChange(n)} style={{ paddingHorizontal: 10, paddingVertical: 6, borderRadius: 999, borderWidth: 1, borderColor: n === value ? '#fff' : '#222', backgroundColor: n === value ? '#111' : '#060606' }}>
            <Text style={{ color: n === value ? '#fff' : '#888', fontWeight: '700', fontSize: 12 }}>{n}</Text>
          </Pressable>
        ))}
      </View>
    </View>
  );
}

export default function Feedback() {
  const router = useRouter();
  const [notes, setNotes] = useState('');
  const [rating, setRating] = useState(5);
  const [fit, setFit] = useState(5);
  const [strength, setStrength] = useState(5);
  const [finish, setFinish] = useState(5);
  const [ease, setEase] = useState(5);
  const [photoUri, setPhotoUri] = useState<string | null>(null);

  const [failure, setFailure] = useState<'none'|'warping'|'layer_shift'|'weak'|'fit'|'supports'|'other'>('none');

  const sessionId = useSnapStore((s) => (s as any).sessionId);
  const selectedMatchId = useSnapStore((s) => s.selectedMatchId);
  const structuralReport = useSnapStore((s) => (s as any).structuralReport);

  const pickPhoto = async () => {
    const perm = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!perm.granted) return;
    const res = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ImagePicker.MediaTypeOptions.Images, quality: 0.7 });
    if (res.canceled) return;
    const uri = res.assets?.[0]?.uri;
    if (uri) {
      setPhotoUri(uri);
      let uploadedFilename = null;
    if (photoUri) {
      const res = await uploadReviewPhoto(photoUri);
      uploadedFilename = res?.filename ?? null;
    }

    logEvent({ event: 'review_photo_selected', session_id: sessionId, model_id: selectedMatchId ?? undefined, payload: { uri_present: true } });
    }
  };

  const submit = async () => {
    let uploadedFilename = null;
    if (photoUri) {
      const res = await uploadReviewPhoto(photoUri);
      uploadedFilename = res?.filename ?? null;
    }

    logEvent({
      event: 'print_feedback',
      session_id: sessionId,
      model_id: selectedMatchId ?? undefined,
      payload: {
        failure,
        notes,
        confidence: structuralReport?.confidence,
        review: { rating, fit, strength, finish, ease },
        photo_attached: !!photoUri,
        photo_filename: uploadedFilename,
      },
    });
    let uploadedFilename = null;
    if (photoUri) {
      const res = await uploadReviewPhoto(photoUri);
      uploadedFilename = res?.filename ?? null;
    }

    logEvent({ event: 'review_submit', session_id: sessionId, model_id: selectedMatchId ?? undefined, payload: { rating, fit, strength, finish, ease, failure, photo_attached: !!photoUri } });
    router.back();
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Print Feedback</Text>
      <Text style={styles.subtitle}>Optional details help the AI improve future suggestions.</Text>

      <View style={styles.panel}>
        <Text style={styles.label}>Overall rating</Text>
        <Stars value={rating} onChange={setRating} />

        <Text style={[styles.label, { marginTop: 12 }]}>Grade this print (1–5)</Text>
        <ScoreRow label="Fit" value={fit} onChange={setFit} />
        <ScoreRow label="Strength" value={strength} onChange={setStrength} />
        <ScoreRow label="Finish" value={finish} onChange={setFinish} />
        <ScoreRow label="Ease of printing" value={ease} onChange={setEase} />

        <Text style={[styles.label, { marginTop: 12 }]}>Optional photo</Text>
        <Pressable style={[styles.secondary, { borderWidth: 1, borderColor: '#2a2a2a', backgroundColor: '#0b0b0b' }]} onPress={pickPhoto}>
          <Text style={styles.secondaryText}>{photoUri ? 'Change photo' : 'Upload photo (optional)'}</Text>
        </Pressable>
        {photoUri ? (
          <Image source={{ uri: photoUri }} style={{ width: '100%', height: 180, borderRadius: 14, marginTop: 10, borderWidth: 1, borderColor: '#1f1f1f' }} />
        ) : null}

        <Text style={styles.label}>What went wrong (if anything)?</Text>

        <View style={styles.row}>
          {[
            ['none','No issues'],
            ['warping','Warping'],
            ['layer_shift','Layer shift'],
            ['weak','Too weak/broke'],
            ['fit','Didn’t fit'],
            ['supports','Support problems'],
            ['other','Other'],
          ].map(([k, t]) => (
            <Pressable
              key={k}
              onPress={() => setFailure(k as any)}
              style={[styles.chip, failure === k ? styles.chipOn : styles.chipOff]}
            >
              <Text style={{ color: failure === k ? '#fff' : '#bdbdbd', fontWeight: '700', fontSize: 12 }}>{t}</Text>
            </Pressable>
          ))}
        </View>

        <Text style={[styles.label, { marginTop: 10 }]}>Notes (optional)</Text>
        <TextInput
          value={notes}
          onChangeText={setNotes}
          placeholder="What happened? What printer/material?"
          placeholderTextColor="#666"
          style={styles.input}
          multiline
        />
      </View>

      <View style={styles.actions}>
        <Pressable style={styles.primary} onPress={submit}>
          <Text style={styles.primaryText}>Submit</Text>
        </Pressable>
        <Pressable style={styles.secondary} onPress={() => router.back()}>
          <Text style={styles.secondaryText}>Cancel</Text>
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
  label: { color: '#bdbdbd', marginBottom: 8 },
  row: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  chip: { paddingHorizontal: 12, paddingVertical: 8, borderRadius: 999, borderWidth: 1 },
  chipOn: { borderColor: '#fff', backgroundColor: '#111' },
  chipOff: { borderColor: '#222', backgroundColor: '#060606' },
  input: { borderWidth: 1, borderColor: '#222', borderRadius: 14, padding: 12, color: '#fff', minHeight: 90, marginTop: 6 },
  actions: { marginTop: 'auto', gap: 10, paddingBottom: 8 },
  primary: { backgroundColor: '#fff', borderRadius: 14, paddingVertical: 14, alignItems: 'center' },
  primaryText: { color: '#000', fontWeight: '800', fontSize: 16 },
  secondary: { borderRadius: 14, paddingVertical: 14, alignItems: 'center', backgroundColor: '#0b0b0b', borderWidth: 1, borderColor: '#2a2a2a' },
  secondaryText: { color: '#fff', fontWeight: '800' },
});
