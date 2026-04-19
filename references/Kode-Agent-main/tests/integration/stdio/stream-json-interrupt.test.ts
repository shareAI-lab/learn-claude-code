import { describe, expect, test } from 'bun:test'
import { createInterface } from 'node:readline'
import { PassThrough } from 'node:stream'
import { KodeAgentStructuredStdio } from '@utils/protocol/kodeAgentStructuredStdio'
import { runKodeAgentStreamJsonSession } from '@utils/protocol/kodeAgentStreamJsonSession'
import { createAssistantMessage } from '@utils/messages'

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

describe('stream-json session interrupt (integration)', () => {
  test('interrupt aborts active turn and emits an error result, then continues next turn', async () => {
    const stdin = new PassThrough()
    const stdout = new PassThrough()
    const rlOut = createInterface({ input: stdout })
    const nextLine = makeLineReader(rlOut)

    let activeTurnAbortController: AbortController | null = null

    const structured = new KodeAgentStructuredStdio(stdin, stdout, {
      onInterrupt: () => {
        activeTurnAbortController?.abort()
      },
    })
    structured.start()

    let queryCalls = 0
    const query = (async function* (_messages: any, _sp: any, _ctx: any, _cu: any, toolUseContext: any) {
      queryCalls += 1
      if (queryCalls === 1) {
        await new Promise<void>(resolve => {
          if (toolUseContext.abortController.signal.aborted) return resolve()
          toolUseContext.abortController.signal.addEventListener('abort', () => resolve(), {
            once: true,
          })
        })
        return
      }
      yield createAssistantMessage(`turn:${queryCalls}`) as any
    }) as any

    const sessionPromise = runKodeAgentStreamJsonSession({
      structured,
      query,
      writeSdkLine: obj => {
        stdout.write(JSON.stringify(obj) + '\n')
      },
      sessionId: 'sess_test',
      systemPrompt: [],
      context: {},
      canUseTool: (async () => ({ result: true })) as any,
      toolUseContextBase: {
        options: {} as any,
        messageId: undefined,
        readFileTimestamps: {},
        setToolJSX: () => {},
      } as any,
      replayUserMessages: true,
      getTotalCostUsd: () => 0,
      onActiveTurnAbortControllerChanged: controller => {
        activeTurnAbortController = controller
      },
    })

    stdin.write(
      JSON.stringify({
        type: 'user',
        uuid: 'u1',
        message: { role: 'user', content: 'hi' },
      }) + '\n',
    )

    const user1 = JSON.parse(await nextLine())
    expect(user1.type).toBe('user')
    expect(user1.uuid).toBe('u1')

    stdin.write(
      JSON.stringify({
        type: 'control_request',
        request_id: 'req_interrupt',
        request: { subtype: 'interrupt' },
      }) + '\n',
    )

    const controlAck = JSON.parse(await nextLine())
    expect(controlAck.type).toBe('control_response')
    expect(controlAck.response?.subtype).toBe('success')
    expect(controlAck.response?.request_id).toBe('req_interrupt')

    const result1 = JSON.parse(await nextLine())
    expect(result1.type).toBe('result')
    expect(result1.is_error).toBe(true)

    stdin.write(
      JSON.stringify({
        type: 'user',
        uuid: 'u2',
        message: { role: 'user', content: 'yo' },
      }) + '\n',
    )

    const user2 = JSON.parse(await nextLine())
    expect(user2.type).toBe('user')
    expect(user2.uuid).toBe('u2')

    const assistant2 = JSON.parse(await nextLine())
    expect(assistant2.type).toBe('assistant')

    const result2 = JSON.parse(await nextLine())
    expect(result2.type).toBe('result')
    expect(result2.is_error).toBe(false)

    stdin.end()
    await sessionPromise
    expect(queryCalls).toBe(2)

    rlOut.close()
    stdout.end()
  })
})

