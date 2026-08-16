import { Redirect, Slot } from 'expo-router';
import React from 'react';
import { View } from 'react-native';

import { PhoneFrame } from '@/components/PhoneFrame';
import { TabBar, type NavItem } from '@/components/TabBar';
import { Loading } from '@/components/ui';
import { useAuth } from '@/store/auth';
import { colors } from '@/theme';

const TABS: NavItem[] = [
  { href: '/student', label: 'Home', icon: '🔥' },
  { href: '/student/upload', label: 'Upload', icon: '🎬' },
  { href: '/student/history', label: 'History', icon: '📋' },
  { href: '/student/leaderboard', label: 'Ranks', icon: '🏆' },
  { href: '/student/profile', label: 'Me', icon: '👤' },
];

export default function StudentLayout() {
  const { user, ready } = useAuth();

  if (!ready) return <Loading label="Starting Pramonit…" />;
  if (!user) return <Redirect href="/login" />;
  if (user.role !== 'student') return <Redirect href="/coach" />;

  return (
    <PhoneFrame label="Student app">
      <View style={{ flex: 1, backgroundColor: colors.bg }}>
        <View style={{ flex: 1 }}>
          <Slot />
        </View>
        <TabBar items={TABS} />
      </View>
    </PhoneFrame>
  );
}
