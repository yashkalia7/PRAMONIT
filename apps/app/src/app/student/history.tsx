import { useQuery } from '@tanstack/react-query';
import { router } from 'expo-router';
import React from 'react';
import { Text, View } from 'react-native';

import { endpoints, queryKeys } from '@/api/endpoints';
import type { Submission } from '@/api/types';
import {
  Badge,
  Button,
  Card,
  EmptyState,
  Loading,
  Muted,
  Notice,
  Row,
  Screen,
  Title,
} from '@/components/ui';
import { colors, font, spacing } from '@/theme';

export default function HistoryScreen() {
  const query = useQuery({
    queryKey: queryKeys.submissions,
    queryFn: () => endpoints.mySubmissions(50),
  });

  if (query.isLoading) return <Loading label="Loading your submissions…" />;
  if (query.isError) {
    return (
      <Screen testID="history-screen">
        <Notice>{(query.error as Error).message}</Notice>
      </Screen>
    );
  }

  const submissions = query.data ?? [];

  return (
    <Screen testID="history-screen">
      <Title>My submissions</Title>
      <Muted style={{ marginBottom: spacing.lg }}>
        {submissions.length} video{submissions.length === 1 ? '' : 's'} submitted
      </Muted>

      {submissions.length === 0 ? (
        <EmptyState
          emoji="🎬"
          title="Nothing submitted yet"
          body="Film a drill and send it to your coach — two a week keeps your streak alive."
          action={
            <Button
              label="Upload your first video"
              testID="history-upload-cta"
              onPress={() => router.push('/student/upload')}
            />
          }
        />
      ) : (
        <View style={{ gap: spacing.sm }}>
          {submissions.map((submission) => (
            <SubmissionRow key={submission.id} submission={submission} />
          ))}
        </View>
      )}
    </Screen>
  );
}

function SubmissionRow({ submission }: { submission: Submission }) {
  const tone =
    submission.status === 'approved'
      ? 'success'
      : submission.status === 'rejected'
        ? 'danger'
        : 'warning';

  return (
    <Card testID={`submission-${submission.id}`} style={{ padding: spacing.md }}>
      <Row style={{ justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <View style={{ flex: 1, paddingRight: spacing.md }}>
          <Text style={[font.h3, { color: colors.text }]}>
            {submission.drill?.title ?? 'Training video'}
          </Text>
          <Muted style={{ marginTop: 2 }}>
            {submission.week_label}
            {submission.reps_claimed ? ` · ${submission.reps_claimed} reps` : ''}
            {submission.duration_sec ? ` · ${submission.duration_sec}s` : ''}
          </Muted>
        </View>
        <View style={{ alignItems: 'flex-end', gap: 4 }}>
          <Badge
            label={submission.status}
            tone={tone as any}
            testID={`status-${submission.status}`}
          />
          {submission.auto_approved && <Badge label="auto ⏱" tone="info" />}
        </View>
      </Row>

      {!!submission.student_note && (
        <Muted style={{ marginTop: spacing.sm, fontStyle: 'italic' }}>
          “{submission.student_note}”
        </Muted>
      )}

      {!!submission.coach_feedback && (
        <View
          style={{
            marginTop: spacing.sm,
            paddingLeft: spacing.md,
            borderLeftWidth: 2,
            borderLeftColor: submission.status === 'rejected' ? colors.danger : colors.success,
          }}
        >
          <Text style={[font.label, { color: colors.textFaint }]}>COACH</Text>
          <Text style={[font.bodySm, { color: colors.textMuted, marginTop: 2 }]}>
            {submission.coach_feedback}
          </Text>
        </View>
      )}

      {!!submission.coach_rating && (
        <Text style={{ marginTop: spacing.sm, fontSize: 14 }}>
          {'⭐'.repeat(submission.coach_rating)}
        </Text>
      )}
    </Card>
  );
}
