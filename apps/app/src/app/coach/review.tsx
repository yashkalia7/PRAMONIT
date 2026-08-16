import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import React, { useEffect, useMemo, useState } from 'react';
import { Platform, Pressable, Text, View } from 'react-native';

import { endpoints, queryKeys } from '@/api/endpoints';
import type { Submission } from '@/api/types';
import { VideoPreview } from '@/components/VideoPreview';
import {
  Badge,
  Button,
  Card,
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
import { colors, font, radius, spacing } from '@/theme';

export default function ReviewScreen() {
  const queryClient = useQueryClient();
  const { isDesktop } = useResponsive();

  const queueQuery = useQuery({ queryKey: queryKeys.queue, queryFn: () => endpoints.reviewQueue(50) });

  const [index, setIndex] = useState(0);
  const [rating, setRating] = useState<number | null>(null);
  const [feedback, setFeedback] = useState('');
  const [error, setError] = useState<string | null>(null);

  const items = queueQuery.data?.items ?? [];
  const current = items[Math.min(index, Math.max(0, items.length - 1))] ?? null;

  useEffect(() => {
    // Fresh form for each video — carrying a rating over would silently apply
    // one student's mark to the next.
    setRating(null);
    setFeedback('');
  }, [current?.id]);

  const decide = useMutation({
    mutationFn: async (decision: 'approved' | 'rejected') => {
      if (!current) return;
      return endpoints.review(current.id, {
        decision,
        rating: decision === 'approved' ? rating : null,
        feedback: feedback.trim() || null,
      });
    },
    onSuccess: async () => {
      setError(null);
      await queryClient.invalidateQueries();
      setIndex((i) => Math.max(0, Math.min(i, items.length - 2)));
    },
    onError: (err: Error) => setError(err.message),
  });

  // Desktop keyboard shortcuts: a coach clearing thirty videos should never
  // have to reach for the mouse.
  useEffect(() => {
    if (Platform.OS !== 'web' || typeof document === 'undefined') return;
    const onKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (target && ['INPUT', 'TEXTAREA'].includes(target.tagName)) return;
      const key = event.key.toLowerCase();
      if (key === 'a') decide.mutate('approved');
      else if (key === 'r') decide.mutate('rejected');
      else if (key === 'j') setIndex((i) => Math.min(items.length - 1, i + 1));
      else if (key === 'k') setIndex((i) => Math.max(0, i - 1));
      else if (key >= '1' && key <= '5') setRating(Number(key));
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [decide, items.length]);

  const waited = useMemo(() => {
    if (!current) return null;
    const hours = (Date.now() - new Date(current.submitted_at).getTime()) / 3_600_000;
    return Math.max(0, Math.round(hours * 10) / 10);
  }, [current]);

  if (queueQuery.isLoading) return <Loading label="Loading the review queue…" />;

  if (!current) {
    return (
      <Screen testID="review-screen">
        <Title>Review</Title>
        <EmptyState
          emoji="✅"
          title="Queue clear"
          body="Nothing is waiting on you. Every video your students send lands here."
          testID="queue-empty"
        />
      </Screen>
    );
  }

  return (
    <Screen testID="review-screen">
      <Row style={{ justifyContent: 'space-between', marginBottom: spacing.md }}>
        <Title>Review</Title>
        <Badge
          label={`${queueQuery.data?.total_pending ?? items.length} pending`}
          tone="warning"
          testID="pending-count"
        />
      </Row>

      {!!error && <Notice testID="review-error">{error}</Notice>}

      {waited !== null && waited > 48 && (
        <Notice tone="warning" testID="auto-approve-warning">
          Waiting {waited}h — auto-approves at 72h.
        </Notice>
      )}

      <View style={{ flexDirection: isDesktop ? 'row' : 'column', gap: spacing.lg }}>
        <View style={{ flex: isDesktop ? 3 : undefined }}>
          <VideoPreview url={current.playback_url} height={isDesktop ? 420 : 240} />

          <Card style={{ marginTop: spacing.md }}>
            <Row style={{ justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <View style={{ flex: 1 }}>
                <Text style={[font.h2, { color: colors.text }]} testID="review-student">
                  {current.student_name ?? 'Student'}
                </Text>
                <Muted>
                  {current.batch_name ?? 'No batch'} · {current.week_label}
                </Muted>
              </View>
              <Badge label={current.source} tone="info" />
            </Row>

            <View style={{ marginTop: spacing.md, gap: 4 }}>
              <Text style={[font.h3, { color: colors.primary }]} testID="review-drill">
                {current.drill?.title ?? 'Training video'}
              </Text>
              <Muted>
                {current.drill?.target_label ? `Target ${current.drill.target_label}` : ''}
                {current.reps_claimed ? ` · claimed ${current.reps_claimed}` : ''}
                {current.duration_sec ? ` · ${current.duration_sec}s` : ''}
                {waited !== null ? ` · waited ${waited}h` : ''}
              </Muted>
            </View>

            {!!current.student_note && (
              <Notice tone="info" testID="student-note">
                “{current.student_note}”
              </Notice>
            )}
          </Card>
        </View>

        <View style={{ flex: isDesktop ? 2 : undefined }}>
          <Card>
            <SectionTitle>Rating</SectionTitle>
            <Row gap={spacing.sm}>
              {[1, 2, 3, 4, 5].map((star) => (
                <Pressable
                  key={star}
                  testID={`rate-${star}`}
                  accessibilityRole="button"
                  accessibilityLabel={`Rate ${star} out of 5`}
                  onPress={() => setRating(star)}
                  style={{
                    width: 44,
                    height: 44,
                    borderRadius: radius.md,
                    alignItems: 'center',
                    justifyContent: 'center',
                    borderWidth: 1,
                    borderColor: (rating ?? 0) >= star ? colors.primary : colors.border,
                    backgroundColor:
                      (rating ?? 0) >= star ? colors.primarySoft : colors.surfaceAlt,
                  }}
                >
                  <Text style={{ fontSize: 18 }}>{(rating ?? 0) >= star ? '⭐' : '☆'}</Text>
                </Pressable>
              ))}
            </Row>
            <Muted style={{ marginTop: spacing.sm }}>
              4 or 5 stars awards the student a bonus.
            </Muted>

            <View style={{ marginTop: spacing.lg }}>
              <Field
                label="Feedback"
                testID="review-feedback"
                value={feedback}
                onChangeText={setFeedback}
                placeholder="Good tempo. Head up more between touches."
                multiline
              />
            </View>

            <Row gap={spacing.sm}>
              <View style={{ flex: 1 }}>
                <Button
                  label="Approve"
                  variant="success"
                  testID="approve-button"
                  loading={decide.isPending}
                  onPress={() => decide.mutate('approved')}
                  full
                />
              </View>
              <View style={{ flex: 1 }}>
                <Button
                  label="Reject"
                  variant="danger"
                  testID="reject-button"
                  loading={decide.isPending}
                  onPress={() => decide.mutate('rejected')}
                  full
                />
              </View>
            </Row>

            {items.length > 1 && (
              <Row gap={spacing.sm} style={{ marginTop: spacing.md }}>
                <Button
                  label="← Prev"
                  variant="ghost"
                  small
                  testID="prev-video"
                  onPress={() => setIndex((i) => Math.max(0, i - 1))}
                />
                <Muted style={{ flex: 1, textAlign: 'center' }}>
                  {Math.min(index + 1, items.length)} of {items.length}
                </Muted>
                <Button
                  label="Skip →"
                  variant="ghost"
                  small
                  testID="next-video"
                  onPress={() => setIndex((i) => Math.min(items.length - 1, i + 1))}
                />
              </Row>
            )}

            {Platform.OS === 'web' && (
              <Muted style={{ marginTop: spacing.md, textAlign: 'center' }}>
                Shortcuts: A approve · R reject · J/K next/prev · 1–5 rate
              </Muted>
            )}
          </Card>
        </View>
      </View>
    </Screen>
  );
}
