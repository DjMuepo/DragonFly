export type DetectionResult = {
  label: string;
  confidence: number;
  promptNext: string;
  notes: string;
};

function fallbackFromUri(): DetectionResult {
  return {
    label: 'Object',
    confidence: 0,
    promptNext: 'Generate a 3D model from this photo.',
    notes: 'Object classification is not configured; reconstruction uses the uploaded photo.',
  };
}

async function uriToDataUrl(uri: string): Promise<string> {
  const res = await fetch(uri);
  const blob = await res.blob();

  return await new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => resolve(String(reader.result));
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

function parseOutput(data: any): DetectionResult {
  const raw = data?.output_text ?? data?.output?.[0]?.content?.[0]?.text ?? data?.output?.[1]?.content?.[0]?.text;
  if (!raw || typeof raw !== 'string') return fallbackFromUri();
  const parsed = JSON.parse(raw);
  return {
    label: parsed.label || 'Object',
    confidence: typeof parsed.confidence === 'number' ? parsed.confidence : 0.72,
    promptNext: parsed.promptNext || 'Generate a 3D draft from this photo now.',
    notes: parsed.notes || '',
  };
}

export async function classifyImage(uri: string): Promise<DetectionResult> {
  if (!uri) throw new Error('No photo selected.');
  return fallbackFromUri();
}
