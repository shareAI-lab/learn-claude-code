import React from 'react';
import { Box, Text } from 'ink';
import type { UiMessage } from '../bridge/reducer.js';
import { MessageRow } from './message-row.js';

const MAX_VISIBLE_MESSAGES = 12;

export function MessageList({ messages }: { messages: UiMessage[] }): React.ReactNode {
  const visible = messages.slice(-MAX_VISIBLE_MESSAGES);
  if (visible.length === 0) {
    return (
      <Box marginY={1}>
        <Text color="gray">No messages yet. Type a prompt to start.</Text>
      </Box>
    );
  }
  return (
    <Box flexDirection="column" marginTop={1}>
      {visible.map(message => (
        <MessageRow key={message.id} message={message} />
      ))}
    </Box>
  );
}

