import React from 'react';
import { Box, Text } from 'ink';
import type { UiMessage } from '../bridge/reducer.js';

export function MessageRow({ message }: { message: UiMessage }): React.ReactNode {
  const color = colorFor(message.kind);
  const marker = markerFor(message.kind);
  return (
    <Box flexDirection="column" marginBottom={1}>
      <Box>
        <Text color={color}>{marker} {message.title || message.kind}</Text>
        {message.streaming ? <Text color="yellow"> running</Text> : null}
      </Box>
      <Box paddingLeft={2}>
        <Text>{message.text || '(empty)'}</Text>
      </Box>
    </Box>
  );
}

function colorFor(kind: UiMessage['kind']): string {
  if (kind === 'user') return 'cyan';
  if (kind === 'assistant') return 'green';
  if (kind === 'tool') return 'magenta';
  if (kind === 'error') return 'red';
  return 'gray';
}

function markerFor(kind: UiMessage['kind']): string {
  if (kind === 'user') return '>';
  if (kind === 'assistant') return '<';
  if (kind === 'tool') return '*';
  if (kind === 'error') return '!';
  return '-';
}

