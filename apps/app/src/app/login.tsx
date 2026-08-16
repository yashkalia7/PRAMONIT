import { Link, Redirect, router } from 'expo-router';
import React, { useState } from 'react';
import { Platform, Pressable, Text, View } from 'react-native';

import { ApiError } from '@/api/client';
import { Brand, Button, Card, Field, Loading, Muted, Notice, Screen } from '@/components/ui';
import { useAuth } from '@/store/auth';
import { colors, font, spacing } from '@/theme';

export default function LoginScreen() {
  const { login, user, ready, signingIn } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);

  if (!ready) return <Loading label="Starting Pramonit…" />;
  if (user) return <Redirect href={user.role === 'coach' ? '/coach' : '/student'} />;

  const submit = async () => {
    setError(null);
    if (!email.trim() || !password) {
      setError('Enter your email and password.');
      return;
    }
    try {
      const me = await login(email.trim(), password);
      router.replace(me.role === 'coach' ? '/coach' : '/student');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not sign in. Please try again.');
    }
  };

  return (
    <Screen testID="login-screen" style={{ maxWidth: 460, width: '100%', alignSelf: 'center' }}>
      <View style={{ marginTop: spacing.xxxl, marginBottom: spacing.xl }}>
        <Brand />
      </View>

      <Text style={[font.display, { color: colors.text, marginBottom: spacing.xs }]}>
        Train. Film. Prove it.
      </Text>
      <Muted style={{ marginBottom: spacing.xl }}>
        Two sessions a week, filmed and signed off by your coach. Everything else is your own
        ambition.
      </Muted>

      <Card>
        {!!error && <Notice testID="login-error">{error}</Notice>}

        <Field
          label="Email"
          testID="login-email"
          value={email}
          onChangeText={setEmail}
          placeholder="you@example.com"
          keyboardType="email-address"
          autoCapitalize="none"
        />
        <Field
          label="Password"
          testID="login-password"
          value={password}
          onChangeText={setPassword}
          placeholder="••••••••"
          secure
          autoCapitalize="none"
        />
        <Button label="Sign in" testID="login-submit" onPress={submit} loading={signingIn} full />
      </Card>

      <View style={{ marginTop: spacing.xl, gap: spacing.md }}>
        <Muted>New to the academy?</Muted>
        <View style={{ flexDirection: 'row', gap: spacing.md, flexWrap: 'wrap' }}>
          <Link href="/register/student" asChild>
            <Pressable testID="link-register-student" style={linkStyle}>
              <Text style={[font.body, { color: colors.primary, fontWeight: '700' }]}>
                Register as a student →
              </Text>
            </Pressable>
          </Link>
          <Link href="/register/coach" asChild>
            <Pressable testID="link-register-coach" style={linkStyle}>
              <Text style={[font.body, { color: colors.textMuted, fontWeight: '700' }]}>
                I'm a coach →
              </Text>
            </Pressable>
          </Link>
        </View>
      </View>
    </Screen>
  );
}

const linkStyle = Platform.select({
  web: { cursor: 'pointer' } as any,
  default: {},
});
