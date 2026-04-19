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

describe('stream-json persistent session', () => {
  test('replay-user-messages echoes user lines and suppresses duplicate uuid execution', async () => {
    const stdin = new PassThrough()
    const stdout = new PassThrough()
    const rlOut = createInterface({ input: stdout })
    const nextLine = makeLineReader(rlOut)

    const structured = new KodeAgentStructuredStdio(stdin, stdout)
    structured.start()

    let queryCalls = 0
    const query = async function* () {
      queryCalls += 1
      yield createAssistantMessage(`turn:${queryCalls}`) as any
    } as any

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

    const assistant1 = JSON.parse(await nextLine())
    expect(assistant1.type).toBe('assistant')

    const result1 = JSON.parse(await nextLine())
    expect(result1.type).toBe('result')
    expect(result1.is_error).toBe(false)

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

    stdin.write(
      JSON.stringify({
        type: 'user',
        uuid: 'u1',
        message: { role: 'user', content: 'hi' },
      }) + '\n',
    )

    const dup = JSON.parse(await nextLine())
    expect(dup.type).toBe('user')
    expect(dup.uuid).toBe('u1')

    stdin.end()
    await sessionPromise
    expect(queryCalls).toBe(2)

    rlOut.close()
    stdout.end()
  })

  test('without replay-user-messages, user lines are not emitted', async () => {
    const stdin = new PassThrough()
    const stdout = new PassThrough()
    const rlOut = createInterface({ input: stdout })
    const nextLine = makeLineReader(rlOut)

    const structured = new KodeAgentStructuredStdio(stdin, stdout)
    structured.start()

    let queryCalls = 0
    const query = async function* () {
      queryCalls += 1
      yield createAssistantMessage(`turn:${queryCalls}`) as any
    } as any

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
      replayUserMessages: false,
      getTotalCostUsd: () => 0,
    })

    stdin.write(
      JSON.stringify({
        type: 'user',
        uuid: 'u1',
        message: { role: 'user', content: 'hi' },
      }) + '\n',
    )

    const assistant1 = JSON.parse(await nextLine())
    expect(assistant1.type).toBe('assistant')

    const result1 = JSON.parse(await nextLine())
    expect(result1.type).toBe('result')
    expect(result1.is_error).toBe(false)

    stdin.end()
    await sessionPromise
    expect(queryCalls).toBe(1)

    rlOut.close()
    stdout.end()
  })
})
