import { useQuery } from '@tanstack/react-query';
import { router } from 'expo-router';
import React from 'react';
import { Text, View } from 'react-native';

import { endpoints, queryKeys } from '@/api/endpoints';
import type { Drill, Streak, Week } from '@/api/types';
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
  SectionTitle,
  StatTile,
} from '@/components/ui';
import { useAuth } from '@/store/auth';
import { colors, font, radius, spacing } from '@/theme';

export default function StudentHome() {
  const { user } = useAuth();

  const streakQuery = useQuery({ queryKey: queryKeys.streak, queryFn: endpoints.streak });
  const weeksQuery = useQuery({ queryKey: queryKeys.weeks, queryFn: () => endpoints.weeks(12) });
  const assignmentQuery = useQuery({
    queryKey: queryKeys.assignment,
    queryFn: endpoints.currentAssignment,
  });

  if (streakQuery.isLoading) return <Loading label="Loading your week…" />;

  if (streakQuery.isError) {
    return (
      <Screen testID="student-home">
        <Notice testID="home-error">
          {(streakQuery.error as Error).message}
        </Notice>
      </Screen>
    );
  }

  const streak = streakQuery.data as Streak;
  const week = streak.this_week;
  const remaining = Math.max(0, week.required_count - week.approved_count);
  const drills =
    assignmentQuery.data?.assignment?.items.map((item) => item.drill) ??
    assignmentQuery.data?.fallback_drills ??
    [];

  return (
    <Screen testID="student-home">
      <Muted>{greeting()}</Muted>
      <Text style={[font.h1, { color: colors.text, marginBottom: spacing.lg }]}>
        {user?.full_name?.split(' ')[0] ?? 'Player'}
      </Text>

      <StreakCard streak={streak} />

      <SectionTitle>This week · {week.week_label}</SectionTitle>
      <Card testID="week-progress">
        <Row style={{ justifyContent: 'space-between', marginBottom: spacing.md }}>
          <Text style={[font.h2, { color: colors.text }]} testID="week-count">
            {week.approved_count} / {week.required_count}
          </Text>
          {week.met ? (
            <Badge label="Week complete" tone="success" testID="week-met" />
          ) : (
            <Badge
              label={`${remaining} more to go`}
              tone={remaining > 1 ? 'warning' : 'info'}
              testID="week-remaining"
            />
          )}
        </Row>

        <ProgressBar value={week.approved_count} total={week.required_count} />

        {week.pending_count > 0 && (
          <Notice tone="info" testID="pending-notice">
            {week.pending_count} video{week.pending_count === 1 ? '' : 's'} waiting on your coach.
            They count the moment they're approved — and auto-approve after 72 hours if your coach
            hasn't got to them.
          </Notice>
        )}

        <Button
          label={week.met ? 'Upload another anyway' : 'Upload today’s training'}
          testID="home-upload-cta"
          onPress={() => router.push('/student/upload')}
          full
          style={{ marginTop: spacing.md }}
        />
      </Card>

      <SectionTitle>
        {assignmentQuery.data?.assignment ? 'Set by your coach' : 'Ball mastery library'}
      </SectionTitle>
      {assignmentQuery.isLoading ? (
        <Loading label="Loading drills…" />
      ) : drills.length === 0 ? (
        <EmptyState
          emoji="⚽"
          title="No drills yet"
          body="Your coach hasn't set this week's work. Check back shortly."
        />
      ) : (
        <View style={{ gap: spacing.sm }}>
          {drills.map((drill) => (
            <DrillRow key={drill.id} drill={drill} />
          ))}
        </View>
      )}

      <SectionTitle>Last 12 weeks</SectionTitle>
      {weeksQuery.data ? (
        <WeekStrip weeks={weeksQuery.data.weeks} />
      ) : (
        <Loading label="Loading history…" />
      )}
    </Screen>
  );
}

// ---------------------------------------------------------------------------

