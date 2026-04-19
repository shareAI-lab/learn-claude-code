import { createInterface } from 'node:readline'
import { AbortError } from '@utils/text/errors'

type ControlRequestMessage = {
  type: 'control_request'
  request_id: string
  request: { subtype: string; [key: string]: unknown }
}

type KeepAliveMessage = { type: 'keep_alive' }

type ControlResponseMessage = {
  type: 'control_response'
  response: {
    request_id: string
    subtype: 'success' | 'error'
    response?: unknown
    error?: string
  }
}

type ControlCancelRequestMessage = {
  type: 'control_cancel_request'
  request_id: string
}

type UserInputMessage = {
  type: 'user'
  uuid?: string
  parent_tool_use_id?: string | null
  message: { role: 'user'; content: unknown }
}

type StructuredInputMessage =
  | ControlRequestMessage
  | ControlResponseMessage
  | ControlCancelRequestMessage
  | UserInputMessage
  | KeepAliveMessage
  | { type: string; [key: string]: unknown }

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}

function tryParseLine(line: string): StructuredInputMessage | null {
  if (!line.trim()) return null
  try {
    const parsed = JSON.parse(line) as unknown
    if (!isRecord(parsed)) return null
    if (typeof parsed.type !== 'string') return null
    return parsed as StructuredInputMessage
  } catch {
    return null
  }
}

function makeRequestId(): string {
  return Math.random().toString(36).slice(2, 15)
}

export class KodeAgentStructuredStdio {
  private started = false
  private inputClosed = false
  private pendingRequests = new Map<
    string,
    {
      resolve: (msg: ControlResponseMessage['response']) => void
      reject: (err: Error) => void
      cleanup: () => void
    }
  >()
  private queuedUserMessages: UserInputMessage[] = []
  private awaitingUserWaiters: Array<{
    resolve: (msg: UserInputMessage) => void
    reject: (err: Error) => void
  }> = []

  constructor(
    private input: NodeJS.ReadableStream,
    private output: NodeJS.WritableStream,
    private opts: {
      onInterrupt?: () => void
      onControlRequest?: (msg: ControlRequestMessage) => Promise<unknown | void>
    } = {},
  ) {}

  start(): void {
    if (this.started) return
    this.started = true

    const rl = createInterface({ input: this.input })
    ;(async () => {
      for await (const line of rl) {
        this.handleLine(String(line))
      }
    })()
      .catch(() => {})
      .finally(() => {
        this.inputClosed = true
        rl.close()
        this.rejectAllPending(new Error('Stream closed'))
        this.rejectAllUserWaiters(new Error('Stream closed'))
      })
  }

  private rejectAllPending(err: Error): void {
    for (const pending of this.pendingRequests.values()) {
      pending.cleanup()
      pending.reject(err)
    }
    this.pendingRequests.clear()
  }

  private rejectAllUserWaiters(err: Error): void {
    for (const waiter of this.awaitingUserWaiters.splice(0)) {
      waiter.reject(err)
    }
  }

  private write(obj: unknown): void {
    this.output.write(JSON.stringify(obj) + '\n')
  }

  private sendControlResponseSuccess(
    requestId: string,
    response?: unknown,
  ): void {
    this.write({
      type: 'control_response',
      response: {
        subtype: 'success',
        request_id: requestId,
        ...(response !== undefined ? { response } : {}),
      },
    })
  }

  private sendControlResponseError(requestId: string, error: string): void {
    this.write({
      type: 'control_response',
      response: {
        subtype: 'error',
        request_id: requestId,
        error,
      },
    })
  }

  private sendControlCancelRequest(requestId: string): void {
    this.write({
      type: 'control_cancel_request',
      request_id: requestId,
    })
  }

