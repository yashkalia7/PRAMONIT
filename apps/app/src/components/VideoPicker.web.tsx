/**
 * Web video picker.
 *
 * Deliberately a real `<input type="file">` rather than expo-image-picker's web
 * shim: it is the element browsers and automated tests both understand, so the
 * Playwright suite can drive the genuine upload path instead of a mock.
 */

import React, { useRef } from 'react';

import { Button } from '@/components/ui';
import { normaliseMime, type PickedVideo } from '@/lib/video';

export function VideoPicker({
  onPick,
  onError,
  disabled,
  label = 'Choose a video',
}: {
  onPick: (video: PickedVideo) => void;
  onError?: (message: string) => void;
  disabled?: boolean;
  label?: string;
}) {
  const inputRef = useRef<HTMLInputElement | null>(null);

  const handleChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      const buffer = await file.arrayBuffer();
      onPick({
        name: file.name,
        mimeType: normaliseMime(file.type),
        size: file.size,
        bytes: new Uint8Array(buffer),
        source: 'web',
      });
    } catch {
      onError?.('Could not read that file. Try another video.');
    } finally {
      // Reset so picking the same file twice still fires onChange — which is
      // exactly what a student does after a failed upload.
      event.target.value = '';
    }
  };

  return (
    <>
      {React.createElement('input', {
        ref: inputRef,
        type: 'file',
        accept: 'video/*',
        'data-testid': 'video-file-input',
        onChange: handleChange,
        style: {
          position: 'absolute',
          width: 1,
          height: 1,
          opacity: 0,
          pointerEvents: 'none',
        },
      })}
      <Button
        label={label}
        testID="pick-video"
        variant="secondary"
        disabled={disabled}
        full
        onPress={() => inputRef.current?.click()}
      />
    </>
  );
}
