import { Redirect } from 'expo-router';
import React from 'react';

import { Loading } from '@/components/ui';
import { useAuth } from '@/store/auth';

/** Entry point: send each visitor to the right half of the app. */
export default function Index() {
  const { user, ready } = useAuth();

  if (!ready) return <Loading label="Starting Pramonit…" />;
  if (!user) return <Redirect href="/login" />;
  return <Redirect href={user.role === 'coach' ? '/coach' : '/student'} />;
}
