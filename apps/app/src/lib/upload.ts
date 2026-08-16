/**
 * The upload pipeline.
 *
 * Four steps, in this exact order:
 *   1. hash the file locally
 *   2. exchange the hash for a presigned target — a duplicate is refused HERE,
 *      before a single byte crosses the network
 *   3. PUT the bytes straight to storage; the API never proxies video
 *   4. commit the submission record
 *
 * Identical in development (local disk) and production (Cloudflare R2), because
 * both sign the same kind of URL.
 */

import { Platform } from 'react-native';

import { ApiError } from '@/api/client';
import { endpoints } from '@/api/endpoints';
import type { Submission } from '@/api/types';
import { sha256Hex } from '@/lib/hash';
import type { PickedVideo } from '@/lib/video';

export type UploadStage = 'hashing' | 'requesting' | 'uploading' | 'saving' | 'done';

export type UploadArgs = {
  video: PickedVideo;
  drillId?: string | null;
  repsClaimed?: number | null;
  note?: string | null;
  onStage?: (stage: UploadStage) => void;
};

async function readBytes(video: PickedVideo): Promise<Uint8Array> {
  if (video.bytes) return video.bytes;
  if (!video.uri) throw new Error('No video data to upload.');

  // Native: read the file off disk once, so the hash and the uploaded bytes are
  // guaranteed to describe the same content. expo-file-system's File implements
  // Blob, so this is the same call the web path makes.
  const { File } = await import('expo-file-system');
  const buffer = await new File(video.uri).arrayBuffer();
  return new Uint8Array(buffer);
}

export async function uploadSubmission({
  video,
  drillId,
  repsClaimed,
  note,
  onStage,
}: UploadArgs): Promise<Submission> {
  onStage?.('hashing');
  const bytes = await readBytes(video);
  const contentHash = await sha256Hex(bytes);

  onStage?.('requesting');
  const target = await endpoints.uploadTarget({
    content_type: video.mimeType,
    content_hash: contentHash,
    content_length: bytes.byteLength || video.size || undefined,
  });

  onStage?.('uploading');
  // One code path for every platform: PUT the raw bytes at the presigned URL.
  // The bytes go straight to storage — the API never proxies video content.
  const response = await fetch(target.upload_url, {
    method: target.method,
    headers: target.headers,
    body: bytes as unknown as BodyInit,
  });
  if (!response.ok) {
    throw new ApiError(response.status, null, `Upload failed (${response.status}).`);
  }

  onStage?.('saving');
  const submission = await endpoints.createSubmission({
    video_key: target.video_key,
    content_hash: contentHash,
    drill_id: drillId ?? null,
    duration_sec: video.durationSec ?? null,
    file_size_bytes: bytes.byteLength || video.size || null,
    mime_type: video.mimeType,
    source: video.source,
    reps_claimed: repsClaimed ?? null,
    student_note: note ?? null,
  });

  onStage?.('done');
  return submission;
}

export const STAGE_LABEL: Record<UploadStage, string> = {
  hashing: 'Fingerprinting your video…',
  requesting: 'Checking it hasn’t been submitted before…',
  uploading: 'Uploading…',
  saving: 'Sending to your coach…',
  done: 'Done',
};
