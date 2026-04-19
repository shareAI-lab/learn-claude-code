import React from 'react';
import { Box, Text } from 'ink';
import type { TaskItemPayload } from '../bridge/protocol.js';

export function TaskPanel({ tasks }: { tasks: TaskItemPayload[] }): React.ReactNode {
  if (tasks.length === 0) {
    return null;
  }
  return (
    <Box flexDirection="column" borderStyle="round" borderColor="green" paddingX={1} marginBottom={1}>
      <Text color="green">Tasks ({tasks.length})</Text>
      {tasks.map(task => (
        <Text key={task.id}>
          {task.id} [{task.status}] {task.content}
          {task.owner ? ` owner=${task.owner}` : ''}
        </Text>
      ))}
    </Box>
  );
}
