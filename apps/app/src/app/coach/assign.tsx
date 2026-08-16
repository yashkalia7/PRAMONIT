import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import React, { useMemo, useState } from 'react';
import { Pressable, Text, View } from 'react-native';

import { endpoints, queryKeys } from '@/api/endpoints';
import type { Drill } from '@/api/types';
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
import { useAuth } from '@/store/auth';
import { colors, font, radius, spacing } from '@/theme';

export default function AssignScreen() {
  const { user } = useAuth();
  const queryClient = useQueryClient();

  const drillsQuery = useQuery({ queryKey: queryKeys.drills, queryFn: endpoints.drills });
  const rosterQuery = useQuery({ queryKey: queryKeys.roster, queryFn: endpoints.roster });
  const assignmentsQuery = useQuery({
    queryKey: queryKeys.assignments,
    queryFn: () => endpoints.assignments(8),
  });

  const batches = useMemo(() => {
    const fromRoster = rosterQuery.data?.batches ?? [];
    const fromProfile = user?.coach_profile?.batches ?? [];
    return Array.from(new Set([...fromProfile, ...fromRoster]));
  }, [rosterQuery.data, user]);

  const [batch, setBatch] = useState<string | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [notes, setNotes] = useState('');
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [newTitle, setNewTitle] = useState('');
  const [newTarget, setNewTarget] = useState('');

  const activeBatch = batch ?? batches[0] ?? null;

  const assign = useMutation({
    mutationFn: () =>
      endpoints.assign({
        batch_name: activeBatch!,
        notes: notes.trim() || null,
        drills: selected.map((id) => ({ drill_id: id })),
      }),
    onSuccess: async () => {
      setError(null);
      setStatus(`Assigned ${selected.length} drill(s) to ${activeBatch} for this week.`);
      await queryClient.invalidateQueries();
    },
    onError: (err: Error) => {
      setStatus(null);
      setError(err.message);
    },
  });

  const createDrill = useMutation({
    mutationFn: () =>
      endpoints.createDrill({
        title: newTitle.trim(),
        target_value: Number(newTarget.trim()) || 0,
        metric_type: 'reps',
      }),
    onSuccess: async (drill) => {
      setNewTitle('');
      setNewTarget('');
      setSelected((current) => [...current, drill.id]);
      await queryClient.invalidateQueries({ queryKey: queryKeys.drills });
    },
    onError: (err: Error) => setError(err.message),
  });

  if (drillsQuery.isLoading) return <Loading label="Loading the drill library…" />;

  const drills = drillsQuery.data ?? [];

  return (
    <Screen testID="assign-screen">
      <Title>Set this week’s work</Title>
      <Muted style={{ marginBottom: spacing.lg }}>
        Pick a batch and the drills every student in it should film this week.
      </Muted>

      {!!error && <Notice testID="assign-error">{error}</Notice>}
      {!!status && (
        <Notice tone="success" testID="assign-success">
          {status}
        </Notice>
      )}

      <SectionTitle>Batch</SectionTitle>
      {batches.length === 0 ? (
        <EmptyState
          emoji="👥"
          title="No batches yet"
          body="Add batches to your coach profile, or wait for students to register with one."
        />
      ) : (
        <Row style={{ flexWrap: 'wrap' }} gap={spacing.sm}>
          {batches.map((name) => (
            <Chip
              key={name}
              label={name}
              selected={activeBatch === name}
              testID={`assign-batch-${name}`}
              onPress={() => setBatch(name)}
            />
          ))}
        </Row>
      )}

      <SectionTitle>Drills · {selected.length} selected</SectionTitle>
      <View style={{ gap: spacing.sm }}>
        {drills.map((drill) => (
          <DrillPick
            key={drill.id}
            drill={drill}
            selected={selected.includes(drill.id)}
            onToggle={() =>
              setSelected((current) =>
                current.includes(drill.id)
                  ? current.filter((id) => id !== drill.id)
                  : [...current, drill.id],
              )
            }
          />
        ))}
      </View>

      <SectionTitle>Add your own drill</SectionTitle>
      <Card>
        <Row gap={spacing.sm} style={{ alignItems: 'flex-start' }}>
          <View style={{ flex: 2 }}>
            <Field
              label="Title"
              testID="new-drill-title"
              value={newTitle}
              onChangeText={setNewTitle}
              placeholder="Weak-foot wall pass"
            />
          </View>
          <View style={{ flex: 1 }}>
            <Field
              label="Reps"
              testID="new-drill-target"
              value={newTarget}
              onChangeText={setNewTarget}
              placeholder="300"
              keyboardType="numeric"
            />
          </View>
        </Row>
        <Button
          label="Add to library"
          variant="secondary"
          testID="create-drill"
          disabled={newTitle.trim().length < 3}
          loading={createDrill.isPending}
          onPress={() => createDrill.mutate()}
          full
        />
      </Card>

      <SectionTitle>Note for the batch</SectionTitle>
      <Card>
        <Field
          label="Notes"
          testID="assign-notes"
          value={notes}
          onChangeText={setNotes}
          placeholder="Control before speed. Film from the side."
          multiline
        />
      </Card>

      <Button
        label="Assign to this week"
        testID="assign-submit"
        disabled={!activeBatch || selected.length === 0}
        loading={assign.isPending}
        onPress={() => assign.mutate()}
        full
        style={{ marginTop: spacing.lg }}
      />

      <SectionTitle>Recent assignments</SectionTitle>
      {assignmentsQuery.data?.length ? (
        <View style={{ gap: spacing.sm }}>
          {assignmentsQuery.data.map((assignment) => (
            <Card key={assignment.id} style={{ padding: spacing.md }}>
              <Row style={{ justifyContent: 'space-between' }}>
                <Text style={[font.h3, { color: colors.text }]}>{assignment.batch_name}</Text>
                <Badge label={assignment.week_label} />
              </Row>
              <Muted style={{ marginTop: 4 }}>
                {assignment.items.map((item) => item.drill.title).join(' · ') || 'No drills'}
              </Muted>
            </Card>
          ))}
        </View>
      ) : (
        <Muted>Nothing assigned yet.</Muted>
      )}
    </Screen>
  );
}

function DrillPick({
  drill,
  selected,
  onToggle,
}: {
  drill: Drill;
  selected: boolean;
  onToggle: () => void;
}) {
  return (
    <Pressable
      testID={`pick-drill-${drill.slug}`}
      accessibilityRole="checkbox"
      accessibilityState={{ checked: selected }}
      onPress={onToggle}
      style={{
        padding: spacing.md,
        borderRadius: radius.md,
        borderWidth: 1,
        borderColor: selected ? colors.primary : colors.border,
        backgroundColor: selected ? colors.primarySoft : colors.surface,
      }}
    >
      <Row style={{ justifyContent: 'space-between' }}>
        <View style={{ flex: 1, paddingRight: spacing.md }}>
          <Text style={[font.h3, { color: selected ? colors.primary : colors.text }]}>
            {selected ? '☑  ' : '☐  '}
            {drill.title}
          </Text>
          {!!drill.description && <Muted style={{ marginTop: 2 }}>{drill.description}</Muted>}
        </View>
        <Badge label={drill.target_label} tone="info" />
      </Row>
    </Pressable>
  );
}
