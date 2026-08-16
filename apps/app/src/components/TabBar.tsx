/** Bottom tab bar for the student app, and the coach sidebar for desktop. */

import { Link, usePathname } from 'expo-router';
import React from 'react';
import { Platform, Pressable, StyleSheet, Text, View } from 'react-native';

import { colors, font, radius, spacing } from '@/theme';

export type NavItem = { href: string; label: string; icon: string };

function isActive(pathname: string, href: string): boolean {
  if (href.endsWith('/')) return pathname === href.slice(0, -1) || pathname === href;
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function TabBar({ items }: { items: NavItem[] }) {
  const pathname = usePathname();

  return (
    <View style={styles.tabBar} testID="tab-bar">
      {items.map((item) => {
        const active = isActive(pathname, item.href);
        return (
          <Link key={item.href} href={item.href as any} asChild>
            <Pressable
              testID={`tab-${item.label.toLowerCase()}`}
              accessibilityRole="tab"
              accessibilityState={{ selected: active }}
              accessibilityLabel={item.label}
              style={styles.tab}
            >
              <Text style={{ fontSize: 20, opacity: active ? 1 : 0.45 }}>{item.icon}</Text>
              <Text
                style={[
                  font.label,
                  { color: active ? colors.primary : colors.textFaint, marginTop: 2 },
                ]}
              >
                {item.label.toUpperCase()}
              </Text>
            </Pressable>
          </Link>
        );
      })}
    </View>
  );
}

export function Sidebar({
  items,
  header,
  footer,
}: {
  items: NavItem[];
  header?: React.ReactNode;
  footer?: React.ReactNode;
}) {
  const pathname = usePathname();

  return (
    <View style={styles.sidebar} testID="sidebar">
      {!!header && <View style={{ marginBottom: spacing.xl }}>{header}</View>}
      <View style={{ gap: spacing.xs, flex: 1 }}>
        {items.map((item) => {
          const active = isActive(pathname, item.href);
          return (
            <Link key={item.href} href={item.href as any} asChild>
              <Pressable
                testID={`nav-${item.label.toLowerCase()}`}
                accessibilityRole="link"
                accessibilityState={{ selected: active }}
                style={({ pressed }) => [
                  styles.sidebarItem,
                  active && { backgroundColor: colors.primarySoft },
                  pressed && { opacity: 0.85 },
                ]}
              >
                <Text style={{ fontSize: 17, width: 26 }}>{item.icon}</Text>
                <Text
                  style={[
                    font.body,
                    { color: active ? colors.primary : colors.textMuted, fontWeight: '700' },
                  ]}
                >
                  {item.label}
                </Text>
              </Pressable>
            </Link>
          );
        })}
      </View>
      {!!footer && <View>{footer}</View>}
    </View>
  );
}

const styles = StyleSheet.create({
  tabBar: {
    flexDirection: 'row',
    backgroundColor: colors.surface,
    borderTopWidth: 1,
    borderTopColor: colors.border,
    paddingTop: spacing.sm,
    paddingBottom: spacing.md,
  },
  tab: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: spacing.xs,
    ...Platform.select({ web: { cursor: 'pointer' } as any, default: {} }),
  },
  sidebar: {
    width: 232,
    backgroundColor: colors.surface,
    borderRightWidth: 1,
    borderRightColor: colors.border,
    padding: spacing.lg,
  },
  sidebarItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.md,
    borderRadius: radius.md,
    ...Platform.select({ web: { cursor: 'pointer' } as any, default: {} }),
  },
});
