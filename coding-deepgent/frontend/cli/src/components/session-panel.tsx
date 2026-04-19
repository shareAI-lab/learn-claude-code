import React from 'react';
import { Box, Text } from 'ink';

export function SessionPanel({ recoveryBrief }: { recoveryBrief: string | undefined }): React.ReactNode {
  if (!recoveryBrief) {
    return null;
  }
  const firstLines = recoveryBrief.split('\n').slice(0, 6).join('\n');
  return (
    <Box flexDirection="column" borderStyle="single" borderColor="gray" paddingX={1} marginBottom={1}>
      <Text color="gray">Recovery brief</Text>
      <Text>{firstLines}</Text>
    </Box>
  );
}
