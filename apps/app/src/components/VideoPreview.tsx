/** Native video player. */

import { useVideoPlayer, VideoView } from 'expo-video';
import React from 'react';
import { View } from 'react-native';

import { colors, radius } from '@/theme';

export function VideoPreview({ url, height = 260 }: { url: string | null; height?: number }) {
  const player = useVideoPlayer(url ?? '', (instance) => {
    instance.loop = false;
  });

  if (!url) {
    return <View style={{ height, backgroundColor: colors.surfaceHi, borderRadius: radius.md }} />;
  }

  return (
    <View testID="video-preview" style={{ borderRadius: radius.md, overflow: 'hidden' }}>
      <VideoView
        player={player}
        style={{ width: '100%', height, backgroundColor: '#000' }}
        nativeControls
      />
    </View>
  );
}
