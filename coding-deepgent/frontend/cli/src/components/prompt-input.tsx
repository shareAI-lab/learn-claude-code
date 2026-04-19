import React, { useState } from 'react';
import { Box, Text, useInput } from 'ink';

export function PromptInput({
  disabled,
  onSubmit,
  onExit
}: {
  disabled: boolean;
  onSubmit: (value: string) => void;
  onExit: () => void;
}): React.ReactNode {
  const [value, setValue] = useState('');

  useInput((input, key) => {
    if (key.ctrl && input === 'c') {
      onExit();
      return;
    }
    if (disabled) {
      return;
    }
    const newlineIndex = input.search(/[\r\n]/);
    if (key.return || newlineIndex !== -1) {
      const submittedValue =
        newlineIndex === -1 ? value : value + input.slice(0, newlineIndex);
      const trimmed = submittedValue.trim();
      if (trimmed === '/exit') {
        onExit();
        return;
      }
      if (trimmed) {
        onSubmit(trimmed);
        setValue('');
      }
      return;
    }
    if (key.backspace || key.delete) {
      setValue(current => current.slice(0, -1));
      return;
    }
    if (input && !key.ctrl && !key.meta) {
      setValue(current => current + input);
    }
  });

  return (
    <Box borderStyle="single" borderColor={disabled ? 'gray' : 'cyan'} paddingX={1}>
      <Text color="cyan">prompt </Text>
      <Text>{value}</Text>
      {!disabled ? <Text color="cyan">_</Text> : <Text color="gray"> waiting...</Text>}
    </Box>
  );
}
