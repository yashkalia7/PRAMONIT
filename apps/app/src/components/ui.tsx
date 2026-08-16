/** Shared primitives. Everything here works unchanged on web, iOS and Android. */

import React from 'react';
import {
  ActivityIndicator,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
  type StyleProp,
  type TextStyle,
  type ViewStyle,
} from 'react-native';

import { colors, font, radius, spacing } from '@/theme';

// ---------------------------------------------------------------------------

export function Crest({ size = 34 }: { size?: number }) {
  return (
    <View
      style={{
        width: size,
        height: size,
        borderRadius: size / 3.2,
        backgroundColor: colors.primary,
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <Text style={{ fontSize: size * 0.52, lineHeight: size * 0.72 }}>⚽</Text>
    </View>
  );
}

export function Brand({ subtitle }: { subtitle?: string }) {
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: spacing.md }}>
      <Crest />
      <View>
        <Text style={[font.h2, { color: colors.text, letterSpacing: 1 }]}>PRAMONIT</Text>
        <Text style={[font.label, { color: colors.textFaint }]}>
          {(subtitle ?? 'FOOTBALL ACADEMY').toUpperCase()}
        </Text>
      </View>
    </View>
  );
}

// ---------------------------------------------------------------------------

export function Card({
  children,
  style,
  padded = true,
  testID,
}: {
  children: React.ReactNode;
  style?: StyleProp<ViewStyle>;
  padded?: boolean;
  testID?: string;
}) {
  return (
    <View testID={testID} style={[styles.card, padded && { padding: spacing.lg }, style]}>
      {children}
    </View>
  );
}

export function SectionTitle({ children, right }: { children: React.ReactNode; right?: React.ReactNode }) {
  return (
    <View style={styles.sectionTitle}>
      <Text style={[font.label, { color: colors.textFaint }]}>
        {typeof children === 'string' ? children.toUpperCase() : children}
      </Text>
      {right}
    </View>
  );
}

export function Divider() {
  return <View style={{ height: 1, backgroundColor: colors.border, marginVertical: spacing.md }} />;
}

// ---------------------------------------------------------------------------

type ButtonProps = {
  label: string;
  onPress?: () => void;
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger' | 'success';
  disabled?: boolean;
  loading?: boolean;
  small?: boolean;
  full?: boolean;
  testID?: string;
  style?: StyleProp<ViewStyle>;
};

export function Button({
  label,
  onPress,
  variant = 'primary',
  disabled,
  loading,
  small,
  full,
  testID,
  style,
}: ButtonProps) {
  const palette = {
    primary: { bg: colors.primary, fg: colors.onPrimary, border: colors.primary },
    secondary: { bg: colors.surfaceHi, fg: colors.text, border: colors.borderBright },
    ghost: { bg: 'transparent', fg: colors.textMuted, border: 'transparent' },
    danger: { bg: colors.dangerSoft, fg: colors.danger, border: colors.danger },
    success: { bg: colors.successSoft, fg: colors.success, border: colors.success },
  }[variant];

  const inert = disabled || loading;

  return (
    <Pressable
      testID={testID}
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityState={{ disabled: !!inert, busy: !!loading }}
      onPress={inert ? undefined : onPress}
      style={({ pressed }) => [
        styles.button,
        small && { paddingVertical: spacing.sm, paddingHorizontal: spacing.md },
        full && { alignSelf: 'stretch' },
        {
          backgroundColor: palette.bg,
          borderColor: palette.border,
          opacity: inert ? 0.45 : pressed ? 0.82 : 1,
        },
        style,
      ]}
    >
      {loading ? (
        <ActivityIndicator size="small" color={palette.fg} />
      ) : (
        <Text style={[small ? font.bodySm : font.body, { color: palette.fg, fontWeight: '700' }]}>
          {label}
        </Text>
      )}
    </Pressable>
  );
}

// ---------------------------------------------------------------------------

