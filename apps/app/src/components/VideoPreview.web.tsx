/** Web video player — a real <video> element, so scrubbing and Range work. */

import React from 'react';
import { View } from 'react-native';

import { colors, radius } from '@/theme';

export function VideoPreview({ url, height = 260 }: { url: string | null; height?: number }) {
  if (!url) return <View style={{ height, backgroundColor: colors.surfaceHi, borderRadius: radius.md }} />;

  return (
    <View
      testID="video-preview"
      style={{ borderRadius: radius.md, overflow: 'hidden', backgroundColor: '#000' }}
    >
      {React.createElement('video', {
        src: url,
        controls: true,
        preload: 'metadata',
        playsInline: true,
        'data-testid': 'video-element',
        style: { width: '100%', height, display: 'block', backgroundColor: '#000' },
      })}
    </View>
  );
}
