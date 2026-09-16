export async function cutoutImage(uri: string): Promise<string> {
  if (!uri) throw new Error('No image provided for cutout.');
  return uri;
}
