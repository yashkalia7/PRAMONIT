import { useQuery } from '@tanstack/react-query';
import React, { useState } from 'react';
import { Text, View } from 'react-native';

import { endpoints, queryKeys } from '@/api/endpoints';
import type { LeaderboardRow, LeaderboardScope, LeaderboardWindow } from '@/api/types';

import { Card, Chip, EmptyState, Loading, Muted, Notice, Row, SectionTitle } from './ui';
import { colors, font, radius, spacing } from '@/theme';

const MEDALS = ['🥇', '🥈', '🥉'];

export function LeaderboardView({
  scopes,
  batches,
  compact,
}: {
  scopes: { key: LeaderboardScope; label: string }[];
  /** Coaches must name a batch for the batch scope; students never do. */
  batches?: string[];
  compact?: boolean;
}) {
  const [scope, setScope] = useState<LeaderboardScope>(scopes[0].key);
  const [window, setWindow] = useState<LeaderboardWindow>('week');
  const [batch, setBatch] = useState<string | undefined>(batches?.[0]);

  const needsBatch = scope === 'batch' && !!batches;
  const query = useQuery({
    queryKey: queryKeys.leaderboard(scope, window, needsBatch ? batch : undefined),
    queryFn: () => endpoints.leaderboard(scope, window, needsBatch ? batch : undefined),
    enabled: !needsBatch || !!batch,
  });

  return (
    <View testID="leaderboard-view">
      <Row style={{ flexWrap: 'wrap' }} gap={spacing.sm}>
        {scopes.map((item) => (
          <Chip
            key={item.key}
            label={item.label}
            selected={scope === item.key}
            testID={`scope-${item.key}`}
            onPress={() => setScope(item.key)}
          />
        ))}
      </Row>

      <Row style={{ marginTop: spacing.sm }} gap={spacing.sm}>
        <Chip
          label="This week"
          selected={window === 'week'}
          testID="window-week"
          onPress={() => setWindow('week')}
        />
        <Chip
          label="All time"
          selected={window === 'all'}
          testID="window-all"
          onPress={() => setWindow('all')}
        />
      </Row>

      {needsBatch && batches!.length > 0 && (
        <Row style={{ marginTop: spacing.sm, flexWrap: 'wrap' }} gap={spacing.sm}>
          {batches!.map((name) => (
            <Chip
              key={name}
              label={name}
              selected={batch === name}
              testID={`lb-batch-${name}`}
              onPress={() => setBatch(name)}
            />
          ))}
        </Row>
      )}

      <SectionTitle>
        {query.data ? `${query.data.total_students} students` : 'Rankings'}
      </SectionTitle>

      {query.isLoading ? (
        <Loading label="Loading rankings…" />
      ) : query.isError ? (
        <Notice>{(query.error as Error).message}</Notice>
      ) : !query.data?.rows.length ? (
        <EmptyState
          emoji="🏆"
          title="Nobody on the board yet"
          body="Approved videos start putting points on here."
        />
      ) : (
        <Card padded={false} testID="leaderboard-table">
          {query.data.rows.map((row, index) => (
            <RankRow
              key={row.student_id}
              row={row}
              last={index === query.data!.rows.length - 1}
              // A gap in rank means the viewer was pinned below the cut.
              gapBefore={index > 0 && row.rank > query.data!.rows[index - 1].rank + 1}
              compact={compact}
            />
          ))}
        </Card>
      )}
    </View>
  );
}

function RankRow({
  row,
  last,
  gapBefore,
  compact,
}: {
  row: LeaderboardRow;
  last: boolean;
  gapBefore: boolean;
  compact?: boolean;
}) {
  return (
    <>
      {gapBefore && (
        <View style={{ paddingVertical: spacing.xs, alignItems: 'center' }}>
          <Text style={{ color: colors.textFaint, letterSpacing: 4 }}>· · ·</Text>
        </View>
      )}
      <View
        testID={row.is_viewer ? 'leaderboard-viewer-row' : `rank-${row.rank}`}
        style={{
          flexDirection: 'row',
          alignItems: 'center',
          gap: spacing.md,
          paddingVertical: spacing.md,
          paddingHorizontal: spacing.lg,
          borderBottomWidth: last ? 0 : 1,
          borderBottomColor: colors.border,
          backgroundColor: row.is_viewer ? colors.primarySoft : 'transparent',
          borderRadius: row.is_viewer ? radius.md : 0,
        }}
      >
        <Text style={[font.h3, { color: colors.textMuted, width: 34 }]}>
          {row.rank <= 3 ? MEDALS[row.rank - 1] : row.rank}
        </Text>

        <View style={{ flex: 1 }}>
          <Text
            style={[font.body, { color: row.is_viewer ? colors.primary : colors.text, fontWeight: '700' }]}
            numberOfLines={1}
          >
            {row.full_name}
            {row.is_viewer ? '  (you)' : ''}
          </Text>
          {!compact && !!row.batch_name && <Muted>{row.batch_name}</Muted>}
        </View>

        <View style={{ alignItems: 'flex-end' }}>
          <Text style={[font.h3, { color: colors.text }]}>{row.points}</Text>
          <Muted>
            🔥 {row.current_weeks}w · {row.approved_total} vids
          </Muted>
        </View>
      </View>
    </>
  );
}
