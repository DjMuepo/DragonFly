export async function cutoutImage(uri: string): Promise<string> {
  if (!uri) throw new Error('No image provided for cutout.');
  // MVP: this is the isolated-image slot. Replace internals with SAM/Grounded-SAM backend later.
  await new Promise((resolve) => setTimeout(resolve, 600));
  return uri;
}
