#!/usr/bin/env node
import React from 'react';
import { render } from 'ink';
import { App } from './app.js';
import { PythonProcessBridge } from './bridge/python-process.js';

if (!process.stdin.isTTY) {
  console.error(
    'coding-deepgent-ui requires an interactive TTY. Use `python3 -m coding_deepgent ui-bridge` for JSONL automation.'
  );
  process.exit(2);
}

const fake = process.argv.includes('--fake') || process.env.CODING_DEEPGENT_UI_FAKE === '1';
const bridge = new PythonProcessBridge({ fake });

render(<App bridge={bridge} />);
