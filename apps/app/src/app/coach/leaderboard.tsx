import { useQuery } from '@tanstack/react-query';
import React from 'react';

import { endpoints, queryKeys } from '@/api/endpoints';
import { LeaderboardView } from '@/components/LeaderboardView';
import { Loading, Muted, Screen, Title } from '@/components/ui';
import { spacing } from '@/theme';

export default function CoachLeaderboard() {
  const rosterQuery = useQuery({ queryKey: queryKeys.roster, queryFn: endpoints.roster });

  if (rosterQuery.isLoading) return <Loading label="Loading rankings…" />;

  return (
    <Screen testID="coach-leaderboard">
      <Title>Leaderboard</Title>
      <Muted style={{ marginBottom: spacing.lg }}>
        Who is actually putting the work in — not just turning up.
      </Muted>

      <LeaderboardView
        batches={rosterQuery.data?.batches ?? []}
        scopes={[
          { key: 'coach', label: 'My students' },
          { key: 'batch', label: 'By batch' },
          { key: 'academy', label: 'Academy' },
        ]}
      />
    </Screen>
  );
}
