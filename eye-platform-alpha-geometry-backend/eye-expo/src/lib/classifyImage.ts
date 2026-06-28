export type DetectionResult = {
  label: string;
  confidence: number;
  promptNext: string;
  notes: string;
};

function fallbackFromUri(): DetectionResult {
  return {
    label: 'Object',
    confidence: 0.72,
    promptNext: 'Generate a first 3D draft from this photo. Add more angles only if you want higher accuracy.',
    notes: 'Local fallback used because online AI detection was unavailable.',
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
  const apiKey = process.env.EXPO_PUBLIC_OPENAI_API_KEY;

  if (!apiKey) return fallbackFromUri();

  try {
    const imageDataUrl = await uriToDataUrl(uri);
    const response = await fetch('https://api.openai.com/v1/responses', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${apiKey}`,
      },
      body: JSON.stringify({
        model: process.env.EXPO_PUBLIC_OPENAI_VISION_MODEL || 'gpt-4.1-mini',
        input: [
          {
            role: 'user',
            content: [
              {
                type: 'input_text',
                text:
                  'You are the vision module for a one-photo 3D scanning app. Identify the main object the user wants to scan. Return strict JSON only with keys: label, confidence, promptNext, notes. confidence must be 0 to 1. If the scene is cluttered, choose the strongest central object.',
              },
              { type: 'input_image', image_url: imageDataUrl },
            ],
          },
        ],
        text: {
          format: {
            type: 'json_schema',
            name: 'detection_result',
            schema: {
              type: 'object',
              additionalProperties: false,
              properties: {
                label: { type: 'string' },
                confidence: { type: 'number' },
                promptNext: { type: 'string' },
                notes: { type: 'string' },
              },
              required: ['label', 'confidence', 'promptNext', 'notes'],
            },
          },
        },
      }),
    });

    if (!response.ok) return fallbackFromUri();
    const data = await response.json();
    return parseOutput(data);
  } catch {
    return fallbackFromUri();
  }
}
