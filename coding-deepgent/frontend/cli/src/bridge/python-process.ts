import { spawn, type ChildProcessWithoutNullStreams } from 'node:child_process';
import readline from 'node:readline';
import { encodeFrontendInput, parseFrontendEvent, type FrontendEvent, type FrontendInput } from './protocol.js';

export type BridgeClient = {
  start(): void;
  send(input: FrontendInput): void;
  stop(): void;
  onEvent(listener: (event: FrontendEvent) => void): () => void;
};

export type PythonBridgeOptions = {
  fake?: boolean;
};

export class PythonProcessBridge implements BridgeClient {
  private child: ChildProcessWithoutNullStreams | undefined;
  private readonly listeners = new Set<(event: FrontendEvent) => void>();
  private stopped = false;

  constructor(private readonly options: PythonBridgeOptions = {}) {}

  start(): void {
    if (this.child) {
      return;
    }
    const command = resolveBridgeCommand(this.options.fake);
    this.child = spawn(command.command, command.args, {
      cwd: process.env.CODING_DEEPGENT_UI_WORKDIR || process.cwd(),
      env: {
        ...process.env,
        PYTHONPATH: process.env.PYTHONPATH || 'src'
      },
      shell: command.shell,
      stdio: 'pipe'
    });

    const lines = readline.createInterface({ input: this.child.stdout });
    lines.on('line', line => {
      try {
        this.emit(parseFrontendEvent(line));
      } catch (error) {
        this.emit({
          type: 'protocol_error',
          error: error instanceof Error ? error.message : String(error)
        });
      }
    });

    this.child.stderr.on('data', chunk => {
      const text = String(chunk).trim();
      if (text) {
        this.emit({ type: 'runtime_event', kind: 'stderr', message: text });
      }
    });

    this.child.on('error', error => {
      this.emit({ type: 'run_failed', session_id: 'unknown', error: error.message });
    });

    this.child.on('close', code => {
      if (!this.stopped && code !== 0) {
        this.emit({
          type: 'run_failed',
          session_id: 'unknown',
          error: `Python bridge exited with code ${code ?? 'unknown'}`
        });
      }
    });
  }

  send(input: FrontendInput): void {
    if (!this.child) {
      this.start();
    }
    this.child?.stdin.write(encodeFrontendInput(input));
  }

  stop(): void {
    if (this.stopped) {
      return;
    }
    this.stopped = true;
    if (
      this.child &&
      !this.child.killed &&
      !this.child.stdin.destroyed &&
      !this.child.stdin.writableEnded
    ) {
      this.child.stdin.write(encodeFrontendInput({ type: 'exit' }));
      this.child.stdin.end();
    }
  }

  onEvent(listener: (event: FrontendEvent) => void): () => void {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  }

  private emit(event: FrontendEvent): void {
    for (const listener of this.listeners) {
      listener(event);
    }
  }
}

function resolveBridgeCommand(fake = false): { command: string; args: string[]; shell?: boolean } {
  const configured = process.env.CODING_DEEPGENT_UI_BRIDGE_COMMAND;
  if (configured) {
    return { command: configured, args: [], shell: true };
  }
  return {
    command: 'python3',
    args: ['-m', 'coding_deepgent', 'ui-bridge', ...(fake || process.env.CODING_DEEPGENT_UI_FAKE === '1' ? ['--fake'] : [])]
  };
}
