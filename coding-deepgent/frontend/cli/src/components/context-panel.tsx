import React from 'react';
import { Box, Text } from 'ink';
import type { ContextSnapshotPayload } from '../bridge/protocol.js';

export function ContextPanel({
  snapshot
}: {
  snapshot: ContextSnapshotPayload | undefined;
}): React.ReactNode {
  if (!snapshot) {
    return null;
  }
  const pressure = `${snapshot.visible_messages}/${snapshot.history_messages} raw visible`;
  const compact = `compact ${snapshot.compact_count} collapse ${snapshot.collapse_count}`;
  const latest = snapshot.latest_event ? ` latest ${snapshot.latest_event}` : '';
  return (
    <Box flexDirection="column" borderStyle="round" borderColor="yellow" paddingX={1} marginBottom={1}>
      <Text color="yellow">Context ({snapshot.projection_mode})</Text>
      <Text>
        model {snapshot.model_messages} | {pressure} | hidden {snapshot.hidden_messages}
      </Text>
      <Text>
        {compact} | session memory {snapshot.session_memory_status}
        {latest}
      </Text>
    </Box>
  );
}
