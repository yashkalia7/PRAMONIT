import { Platform } from 'react-native';

function toHex(bytes: Uint8Array): string {
  let out = '';
  for (const byte of bytes) out += byte.toString(16).padStart(2, '0');
  return out;
}

/**
 * SHA-256 of the raw file bytes.
 *
 * Both platforms hash the *bytes*, never a base64 string, so the same video
 * produces the same digest whether it was submitted from the web app or from a
 * phone. If the two disagreed, a student could upload one clip twice by
 * switching device — which is exactly the cheat the hash exists to stop.
 */
export async function sha256Hex(bytes: Uint8Array): Promise<string> {
  // Copy into a view that is provably backed by a plain ArrayBuffer. Both
  // crypto.subtle and expo-crypto reject SharedArrayBuffer-backed views, which
  // is what the general Uint8Array type permits.
  const input = new Uint8Array(bytes);

  if (Platform.OS === 'web' && globalThis.crypto?.subtle) {
    const digest = await globalThis.crypto.subtle.digest('SHA-256', input);
    return toHex(new Uint8Array(digest));
  }

  const Crypto = await import('expo-crypto');
  const digest = await Crypto.digest(Crypto.CryptoDigestAlgorithm.SHA256, input);
  return toHex(new Uint8Array(digest));
}
