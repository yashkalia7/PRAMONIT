import { useQuery, useQueryClient } from '@tanstack/react-query';
import { router } from 'expo-router';
import React, { useMemo, useState } from 'react';
import { Text, View } from 'react-native';

import { ApiError } from '@/api/client';
import { endpoints, queryKeys } from '@/api/endpoints';
import type { Drill } from '@/api/types';
import { VideoPicker } from '@/components/VideoPicker';
import {
  Badge,
  Button,
  Card,
  Chip,
  Field,
  Loading,
  Muted,
  Notice,
  Row,
  Screen,
  SectionTitle,
  Title,
} from '@/components/ui';
import { STAGE_LABEL, uploadSubmission, type UploadStage } from '@/lib/upload';
import { formatBytes, type PickedVideo } from '@/lib/video';
import { colors, font, spacing } from '@/theme';

export default function UploadScreen() {
  const queryClient = useQueryClient();

  const assignmentQuery = useQuery({
    queryKey: queryKeys.assignment,
    queryFn: endpoints.currentAssignment,
  });

  const [video, setVideo] = useState<PickedVideo | null>(null);
  const [drillId, setDrillId] = useState<string | null>(null);
  const [reps, setReps] = useState('');
  const [note, setNote] = useState('');
  const [stage, setStage] = useState<UploadStage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  const drills: Drill[] = useMemo(
    () =>
      assignmentQuery.data?.assignment?.items.map((item) => item.drill) ??
      assignmentQuery.data?.fallback_drills ??
      [],
    [assignmentQuery.data],
  );

  const busy = stage !== null && stage !== 'done';

  const submit = async () => {
    if (!video) {
      setError('Choose a video first.');
      return;
    }
    setError(null);
    try {
      await uploadSubmission({
        video,
        drillId,
        repsClaimed: reps.trim() ? Number(reps.trim()) : null,
        note: note.trim() || null,
        onStage: setStage,
      });
      await queryClient.invalidateQueries();
      setDone(true);
    } catch (err) {
      setStage(null);
      if (err instanceof ApiError && err.status === 409) {
        setError(
          'This exact video has already been submitted. Record a fresh one — re-uploading old footage does not count.',
        );
      } else {
        setError(err instanceof Error ? err.message : 'Upload failed. Please try again.');
      }
    }
  };

  if (done) {
    return (
      <Screen testID="upload-success">
        <View style={{ alignItems: 'center', paddingVertical: spacing.xxxl }}>
          <Text style={{ fontSize: 56, marginBottom: spacing.md }}>✅</Text>
          <Title>Sent to your coach</Title>
          <Muted style={{ textAlign: 'center', marginTop: spacing.sm, maxWidth: 320 }}>
            It counts toward this week the moment your coach approves it — and auto-approves after
            72 hours if they haven't got to it.
          </Muted>
          <View style={{ marginTop: spacing.xl, gap: spacing.sm, alignSelf: 'stretch' }}>
            <Button
              label="Back to my week"
              testID="upload-done-home"
              onPress={() => router.replace('/student')}
              full
            />
            <Button
              label="Upload another"
              variant="secondary"
              testID="upload-again"
              onPress={() => {
                setVideo(null);
                setReps('');
                setNote('');
                setStage(null);
                setDone(false);
              }}
              full
            />
          </View>
        </View>
      </Screen>
    );
  }

  return (
    <Screen testID="upload-screen">
      <Title>Upload training</Title>
      <Muted style={{ marginBottom: spacing.lg }}>
        Film the whole set in one take, from the side, with the ball in frame.
      </Muted>

      {!!error && <Notice testID="upload-error">{error}</Notice>}

      <SectionTitle>Which drill?</SectionTitle>
      {assignmentQuery.isLoading ? (
        <Loading label="Loading drills…" />
      ) : (
        <Row style={{ flexWrap: 'wrap', marginBottom: spacing.md }} gap={spacing.sm}>
          {drills.map((drill) => (
            <Chip
              key={drill.id}
              label={drill.title}
              selected={drillId === drill.id}
              testID={`select-drill-${drill.slug}`}
              onPress={() => {
                setDrillId(drill.id);
                if (drill.metric_type === 'reps' && !reps) setReps(String(drill.target_value));
              }}
            />
          ))}
        </Row>
      )}

      <SectionTitle>Your video</SectionTitle>
      <Card>
        {video ? (
          <View style={{ gap: spacing.sm }}>
            <Row style={{ justifyContent: 'space-between' }}>
              <Text style={[font.h3, { color: colors.text, flex: 1 }]} numberOfLines={1}>
                {video.name}
              </Text>
              <Badge label={video.source} tone="info" />
            </Row>
            <Muted testID="video-size">
              {formatBytes(video.size || video.bytes?.byteLength || 0)} · {video.mimeType}
            </Muted>
            <Button
              label="Choose a different video"
              variant="ghost"
              small
              testID="clear-video"
              onPress={() => setVideo(null)}
              disabled={busy}
            />
          </View>
        ) : (
          <VideoPicker onPick={setVideo} onError={setError} disabled={busy} />
        )}
      </Card>

      <SectionTitle>Details</SectionTitle>
      <Card>
        <Field
          label="Reps completed"
          testID="upload-reps"
          value={reps}
          onChangeText={setReps}
          placeholder="200"
          keyboardType="numeric"
        />
        <Field
          label="Note for your coach"
          testID="upload-note"
          value={note}
          onChangeText={setNote}
          placeholder="Left foot felt better today."
          multiline
        />
      </Card>

      {busy && (
        <Notice tone="info" testID="upload-progress">
          {STAGE_LABEL[stage!]}
        </Notice>
      )}

      <Button
        label="Submit to my coach"
        testID="upload-submit"
        onPress={submit}
        loading={busy}
        disabled={!video}
        full
        style={{ marginTop: spacing.lg }}
      />
      <Muted style={{ marginTop: spacing.md, textAlign: 'center' }}>
        Every video is fingerprinted. The same clip can never be submitted twice.
      </Muted>
    </Screen>
  );
}
