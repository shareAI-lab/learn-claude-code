import readline from 'node:readline'

import { JsonRpcPeer } from './jsonrpc'

type TransportOptions = {
  writeLine: (line: string) => void
}

export class StdioTransport {
  private rl: readline.Interface | null = null
  private readonly pending = new Set<Promise<void>>()

  constructor(
    private readonly peer: JsonRpcPeer,
    private readonly opts: TransportOptions,
  ) {}

  start(): void {
    if (this.rl) return

    this.peer.setSend(this.opts.writeLine)

    this.rl = readline.createInterface({
      input: process.stdin,
      crlfDelay: Infinity,
    })

    this.rl.on('line', line => {
      const trimmed = line.trim()
      if (!trimmed) return

      try {
        const payload = JSON.parse(trimmed)
        const p = this.peer.handleIncoming(payload).catch(() => {
        })
        this.pending.add(p)
        void p.finally(() => this.pending.delete(p))
      } catch (err) {
        this.opts.writeLine(
          JSON.stringify({
            jsonrpc: '2.0',
            id: null,
            error: { code: -32700, message: 'Parse error' },
          }),
        )
      }
    })

    this.rl.on('close', () => {
      void (async () => {
        const pending = Array.from(this.pending)
        if (pending.length > 0) {
          await Promise.allSettled(pending)
        }
        process.exit(0)
      })()
    })
  }

  stop(): void {
    this.rl?.close()
    this.rl = null
  }
}
