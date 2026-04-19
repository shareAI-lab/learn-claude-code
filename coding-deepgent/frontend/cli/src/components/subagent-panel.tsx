import React from 'react';
import { Box, Text } from 'ink';
import type { SubagentItemPayload } from '../bridge/protocol.js';

export function SubagentPanel({
  snapshot
}: {
  snapshot: { total: number; items: SubagentItemPayload[] } | undefined;
}): React.ReactNode {
  if (!snapshot || snapshot.total === 0) {
    return null;
  }
  return (
    <Box flexDirection="column" borderStyle="round" borderColor="magenta" paddingX={1} marginBottom={1}>
      <Text color="magenta">Subagents ({snapshot.total})</Text>
      {snapshot.items.map(item => (
        <Text key={`${item.subagent_thread_id}-${item.created_at}`}>
          {item.agent_type}/{item.role} {trim(item.content)}
        </Text>
      ))}
    </Box>
  );
}

function trim(text: string): string {
  return text.length > 100 ? `${text.slice(0, 97)}...` : text;
}
