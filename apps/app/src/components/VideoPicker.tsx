/** Native video picker: film now, or pick an existing clip. */

import * as ImagePicker from 'expo-image-picker';
import React from 'react';
import { View } from 'react-native';

import { Button } from '@/components/ui';
import { normaliseMime, type PickedVideo } from '@/lib/video';
import { spacing } from '@/theme';

async function toPicked(
  result: ImagePicker.ImagePickerResult,
  source: 'camera' | 'gallery',
): Promise<PickedVideo | null> {
  if (result.canceled || !result.assets?.length) return null;
  const asset = result.assets[0];
  return {
    name: asset.fileName ?? `training-${Date.now()}.mp4`,
    mimeType: normaliseMime(asset.mimeType),
    size: asset.fileSize ?? 0,
    uri: asset.uri,
    durationSec: asset.duration ? Math.round(asset.duration / 1000) : null,
    source,
  };
}

export function VideoPicker({
  onPick,
  onError,
  disabled,
}: {
  onPick: (video: PickedVideo) => void;
  onError?: (message: string) => void;
  disabled?: boolean;
  label?: string;
}) {
  const film = async () => {
    const permission = await ImagePicker.requestCameraPermissionsAsync();
    if (!permission.granted) {
      onError?.('Camera permission is needed to film your training.');
      return;
    }
    const picked = await toPicked(
      await ImagePicker.launchCameraAsync({
        mediaTypes: ['videos'],
        videoMaxDuration: 180,
        quality: 0.7,
      }),
      'camera',
    );
    if (picked) onPick(picked);
  };

  const choose = async () => {
    const picked = await toPicked(
      await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ['videos'],
        quality: 0.7,
      }),
      'gallery',
    );
    if (picked) onPick(picked);
  };

  return (
    <View style={{ gap: spacing.sm }}>
      <Button label="🎥  Record now" testID="pick-camera" onPress={film} disabled={disabled} full />
      <Button
        label="🖼  Choose from gallery"
        testID="pick-video"
        variant="secondary"
        onPress={choose}
        disabled={disabled}
        full
      />
    </View>
  );
}