  private handleLine(line: string): void {
    const msg = tryParseLine(line)
    if (!msg) return

    if (msg.type === 'keep_alive') {
      return
    }

    if (msg.type === 'user') {
      const userMsg = msg as UserInputMessage
      const waiter = this.awaitingUserWaiters.shift()
      if (waiter) waiter.resolve(userMsg)
      else this.queuedUserMessages.push(userMsg)
      return
    }

    if (msg.type === 'control_response') {
      const responseMsg = msg as ControlResponseMessage
      const requestId = responseMsg.response?.request_id
      if (typeof requestId !== 'string' || !requestId) return
      const pending = this.pendingRequests.get(requestId)
      if (!pending) return
      pending.cleanup()
      this.pendingRequests.delete(requestId)
      pending.resolve(responseMsg.response)
      return
    }

    if (msg.type === 'control_request') {
      const requestMsg = msg as ControlRequestMessage
      const requestId = requestMsg.request_id
      const subtype = requestMsg.request?.subtype
      if (typeof requestId !== 'string' || !requestId) return
      if (typeof subtype !== 'string' || !subtype) {
        this.sendControlResponseError(
          requestId,
          'Invalid control request (missing subtype)',
        )
        return
      }

      if (subtype === 'interrupt') {
        this.opts.onInterrupt?.()
        this.sendControlResponseSuccess(requestId)
        return
      }

      const handler = this.opts.onControlRequest
      if (handler) {
        Promise.resolve()
          .then(async () => await handler(requestMsg))
          .then(response =>
            this.sendControlResponseSuccess(requestId, response),
          )
          .catch(err =>
            this.sendControlResponseError(
              requestId,
              err instanceof Error ? err.message : String(err),
            ),
          )
        return
      }

      this.sendControlResponseError(
        requestId,
        `Unsupported control request subtype: ${subtype}`,
      )
    }
  }

  async nextUserMessage(args?: {
    signal?: AbortSignal
    timeoutMs?: number
  }): Promise<UserInputMessage> {
    if (this.queuedUserMessages.length > 0) {
      return this.queuedUserMessages.shift()!
    }
    if (this.inputClosed) {
      throw new Error('Stream closed')
    }

    const timeoutMs =
      typeof args?.timeoutMs === 'number' && Number.isFinite(args.timeoutMs)
        ? Math.max(0, args.timeoutMs)
        : null

    return await new Promise<UserInputMessage>((resolve, reject) => {
      let settled = false
      let waiter: {
        resolve: (msg: UserInputMessage) => void
        reject: (err: Error) => void
      } | null = null
      const onAbort = () => {
        cleanup()
        reject(new AbortError('User input aborted.'))
      }

      const onTimeout = () => {
        cleanup()
        reject(new Error('Timed out waiting for user input.'))
      }

      const cleanup = () => {
        if (settled) return
        settled = true
        if (args?.signal) args.signal.removeEventListener('abort', onAbort)
        if (timeoutId) clearTimeout(timeoutId)
        if (waiter) {
          const idx = this.awaitingUserWaiters.indexOf(waiter)
          if (idx >= 0) this.awaitingUserWaiters.splice(idx, 1)
        }
      }

      let timeoutId: NodeJS.Timeout | null = null
      if (timeoutMs !== null) timeoutId = setTimeout(onTimeout, timeoutMs)
      if (args?.signal)
        args.signal.addEventListener('abort', onAbort, { once: true })

      waiter = {
        resolve: msg => {
          cleanup()
          resolve(msg)
        },
        reject: err => {
          cleanup()
          reject(err)
        },
      }

      this.awaitingUserWaiters.push(waiter)
    })
  }

  async sendRequest<TResponse = unknown>(
    request: Record<string, unknown>,
    args?: { signal?: AbortSignal; timeoutMs?: number },
  ): Promise<TResponse> {
    if (this.inputClosed) {
      throw new Error('Stream closed')
    }
    if (args?.signal?.aborted) {
      throw new AbortError('Request aborted.')
    }

    const requestId = makeRequestId()
    this.write({ type: 'control_request', request_id: requestId, request })

    const timeoutMs =
      typeof args?.timeoutMs === 'number' && Number.isFinite(args.timeoutMs)
        ? Math.max(0, args.timeoutMs)
        : null

    return await new Promise<TResponse>((resolve, reject) => {
      const onAbort = () => {
        this.sendControlCancelRequest(requestId)
        this.pendingRequests.delete(requestId)
        cleanup()
        reject(new AbortError('Request aborted.'))
      }

      const onTimeout = () => {
        this.sendControlCancelRequest(requestId)
        this.pendingRequests.delete(requestId)
        cleanup()
        reject(new Error('Timed out waiting for control response.'))
      }

      const cleanup = () => {
        if (args?.signal) args.signal.removeEventListener('abort', onAbort)
        if (timeoutId) clearTimeout(timeoutId)
      }

      let timeoutId: NodeJS.Timeout | null = null
      if (timeoutMs !== null) timeoutId = setTimeout(onTimeout, timeoutMs)
      if (args?.signal)
        args.signal.addEventListener('abort', onAbort, { once: true })

      this.pendingRequests.set(requestId, {
        cleanup,
        resolve: response => {
          if (response.subtype === 'error') {
            reject(
              new Error(response.error || 'Unknown control response error'),
            )
            return
          }
          resolve((response.response ?? null) as TResponse)
        },
        reject,
      })
    })
  }
}
