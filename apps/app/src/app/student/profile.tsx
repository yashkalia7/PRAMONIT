import { useQuery } from '@tanstack/react-query';
import { router } from 'expo-router';
import React from 'react';
import { Text, View } from 'react-native';

import { endpoints, queryKeys } from '@/api/endpoints';
import { Button, Card, Divider, Loading, Muted, Row, Screen, SectionTitle, StatTile, Title } from '@/components/ui';
import { useAuth } from '@/store/auth';
import { colors, font, spacing } from '@/theme';

export default function StudentProfile() {
  const { user, logout } = useAuth();
  const streakQuery = useQuery({ queryKey: queryKeys.streak, queryFn: endpoints.streak });

  if (!user) return <Loading />;
  const profile = user.student_profile;

  return (
    <Screen testID="student-profile">
      <Title>{user.full_name}</Title>
      <Muted style={{ marginBottom: spacing.lg }}>{user.email}</Muted>

      {!!streakQuery.data && (
        <Row gap={spacing.sm} style={{ marginBottom: spacing.lg }}>
          <StatTile value={streakQuery.data.current_weeks} label="Week streak" tone="primary" />
          <StatTile value={streakQuery.data.total_approved} label="Approved" />
          <StatTile value={streakQuery.data.total_points} label="Points" />
        </Row>
      )}

      <SectionTitle>Football</SectionTitle>
      <Card>
        <Detail label="Coach" value={profile?.coach_name} />
        <Detail label="Batch" value={profile?.batch_name} />
        <Detail label="Course" value={profile?.course} />
        <Detail label="Position" value={profile?.preferred_position} />
        <Detail label="Dominant foot" value={profile?.dominant_foot} />
        <Detail label="Jersey" value={profile?.jersey_number?.toString()} />
        <Detail label="Height" value={profile?.height_cm ? `${profile.height_cm} cm` : null} />
        <Detail label="Weight" value={profile?.weight_kg ? `${profile.weight_kg} kg` : null} />
        <Detail label="Years playing" value={profile?.years_playing?.toString()} />
        <Detail label="Previous club" value={profile?.previous_club} last />
      </Card>

      <SectionTitle>Guardian & school</SectionTitle>
      <Card>
        <Detail label="Guardian" value={profile?.guardian_name} />
        <Detail label="Guardian phone" value={profile?.guardian_phone} />
        <Detail label="Emergency" value={profile?.emergency_contact} />
        <Detail label="School" value={profile?.school_name} />
        <Detail label="Medical notes" value={profile?.medical_notes} last />
      </Card>

      <Button
        label="Sign out"
        variant="danger"
        testID="sign-out"
        full
        style={{ marginTop: spacing.xl }}
        onPress={async () => {
          await logout();
          router.replace('/login');
        }}
      />
    </Screen>
  );
}

function Detail({ label, value, last }: { label: string; value?: string | null; last?: boolean }) {
  return (
    <View>
      <Row style={{ justifyContent: 'space-between', paddingVertical: spacing.sm }}>
        <Text style={[font.bodySm, { color: colors.textFaint }]}>{label}</Text>
        <Text
          style={[font.bodySm, { color: value ? colors.text : colors.textFaint, flex: 1, textAlign: 'right' }]}
          numberOfLines={2}
        >
          {value || '—'}
        </Text>
      </Row>
      {!last && <View style={{ height: 1, backgroundColor: colors.border }} />}
    </View>
  );
}
