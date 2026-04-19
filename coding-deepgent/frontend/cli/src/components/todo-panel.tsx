import React from 'react';
import { Box, Text } from 'ink';
import type { TodoItemPayload } from '../bridge/protocol.js';

export function TodoPanel({ todos }: { todos: TodoItemPayload[] }): React.ReactNode {
  if (todos.length === 0) {
    return null;
  }
  const completed = todos.filter(todo => todo.status === 'completed').length;
  return (
    <Box flexDirection="column" borderStyle="round" borderColor="blue" paddingX={1} marginBottom={1}>
      <Text color="blue">Plan ({completed}/{todos.length})</Text>
      {todos.map((todo, index) => (
        <Text key={`${todo.content}-${index}`}>
          {marker(todo.status)} {todo.content}
          {todo.status === 'in_progress' && todo.activeForm ? ` (${todo.activeForm})` : ''}
        </Text>
      ))}
    </Box>
  );
}

function marker(status: TodoItemPayload['status']): string {
  if (status === 'completed') return '[x]';
  if (status === 'in_progress') return '[>]';
  return '[ ]';
}

