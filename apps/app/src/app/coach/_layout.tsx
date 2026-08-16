import { useQuery } from '@tanstack/react-query';
import { Redirect, Slot, router } from 'expo-router';
import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { endpoints, queryKeys } from '@/api/endpoints';
import { Sidebar, TabBar, type NavItem } from '@/components/TabBar';
import { Badge, Brand, Loading, Muted } from '@/components/ui';
import { useResponsive } from '@/hooks/useResponsive';
import { useAuth } from '@/store/auth';
import { colors, font, spacing } from '@/theme';

const NAV: NavItem[] = [
  { href: '/coach', label: 'Dashboard', icon: '📊' },
  { href: '/coach/review', label: 'Review', icon: '🎬' },
  { href: '/coach/roster', label: 'Roster', icon: '👥' },
  { href: '/coach/assign', label: 'Assign', icon: '📌' },
  { href: '/coach/leaderboard', label: 'Ranks', icon: '🏆' },
];

export default function CoachLayout() {
  const { user, ready, logout } = useAuth();
  const { isDesktop } = useResponsive();

  const queueQuery = useQuery({
    queryKey: queryKeys.queue,
    queryFn: () => endpoints.reviewQueue(1),
    enabled: !!user && user.role === 'coach',
    refetchInterval: 60_000,
  });

  if (!ready) return <Loading label="Starting Pramonit…" />;
  if (!user) return <Redirect href="/login" />;
  if (user.role !== 'coach') return <Redirect href="/student" />;

  const pending = queueQuery.data?.total_pending ?? 0;

  // Desktop: a real dashboard. Reviewing thirty videos on a 27" monitor should
  // not feel like a stretched phone app.
  if (isDesktop) {
    return (
      <View style={{ flex: 1, flexDirection: 'row', backgroundColor: colors.bg }}>
        <Sidebar
          items={NAV}
          header={
            <View style={{ gap: spacing.md }}>
              <Brand subtitle="Coach" />
              {pending > 0 && (
                <Badge label={`${pending} awaiting review`} tone="warning" testID="sidebar-pending" />
              )}
            </View>
          }
          footer={
            <View style={{ gap: spacing.xs }}>
              <Text style={[font.bodySm, { color: colors.text, fontWeight: '700' }]}>
                {user.full_name}
              </Text>
              <Muted>{user.coach_profile?.primary_location ?? 'Coach'}</Muted>
              <Pressable
                testID="sign-out"
                onPress={async () => {
                  await logout();
                  router.replace('/login');
                }}
                style={{ marginTop: spacing.sm }}
              >
                <Text style={[font.bodySm, { color: colors.danger, fontWeight: '700' }]}>
                  Sign out
                </Text>
              </Pressable>
            </View>
          }
        />
        <View style={{ flex: 1 }} testID="coach-content">
          <Slot />
        </View>
      </View>
    );
  }

  // Narrow window or phone: bottom tabs, plus a header — without it there is no
  // sign-out affordance anywhere on the coach's phone.
  return (
    <View style={{ flex: 1, backgroundColor: colors.bg }}>
      <View style={styles.header}>
        <View style={{ flex: 1 }}>
          <Text style={[font.h3, { color: colors.text }]} numberOfLines={1}>
            {user.full_name}
          </Text>
          <Muted>{user.coach_profile?.primary_location ?? 'Coach'}</Muted>
        </View>
        {pending > 0 && (
          <Badge label={`${pending} to review`} tone="warning" testID="header-pending" />
        )}
        <Pressable
          testID="sign-out"
          accessibilityRole="button"
          accessibilityLabel="Sign out"
          onPress={async () => {
            await logout();
            router.replace('/login');
          }}
        >
          <Text style={[font.bodySm, { color: colors.danger, fontWeight: '700' }]}>Sign out</Text>
        </Pressable>
      </View>

      <View style={{ flex: 1 }} testID="coach-content">
        <Slot />
      </View>
      <TabBar items={NAV} />
    </View>
  );
}

const styles = StyleSheet.create({
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.xl,
    paddingBottom: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
    backgroundColor: colors.surface,
  },
});
