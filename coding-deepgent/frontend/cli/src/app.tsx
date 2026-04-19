import React, { useEffect, useReducer } from 'react';
import { Box, Text, useApp } from 'ink';
import type { BridgeClient } from './bridge/python-process.js';
import { initialUiState, reduceFrontendEvent } from './bridge/reducer.js';
import type { FrontendInput } from './bridge/protocol.js';
import { MessageList } from './components/message-list.js';
import { ContextPanel } from './components/context-panel.js';
import { PermissionPanel } from './components/permission-panel.js';
import { PromptInput } from './components/prompt-input.js';
import { SessionPanel } from './components/session-panel.js';
import { SpinnerLine } from './components/spinner.js';
import { StatusFooter } from './components/status-footer.js';
import { SubagentPanel } from './components/subagent-panel.js';
import { TaskPanel } from './components/task-panel.js';
import { TodoPanel } from './components/todo-panel.js';

export function App({ bridge }: { bridge: BridgeClient }): React.ReactNode {
  const [state, dispatch] = useReducer(reduceFrontendEvent, initialUiState);
  const ink = useApp();

  useEffect(() => {
    const unsubscribe = bridge.onEvent(event => dispatch(event));
    bridge.start();
    return () => {
      unsubscribe();
      bridge.stop();
    };
  }, [bridge]);

  const send = (input: FrontendInput) => bridge.send(input);
  const exit = () => {
    dispatch({ type: 'ui_interrupted' });
    bridge.stop();
    ink.exit();
  };
  const submit = (text: string) => {
    if (text === '/help') {
      dispatch({ type: 'ui_help' });
      return;
    }
    if (text === '/clear') {
      dispatch({ type: 'ui_clear' });
      return;
    }
    send({ type: 'submit_prompt', text });
  };

  return (
    <Box flexDirection="column" paddingX={1}>
      <Text color="cyan">coding-deepgent</Text>
      <SessionPanel recoveryBrief={state.recoveryBrief} />
      <ContextPanel snapshot={state.contextSnapshot} />
      <TodoPanel todos={state.todos} />
      <TaskPanel tasks={state.tasks} />
      <SubagentPanel snapshot={state.subagentSnapshot} />
      <PermissionPanel permissions={state.pendingPermissions} send={send} />
      <MessageList messages={state.messages} />
      <SpinnerLine active={state.isRunning} />
      <PromptInput
        disabled={state.isRunning || state.pendingPermissions.length > 0}
        onSubmit={submit}
        onExit={exit}
      />
      <StatusFooter state={state} />
    </Box>
  );
}
