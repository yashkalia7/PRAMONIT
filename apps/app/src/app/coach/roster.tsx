import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import React, { useMemo, useState } from 'react';
import { Text, View } from 'react-native';

import { endpoints, queryKeys } from '@/api/endpoints';
import type { RosterEntry } from '@/api/types';
import {
  Badge,
  Button,
  Card,
  Chip,
  EmptyState,
  Field,
  Loading,
  Muted,
  Notice,
  Row,
  Screen,
  SectionTitle,
  Title,
} from '@/components/ui';
import { useResponsive } from '@/hooks/useResponsive';
import { colors, font, spacing } from '@/theme';

type SortKey = 'name' | 'streak' | 'points' | 'risk';

export default function RosterScreen() {
  const queryClient = useQueryClient();
  const { isDesktop } = useResponsive();
  const rosterQuery = useQuery({ queryKey: queryKeys.roster, queryFn: endpoints.roster });

  const [batchFilter, setBatchFilter] = useState<string | null>(null);
  const [sort, setSort] = useState<SortKey>('risk');
  const [editing, setEditing] = useState<string | null>(null);
  const [newBatch, setNewBatch] = useState('');
  const [error, setError] = useState<string | null>(null);

  const update = useMutation({
    mutationFn: (args: { id: string; body: { batch_name?: string; remove?: boolean } }) =>
      endpoints.updateRoster(args.id, args.body),
    onSuccess: async () => {
      setEditing(null);
      setNewBatch('');
      setError(null);
      await queryClient.invalidateQueries();
    },
    onError: (err: Error) => setError(err.message),
  });

  const students = useMemo(() => {
    let list = rosterQuery.data?.students ?? [];
    if (batchFilter) list = list.filter((s) => s.batch_name === batchFilter);
    const sorted = [...list];
    sorted.sort((a, b) => {
      if (sort === 'name') return a.full_name.localeCompare(b.full_name);
      if (sort === 'streak') return b.current_weeks - a.current_weeks;
      if (sort === 'points') return b.points - a.points;
      return Number(b.at_risk) - Number(a.at_risk) || a.full_name.localeCompare(b.full_name);
    });
    return sorted;
  }, [rosterQuery.data, batchFilter, sort]);

  if (rosterQuery.isLoading) return <Loading label="Loading your roster…" />;

  const batches = rosterQuery.data?.batches ?? [];

  return (
    <Screen testID="roster-screen">
      <Title>Roster</Title>
      <Muted style={{ marginBottom: spacing.lg }}>
        {rosterQuery.data?.students.length ?? 0} active students
      </Muted>

      {!!error && <Notice testID="roster-error">{error}</Notice>}

      {batches.length > 0 && (
        <Row style={{ flexWrap: 'wrap', marginBottom: spacing.sm }} gap={spacing.sm}>
          <Chip
            label="All batches"
            selected={batchFilter === null}
            testID="filter-all"
            onPress={() => setBatchFilter(null)}
          />
          {batches.map((batch) => (
            <Chip
              key={batch}
              label={batch}
              selected={batchFilter === batch}
              testID={`filter-${batch}`}
              onPress={() => setBatchFilter(batch)}
            />
          ))}
        </Row>
      )}

      <Row style={{ flexWrap: 'wrap' }} gap={spacing.sm}>
        {([
          ['risk', 'At risk first'],
          ['streak', 'Streak'],
          ['points', 'Points'],
          ['name', 'Name'],
        ] as [SortKey, string][]).map(([key, label]) => (
          <Chip
            key={key}
            label={label}
            selected={sort === key}
            testID={`sort-${key}`}
            onPress={() => setSort(key)}
          />
        ))}
      </Row>

      <SectionTitle>Students</SectionTitle>

      {students.length === 0 ? (
        <EmptyState
          emoji="👥"
          title="No students here yet"
          body="Students appear the moment they pick you during registration."
        />
      ) : (
        <View style={{ gap: spacing.sm }}>
          {isDesktop && (
            <Row style={{ paddingHorizontal: spacing.lg }} gap={spacing.md}>
              <Text style={[font.label, { color: colors.textFaint, flex: 3 }]}>PLAYER</Text>
              <Text style={[font.label, { color: colors.textFaint, flex: 2 }]}>BATCH</Text>
              <Text style={[font.label, { color: colors.textFaint, width: 70 }]}>WEEK</Text>
              <Text style={[font.label, { color: colors.textFaint, width: 60 }]}>STREAK</Text>
              <Text style={[font.label, { color: colors.textFaint, width: 60 }]}>PTS</Text>
              <View style={{ width: 90 }} />
            </Row>
          )}

          {students.map((student) => (
            <Card
              key={student.student_id}
              testID={`roster-${student.student_id}`}
              style={{ padding: spacing.md }}
            >
              <View
                style={{
                  flexDirection: isDesktop ? 'row' : 'column',
                  alignItems: isDesktop ? 'center' : 'flex-start',
                  gap: spacing.md,
                }}
              >
                <View style={{ flex: isDesktop ? 3 : undefined }}>
                  <Text style={[font.body, { color: colors.text, fontWeight: '700' }]}>
                    {student.full_name}
                    {student.jersey_number ? `  #${student.jersey_number}` : ''}
                  </Text>
                  <Muted>{student.preferred_position ?? student.email}</Muted>
                </View>

                <View style={{ flex: isDesktop ? 2 : undefined }}>
                  <Muted>{student.batch_name ?? '—'}</Muted>
                </View>

                <View style={{ width: isDesktop ? 70 : undefined }}>
                  <Badge
                    label={`${student.this_week_approved}/${student.required_count}`}
                    tone={student.at_risk ? 'danger' : 'success'}
                    testID={`week-${student.student_id}`}
                  />
                  {student.this_week_pending > 0 && (
                    <Muted>{student.this_week_pending} pending</Muted>
                  )}
                </View>

                <Text style={[font.body, { color: colors.text, width: isDesktop ? 60 : undefined }]}>
                  🔥 {student.current_weeks}
                </Text>
                <Text style={[font.body, { color: colors.text, width: isDesktop ? 60 : undefined }]}>
                  {student.points}
                </Text>

                <View style={{ width: isDesktop ? 90 : undefined }}>
                  <Button
                    label={editing === student.student_id ? 'Cancel' : 'Edit'}
                    variant="ghost"
                    small
                    testID={`edit-${student.student_id}`}
                    onPress={() => {
                      setEditing(editing === student.student_id ? null : student.student_id);
                      setNewBatch(student.batch_name ?? '');
                    }}
                  />
                </View>
              </View>

              {editing === student.student_id && (
                <View style={{ marginTop: spacing.md }}>
                  <Field
                    label="Move to batch"
                    testID="edit-batch-input"
                    value={newBatch}
                    onChangeText={setNewBatch}
                    placeholder="Powai batch"
                  />
                  <Row gap={spacing.sm}>
                    <Button
                      label="Save batch"
                      small
                      testID="save-batch"
                      loading={update.isPending}
                      onPress={() =>
                        update.mutate({
                          id: student.student_id,
                          body: { batch_name: newBatch.trim() },
                        })
                      }
                    />
                    <Button
                      label="Remove from roster"
                      variant="danger"
                      small
                      testID={`remove-${student.student_id}`}
                      loading={update.isPending}
                      onPress={() =>
                        update.mutate({ id: student.student_id, body: { remove: true } })
                      }
                    />
                  </Row>
                </View>
              )}
            </Card>
          ))}
        </View>
      )}
    </Screen>
  );
}
