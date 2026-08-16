/**
 * Simulated phone column.
 *
 * On a desktop browser the student experience renders inside a fixed 440px
 * device shell, so what you see in the web test phase is what ships to the App
 * Store — same components, same widths, same line breaks. On an actual phone
 * (or a narrow window) the frame disappears entirely and the app is full-bleed.
 */

import React from 'react';
import { Platform, StyleSheet, Text, View } from 'react-native';

import { useResponsive } from '@/hooks/useResponsive';
import { PHONE_WIDTH, colors, font, radius, spacing } from '@/theme';

export function PhoneFrame({
  children,
  label = 'Mobile preview',
}: {
  children: React.ReactNode;
  label?: string;
}) {
  const { simulatePhone, height } = useResponsive();

  if (!simulatePhone) {
    return <View style={{ flex: 1, backgroundColor: colors.bg }}>{children}</View>;
  }

  const frameHeight = Math.min(Math.max(height - 96, 560), 940);

  return (
    <View style={styles.stage} testID="phone-stage">
      <View style={[styles.device, { height: frameHeight }]} testID="phone-frame">
        <View style={styles.notch} />
        <View style={styles.screen}>{children}</View>
      </View>
      <Text style={[font.label, styles.caption]}>
        {label.toUpperCase()} · {PHONE_WIDTH}PX — IDENTICAL TO THE IOS / ANDROID BUILD
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  stage: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#050806',
    padding: spacing.lg,
  },
  device: {
    width: PHONE_WIDTH,
    maxWidth: '100%',
    backgroundColor: colors.bg,
    borderRadius: 38,
    borderWidth: 8,
    borderColor: '#1A211D',
    overflow: 'hidden',
    ...Platform.select({
      web: {
        boxShadow: '0 30px 80px rgba(0,0,0,0.55)',
      } as any,
      default: {},
    }),
  },
  notch: {
    position: 'absolute',
    top: 8,
    alignSelf: 'center',
    width: 120,
    height: 22,
    borderRadius: radius.pill,
    backgroundColor: '#1A211D',
    zIndex: 10,
  },
  screen: {
    flex: 1,
    paddingTop: 34,
    backgroundColor: colors.bg,
  },
  caption: {
    color: colors.textFaint,
    marginTop: spacing.md,
    letterSpacing: 1,
  },
});
