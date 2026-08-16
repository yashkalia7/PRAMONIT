import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import React from 'react';
import { Platform, View } from 'react-native';

import { AuthProvider } from '@/store/auth';
import { colors } from '@/theme';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 15_000,
      // The coach's review queue and the student's streak both change from the
      // other side of the app; refetching on focus keeps two open tabs honest.
      refetchOnWindowFocus: true,
    },
  },
});

export default function RootLayout() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <View style={{ flex: 1, backgroundColor: colors.bg }}>
          <StatusBar style="light" />
          <Stack
            screenOptions={{
              headerShown: false,
              contentStyle: { backgroundColor: colors.bg },
              animation: Platform.OS === 'web' ? 'none' : 'default',
            }}
          />
        </View>
      </AuthProvider>
    </QueryClientProvider>
  );
}
