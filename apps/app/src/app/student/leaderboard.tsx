import React from 'react';

import { LeaderboardView } from '@/components/LeaderboardView';
import { Muted, Screen, Title } from '@/components/ui';
import { spacing } from '@/theme';

export default function StudentLeaderboard() {
  return (
    <Screen testID="student-leaderboard">
      <Title>Leaderboard</Title>
      <Muted style={{ marginBottom: spacing.lg }}>
        10 points per approved video, 25 for hitting the week, 5 for each extra.
      </Muted>

      <LeaderboardView
        compact
        scopes={[
          { key: 'batch', label: 'My batch' },
          { key: 'coach', label: 'My coach' },
          { key: 'academy', label: 'Academy' },
        ]}
      />
    </Screen>
  );
}