function StreakCard({ streak }: { streak: Streak }) {
  const alive = streak.current_weeks > 0;
  return (
    <Card
      testID="streak-card"
      style={{
        borderColor: alive ? colors.primary : colors.border,
        backgroundColor: alive ? colors.primarySoft : colors.surface,
      }}
    >
      <Row style={{ justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <View>
          <Row gap={spacing.sm}>
            <Text style={{ fontSize: 34 }}>{alive ? '🔥' : '🥶'}</Text>
            <Text style={[font.display, { color: alive ? colors.primary : colors.textMuted }]}>
              <Text testID="streak-weeks">{streak.current_weeks}</Text>
            </Text>
          </Row>
          <Text style={[font.label, { color: colors.textFaint, marginTop: 2 }]}>
            {streak.current_weeks === 1 ? 'WEEK STREAK' : 'WEEK STREAK'}
          </Text>
        </View>

        <View style={{ alignItems: 'flex-end', gap: spacing.xs }}>
          <Muted>Best {streak.longest_weeks}w</Muted>
          <Muted>{streak.total_approved} approved</Muted>
          <Text style={[font.h3, { color: colors.text }]} testID="total-points">
            {streak.total_points} pts
          </Text>
        </View>
      </Row>

      {streak.provisional && (
        <Notice tone="info" testID="provisional-notice">
          Pending confirmation — your streak is held, not broken, while your coach reviews last
          week's videos.
        </Notice>
      )}

      {!alive && !streak.provisional && (
        <Muted style={{ marginTop: spacing.md }}>
          Hit {streak.this_week.required_count} approved videos this week to start a streak.
        </Muted>
      )}
    </Card>
  );
}

function ProgressBar({ value, total }: { value: number; total: number }) {
  const pct = total === 0 ? 0 : Math.min(1, value / total);
  return (
    <View style={{ gap: spacing.sm }}>
      <View
        style={{
          height: 10,
          borderRadius: radius.pill,
          backgroundColor: colors.surfaceHi,
          overflow: 'hidden',
        }}
      >
        <View
          testID="progress-fill"
          style={{
            width: `${pct * 100}%`,
            height: '100%',
            backgroundColor: pct >= 1 ? colors.success : colors.primary,
          }}
        />
      </View>
    </View>
  );
}

function DrillRow({ drill }: { drill: Drill }) {
  return (
    <Card testID={`drill-${drill.slug}`} style={{ padding: spacing.md }}>
      <Row style={{ justifyContent: 'space-between' }}>
        <View style={{ flex: 1, paddingRight: spacing.md }}>
          <Text style={[font.h3, { color: colors.text }]}>{drill.title}</Text>
          {!!drill.description && (
            <Muted style={{ marginTop: 2 }}>{drill.description}</Muted>
          )}
        </View>
        <Badge label={drill.target_label} tone="info" />
      </Row>
    </Card>
  );
}

function WeekStrip({ weeks }: { weeks: Week[] }) {
  return (
    <Card testID="week-strip">
      <Row style={{ flexWrap: 'wrap' }} gap={spacing.sm}>
        {weeks.map((week) => {
          const tone = week.met
            ? colors.success
            : week.pending_count > 0
              ? colors.warning
              : week.approved_count > 0
                ? colors.primaryDim
                : colors.surfaceHi;
          return (
            <View key={week.week_start} style={{ alignItems: 'center', gap: 4, width: 44 }}>
              <View
                testID={`week-cell-${week.week_start}`}
                accessibilityLabel={`${week.week_label}: ${week.approved_count} of ${week.required_count} approved`}
                style={{
                  width: 34,
                  height: 34,
                  borderRadius: radius.sm,
                  backgroundColor: tone,
                  borderWidth: week.is_current ? 2 : 1,
                  borderColor: week.is_current ? colors.primary : colors.border,
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <Text
                  style={[
                    font.label,
                    { color: week.met ? colors.onPrimary : colors.textMuted, fontSize: 11 },
                  ]}
                >
                  {week.approved_count}
                </Text>
              </View>
              <Text style={{ fontSize: 9, color: colors.textFaint }}>
                {week.week_label.split(/[–-]/)[0].trim()}
              </Text>
            </View>
          );
        })}
      </Row>
      <Row style={{ marginTop: spacing.md, flexWrap: 'wrap' }} gap={spacing.md}>
        <Legend color={colors.success} label="Week met" />
        <Legend color={colors.warning} label="Awaiting review" />
        <Legend color={colors.surfaceHi} label="Missed" />
      </Row>
    </Card>
  );
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <Row gap={spacing.xs}>
      <View style={{ width: 10, height: 10, borderRadius: 3, backgroundColor: color }} />
      <Text style={{ fontSize: 11, color: colors.textFaint }}>{label}</Text>
    </Row>
  );
}

function greeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return 'Good morning';
  if (hour < 17) return 'Good afternoon';
  return 'Good evening';
}
