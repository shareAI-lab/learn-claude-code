import { describe, expect, test } from 'bun:test'
import { PassThrough } from 'node:stream'
import { createInterface } from 'node:readline'
import { KodeAgentStructuredStdio } from '@utils/protocol/kodeAgentStructuredStdio'

function makeLineReader(
  rl: ReturnType<typeof createInterface>,
): () => Promise<string> {
  const queue: string[] = []
  let resolveNext: ((line: string) => void) | null = null

  rl.on('line', line => {
    if (resolveNext) {
      const resolve = resolveNext
      resolveNext = null
      resolve(line)
      return
    }
    queue.push(line)
  })

  return async () => {
    if (queue.length > 0) return queue.shift()!
    return await new Promise<string>(resolve => {
      resolveNext = resolve
    })
  }
}

describe('structured stdin/stdout (stdio)', () => {
  test('sendRequest emits control_request and resolves on control_response', async () => {
    const stdin = new PassThrough()
    const stdout = new PassThrough()
    const rlOut = createInterface({ input: stdout })
    const nextLine = makeLineReader(rlOut)

    const channel = new KodeAgentStructuredStdio(stdin, stdout)
    channel.start()

    const pending = channel.sendRequest<{
      behavior: string
      updatedInput?: any
    }>({
      subtype: 'can_use_tool',
      tool_name: 'Bash',
      input: { command: 'ls' },
    })

    const requestLine = await nextLine()
    const request = JSON.parse(requestLine)
    expect(request.type).toBe('control_request')
    expect(request.request.subtype).toBe('can_use_tool')
    expect(typeof request.request_id).toBe('string')

    stdin.write(
      JSON.stringify({
        type: 'control_response',
        response: {
          subtype: 'success',
          request_id: request.request_id,
          response: { behavior: 'allow', updatedInput: { command: 'ls -la' } },
        },
      }) + '\n',
    )

    const resp = await pending
    expect(resp.behavior).toBe('allow')
    rlOut.close()
    stdin.end()
    stdout.end()
  })

  test('interrupt control_request triggers callback and acks with control_response', async () => {
    const stdin = new PassThrough()
    const stdout = new PassThrough()
    const rlOut = createInterface({ input: stdout })
    const nextLine = makeLineReader(rlOut)

    let interrupted = 0
    const channel = new KodeAgentStructuredStdio(stdin, stdout, {
      onInterrupt: () => {
        interrupted += 1
      },
    })
    channel.start()

    stdin.write(
      JSON.stringify({
        type: 'control_request',
        request_id: 'req_interrupt',
        request: { subtype: 'interrupt' },
      }) + '\n',
    )

    const line = await nextLine()
    const msg = JSON.parse(line)
    expect(interrupted).toBe(1)
    expect(msg.type).toBe('control_response')
    expect(msg.response.subtype).toBe('success')
    expect(msg.response.request_id).toBe('req_interrupt')
    rlOut.close()
    stdin.end()
    stdout.end()
  })

  test('non-interrupt control_request is handled by onControlRequest and can return a response payload', async () => {
    const stdin = new PassThrough()
    const stdout = new PassThrough()
    const rlOut = createInterface({ input: stdout })
    const nextLine = makeLineReader(rlOut)

    const channel = new KodeAgentStructuredStdio(stdin, stdout, {
      onControlRequest: async msg => {
        if (msg.request.subtype !== 'set_model') {
          throw new Error(`Unexpected subtype: ${msg.request.subtype}`)
        }
        return { ok: true, model: msg.request.model }
      },
    })
    channel.start()

    stdin.write(JSON.stringify({ type: 'keep_alive' }) + '\n')

    stdin.write(
      JSON.stringify({
        type: 'control_request',
        request_id: 'req_set_model',
        request: { subtype: 'set_model', model: 'opus' },
      }) + '\n',
    )

    const line = await nextLine()
    const msg = JSON.parse(line)
    expect(msg.type).toBe('control_response')
    expect(msg.response.subtype).toBe('success')
    expect(msg.response.request_id).toBe('req_set_model')
    expect(msg.response.response).toEqual({ ok: true, model: 'opus' })

    rlOut.close()
    stdin.end()
    stdout.end()
  })

  test('aborting sendRequest emits control_cancel_request and rejects', async () => {
    const stdin = new PassThrough()
    const stdout = new PassThrough()
    const rlOut = createInterface({ input: stdout })
    const nextLine = makeLineReader(rlOut)

    const channel = new KodeAgentStructuredStdio(stdin, stdout)
    channel.start()

    const ac = new AbortController()
    const pending = channel.sendRequest(
      {
        subtype: 'can_use_tool',
        tool_name: 'Bash',
        input: { command: 'rm -rf /' },
      },
      { signal: ac.signal, timeoutMs: 10_000 },
    )

    const requestLine = await nextLine()
    const request = JSON.parse(requestLine)
    expect(request.type).toBe('control_request')
    expect(typeof request.request_id).toBe('string')

    ac.abort()

    const cancelLine = await nextLine()
    const cancel = JSON.parse(cancelLine)
    expect(cancel.type).toBe('control_cancel_request')
    expect(cancel.request_id).toBe(request.request_id)

    await expect(pending).rejects.toThrow()
    rlOut.close()
    stdin.end()
    stdout.end()
  })
})
