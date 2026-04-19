import React from 'react';
import { Box, Text } from 'ink';
import type { UiState } from '../bridge/reducer.js';

export function StatusFooter({ state }: { state: UiState }): React.ReactNode {
  const permission = state.pendingPermissions[0];
  const status = permission
    ? `Waiting for approval: ${permission.tool}`
    : state.lastError
      ? `Failed: ${state.lastError}`
      : state.status;
  return (
    <Box marginTop={1}>
      <Text color="gray">
        {status}
        {state.sessionId ? ` | session ${state.sessionId.slice(0, 8)}` : ''}
        {state.workdir ? ` | ${state.workdir}` : ''}
        {' | /help /clear /exit'}
      </Text>
    </Box>
  );
}