export function Field({
  label,
  value,
  onChangeText,
  placeholder,
  secure,
  keyboardType,
  multiline,
  hint,
  error,
  testID,
  autoCapitalize = 'sentences',
}: {
  label: string;
  value: string;
  onChangeText: (v: string) => void;
  placeholder?: string;
  secure?: boolean;
  keyboardType?: 'default' | 'email-address' | 'numeric' | 'phone-pad';
  multiline?: boolean;
  hint?: string;
  error?: string;
  testID?: string;
  autoCapitalize?: 'none' | 'sentences' | 'words' | 'characters';
}) {
  return (
    <View style={{ gap: spacing.xs, marginBottom: spacing.md }}>
      <Text style={[font.label, { color: colors.textMuted }]}>{label.toUpperCase()}</Text>
      <TextInput
        testID={testID}
        accessibilityLabel={label}
        value={value}
        onChangeText={onChangeText}
        placeholder={placeholder}
        placeholderTextColor={colors.textFaint}
        secureTextEntry={secure}
        keyboardType={keyboardType}
        autoCapitalize={autoCapitalize}
        autoCorrect={false}
        multiline={multiline}
        style={[
          styles.input,
          multiline && { minHeight: 90, textAlignVertical: 'top' },
          !!error && { borderColor: colors.danger },
        ]}
      />
      {!!hint && !error && (
        <Text style={[font.bodySm, { color: colors.textFaint }]}>{hint}</Text>
      )}
      {!!error && <Text style={[font.bodySm, { color: colors.danger }]}>{error}</Text>}
    </View>
  );
}

export function Chip({
  label,
  selected,
  onPress,
  tone = 'default',
  testID,
}: {
  label: string;
  selected?: boolean;
  onPress?: () => void;
  tone?: 'default' | 'success' | 'warning' | 'danger';
  testID?: string;
}) {
  const toneColor = {
    default: colors.primary,
    success: colors.success,
    warning: colors.warning,
    danger: colors.danger,
  }[tone];

  return (
    <Pressable
      testID={testID}
      accessibilityRole={onPress ? 'button' : 'text'}
      accessibilityState={{ selected: !!selected }}
      onPress={onPress}
      style={({ pressed }) => [
        styles.chip,
        {
          backgroundColor: selected ? toneColor : colors.surfaceHi,
          borderColor: selected ? toneColor : colors.border,
          opacity: pressed && onPress ? 0.8 : 1,
        },
      ]}
    >
      <Text
        style={[
          font.bodySm,
          { color: selected ? colors.onPrimary : colors.textMuted, fontWeight: '700' },
        ]}
      >
        {label}
      </Text>
    </Pressable>
  );
}

export function Badge({
  label,
  tone = 'default',
  testID,
}: {
  label: string;
  tone?: 'default' | 'success' | 'warning' | 'danger' | 'info';
  testID?: string;
}) {
  const map = {
    default: { bg: colors.surfaceHi, fg: colors.textMuted },
    success: { bg: colors.successSoft, fg: colors.success },
    warning: { bg: colors.warningSoft, fg: colors.warning },
    danger: { bg: colors.dangerSoft, fg: colors.danger },
    info: { bg: 'rgba(79,195,247,0.14)', fg: colors.info },
  }[tone];

  return (
    <View testID={testID} style={[styles.badge, { backgroundColor: map.bg }]}>
      <Text style={[font.label, { color: map.fg }]}>{label.toUpperCase()}</Text>
    </View>
  );
}

// ---------------------------------------------------------------------------

export function StatTile({
  value,
  label,
  tone = 'default',
  testID,
}: {
  value: string | number;
  label: string;
  tone?: 'default' | 'primary' | 'success' | 'warning' | 'danger';
  testID?: string;
}) {
  const fg = {
    default: colors.text,
    primary: colors.primary,
    success: colors.success,
    warning: colors.warning,
    danger: colors.danger,
  }[tone];

  return (
    <View testID={testID} style={styles.stat}>
      <Text style={[font.h1, { color: fg }]}>{value}</Text>
      <Text style={[font.label, { color: colors.textFaint, marginTop: 2 }]}>
        {label.toUpperCase()}
      </Text>
    </View>
  );
}

export function EmptyState({
  emoji = '🥅',
  title,
  body,
  action,
  testID,
}: {
  emoji?: string;
  title: string;
  body?: string;
  action?: React.ReactNode;
  testID?: string;
}) {
  return (
    <View testID={testID} style={styles.empty}>
      <Text style={{ fontSize: 40, marginBottom: spacing.sm }}>{emoji}</Text>
      <Text style={[font.h3, { color: colors.text, textAlign: 'center' }]}>{title}</Text>
      {!!body && (
        <Text
          style={[
            font.bodySm,
            { color: colors.textMuted, textAlign: 'center', marginTop: spacing.xs, maxWidth: 320 },
          ]}
        >
          {body}
        </Text>
      )}
      {!!action && <View style={{ marginTop: spacing.lg }}>{action}</View>}
    </View>
  );
}

