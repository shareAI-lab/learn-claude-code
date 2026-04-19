import React from 'react';
import { Text } from 'ink';

export function SpinnerLine({ active }: { active: boolean }): React.ReactNode {
  return active ? <Text color="yellow">Running agent...</Text> : null;
}

