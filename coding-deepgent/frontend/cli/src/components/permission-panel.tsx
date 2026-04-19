import React from 'react';
import { Box, Text, useInput } from 'ink';
import type { FrontendInput } from '../bridge/protocol.js';
import type { PendingPermission } from '../bridge/reducer.js';

export function PermissionPanel({
  permissions,
  send
}: {
  permissions: PendingPermission[];
  send: (input: FrontendInput) => void;
}): React.ReactNode {
  const current = permissions[0];
  useInput(input => {
    if (!current) return;
    if (input.toLowerCase() === 'a') {
      send({ type: 'permission_decision', request_id: current.requestId, decision: 'approve' });
    }
    if (input.toLowerCase() === 'r') {
      send({ type: 'permission_decision', request_id: current.requestId, decision: 'reject' });
    }
  });

  if (!current) {
    return null;
  }
  return (
    <Box flexDirection="column" borderStyle="double" borderColor="yellow" paddingX={1} marginBottom={1}>
      <Text color="yellow">Permission required: {current.tool}</Text>
      <Text>{current.description}</Text>
      <Text color="gray">Press a to approve, r to reject.</Text>
    </Box>
  );
}