export function Loading({ label = 'Loading…' }: { label?: string }) {
  return (
    <View style={styles.empty} testID="loading">
      <ActivityIndicator color={colors.primary} />
      <Text style={[font.bodySm, { color: colors.textMuted, marginTop: spacing.md }]}>{label}</Text>
    </View>
  );
}

export function Notice({
  tone = 'danger',
  children,
  testID,
}: {
  tone?: 'danger' | 'warning' | 'success' | 'info';
  children: React.ReactNode;
  testID?: string;
}) {
  const map = {
    danger: { bg: colors.dangerSoft, fg: colors.danger },
    warning: { bg: colors.warningSoft, fg: colors.warning },
    success: { bg: colors.successSoft, fg: colors.success },
    info: { bg: 'rgba(79,195,247,0.14)', fg: colors.info },
  }[tone];

  return (
    <View testID={testID} style={[styles.notice, { backgroundColor: map.bg }]}>
      <Text style={[font.bodySm, { color: map.fg }]}>{children}</Text>
    </View>
  );
}

export function Screen({
  children,
  scroll = true,
  style,
  testID,
}: {
  children: React.ReactNode;
  scroll?: boolean;
  style?: StyleProp<ViewStyle>;
  testID?: string;
}) {
  if (!scroll) {
    return (
      <View testID={testID} style={[{ flex: 1, backgroundColor: colors.bg }, style]}>
        {children}
      </View>
    );
  }
  return (
    <ScrollView
      testID={testID}
      style={{ flex: 1, backgroundColor: colors.bg }}
      contentContainerStyle={[{ padding: spacing.lg, paddingBottom: spacing.xxxl * 2 }, style]}
      keyboardShouldPersistTaps="handled"
    >
      {children}
    </ScrollView>
  );
}

export function Row({
  children,
  style,
  gap = spacing.md,
}: {
  children: React.ReactNode;
  style?: StyleProp<ViewStyle>;
  gap?: number;
}) {
  return (
    <View style={[{ flexDirection: 'row', alignItems: 'center', gap }, style]}>{children}</View>
  );
}

export function Muted({
  children,
  style,
  testID,
}: {
  children: React.ReactNode;
  style?: StyleProp<TextStyle>;
  testID?: string;
}) {
  return (
    <Text testID={testID} style={[font.bodySm, { color: colors.textMuted }, style]}>
      {children}
    </Text>
  );
}

export function Title({ children, style }: { children: React.ReactNode; style?: StyleProp<TextStyle> }) {
  return <Text style={[font.h1, { color: colors.text }, style]}>{children}</Text>;
}

// ---------------------------------------------------------------------------

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
  },
  sectionTitle: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: spacing.sm,
    marginTop: spacing.lg,
  },
  button: {
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.lg,
    borderRadius: radius.md,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 44,
    ...Platform.select({ web: { cursor: 'pointer' } as any, default: {} }),
  },
  input: {
    backgroundColor: colors.surfaceAlt,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.md,
    color: colors.text,
    fontSize: 15,
    ...Platform.select({ web: { outlineStyle: 'none' } as any, default: {} }),
  },
  chip: {
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md,
    borderRadius: radius.pill,
    borderWidth: 1,
    ...Platform.select({ web: { cursor: 'pointer' } as any, default: {} }),
  },
  badge: {
    paddingVertical: 3,
    paddingHorizontal: spacing.sm,
    borderRadius: radius.sm,
    alignSelf: 'flex-start',
  },
  stat: {
    flex: 1,
    backgroundColor: colors.surfaceAlt,
    borderRadius: radius.md,
    padding: spacing.md,
    borderWidth: 1,
    borderColor: colors.border,
  },
  empty: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: spacing.xxxl,
    paddingHorizontal: spacing.lg,
  },
  notice: {
    borderRadius: radius.md,
    padding: spacing.md,
    marginBottom: spacing.md,
  },
});
