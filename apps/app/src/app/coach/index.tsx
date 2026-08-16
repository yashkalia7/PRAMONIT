import { useQuery } from '@tanstack/react-query';
import { router } from 'expo-router';
import React from 'react';
import { Text, View } from 'react-native';

import { endpoints, queryKeys } from '@/api/endpoints';
import type { BatchStat, RosterEntry } from '@/api/types';
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
  Title,
} from '@/components/ui';
import { useAuth } from '@/store/auth';
import { colors, font, radius, spacing } from '@/theme';

export default function CoachDashboard() {
  const { user } = useAuth();
  const statsQuery = useQuery({ queryKey: queryKeys.stats, queryFn: endpoints.coachStats });
  const rosterQuery = useQuery({ queryKey: queryKeys.roster, queryFn: endpoints.roster });

  if (statsQuery.isLoading) return <Loading label="Loading your academy…" />;
  if (statsQuery.isError) {
    return (
      <Screen testID="coach-dashboard">
        <Notice testID="dashboard-error">{(statsQuery.error as Error).message}</Notice>
      </Screen>
    );
  }

  const stats = statsQuery.data!;
  const atRisk = (rosterQuery.data?.students ?? []).filter((s) => s.at_risk);

  return (
    <Screen testID="coach-dashboard">
      <Muted>Week of {stats.week_label}</Muted>
      <Title>{user?.full_name?.split(' ')[0] ?? 'Coach'}’s academy</Title>

      <Row gap={spacing.sm} style={{ marginTop: spacing.lg, flexWrap: 'wrap' }}>
        <StatTile value={stats.total_students} label="Students" testID="stat-students" />
        <StatTile
          value={stats.pending_reviews}
          label="To review"
          tone={stats.pending_reviews > 0 ? 'warning' : 'success'}
          testID="stat-pending"
        />
        <StatTile
          value={`${stats.compliance_pct}%`}
          label="On track"
          tone={stats.compliance_pct >= 70 ? 'success' : 'danger'}
          testID="stat-compliance"
        />
      </Row>

      {stats.pending_reviews > 0 && (
        <Card style={{ marginTop: spacing.lg, borderColor: colors.warning }} testID="review-cta">
          <Row style={{ justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <View style={{ flex: 1, paddingRight: spacing.md }}>
              <Text style={[font.h3, { color: colors.text }]}>
                {stats.pending_reviews} video{stats.pending_reviews === 1 ? '' : 's'} waiting
              </Text>
              <Muted style={{ marginTop: 2 }}>
                {stats.oldest_waiting_hours !== null
                  ? `Oldest has waited ${stats.oldest_waiting_hours}h. Anything past 72h auto-approves.`
                  : 'Review them to award points and ratings.'}
              </Muted>
            </View>
            <Button
              label="Review now"
              small
              testID="dashboard-review-cta"
              onPress={() => router.push('/coach/review')}
            />
          </Row>
        </Card>
      )}

      <SectionTitle>Batch compliance</SectionTitle>
      {stats.batches.length === 0 ? (
        <EmptyState
          emoji="👥"
          title="No students yet"
          body="Share the app with your batch — students pick you from the list when they register."
        />
      ) : (
        <View style={{ gap: spacing.sm }}>
          {stats.batches.map((batch) => (
            <BatchCard key={batch.batch_name} batch={batch} />
          ))}
        </View>
      )}

      <SectionTitle>Needs a nudge</SectionTitle>
      {atRisk.length === 0 ? (
        <Card>
          <Muted>
            Everyone has filmed or has something in your queue this week. Nothing to chase.
          </Muted>
        </Card>
      ) : (
        <View style={{ gap: spacing.sm }}>
          {atRisk.map((student) => (
            <AtRiskRow key={student.student_id} student={student} />
          ))}
        </View>
      )}
    </Screen>
  );
}

function BatchCard({ batch }: { batch: BatchStat }) {
  const good = batch.compliance_pct >= 70;
  return (
    <Card testID={`batch-${batch.batch_name}`} style={{ padding: spacing.md }}>
      <Row style={{ justifyContent: 'space-between', marginBottom: spacing.sm }}>
        <Text style={[font.h3, { color: colors.text }]}>{batch.batch_name}</Text>
        <Badge
          label={`${batch.compliance_pct}%`}
          tone={good ? 'success' : batch.compliance_pct >= 40 ? 'warning' : 'danger'}
        />
      </Row>
      <View
        style={{
          height: 8,
          borderRadius: radius.pill,
          backgroundColor: colors.surfaceHi,
          overflow: 'hidden',
        }}
      >
        <View
          style={{
            width: `${batch.compliance_pct}%`,
            height: '100%',
            backgroundColor: good ? colors.success : colors.warning,
          }}
        />
      </View>
      <Muted style={{ marginTop: spacing.sm }}>
        {batch.on_track} on track · {batch.at_risk} at risk · {batch.student_count} total
      </Muted>
    </Card>
  );
}

function AtRiskRow({ student }: { student: RosterEntry }) {
  return (
    <Card testID={`at-risk-${student.student_id}`} style={{ padding: spacing.md }}>
      <Row style={{ justifyContent: 'space-between' }}>
        <View style={{ flex: 1 }}>
          <Text style={[font.body, { color: colors.text, fontWeight: '700' }]}>
            {student.full_name}
          </Text>
          <Muted>
            {student.batch_name ?? 'No batch'} · 🔥 {student.current_weeks}w
          </Muted>
        </View>
        <Badge
          label={`${student.this_week_approved}/${student.required_count}`}
          tone="danger"
        />
      </Row>
    </Card>
  );
}
