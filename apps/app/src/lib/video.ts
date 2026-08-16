/** Shared shape for a video the student has chosen, whatever the platform. */

export type PickedVideo = {
  name: string;
  mimeType: string;
  size: number;
  /** Present on web — the raw bytes, ready to hash and PUT. */
  bytes?: Uint8Array;
  /** Present on native — a file:// URI that expo-file-system streams. */
  uri?: string;
  durationSec?: number | null;
  /** 'gallery' or 'camera' on native; always 'web' in a browser. */
  source: 'camera' | 'gallery' | 'web';
};

export const ACCEPTED_MIME = [
  'video/mp4',
  'video/quicktime',
  'video/webm',
  'video/x-matroska',
  'video/3gpp',
] as const;

/** The API only accepts a known set; anything odd is coerced to mp4. */
export function normaliseMime(mime: string | undefined | null): string {
  if (!mime) return 'video/mp4';
  const lower = mime.toLowerCase().split(';')[0].trim();
  return (ACCEPTED_MIME as readonly string[]).includes(lower) ? lower : 'video/mp4';
}

export function formatBytes(size: number): string {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(0)} KB`;
  return `${(size / 1024 / 1024).toFixed(1)} MB`;
}
