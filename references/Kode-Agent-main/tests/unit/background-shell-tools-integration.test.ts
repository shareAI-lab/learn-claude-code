import { describe, expect, test } from 'bun:test'
import { __ToolUseQueueForTests } from '@query'
import { createAssistantMessage } from '@utils/messages'
import { BunShell } from '@utils/bun/shell'
import { BashTool } from '@tools/BashTool/BashTool'
import { TaskOutputTool } from '@tools/TaskOutputTool/TaskOutputTool'
import { KillShellTool } from '@tools/KillShellTool/KillShellTool'

function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms))
}

function makeToolUse(id: string, name: string, input: any) {
  return { id, name, input, type: 'tool_use' } as any
}

describe('Background shell tools integration (no sibling tool errors)', () => {
  test('TaskOutput + KillShell succeed with valid task_id under scheduler', async () => {
    if (process.platform === 'win32') return

    BunShell.restart()
    const shell = BunShell.getInstance()

    const { bashId } = shell.execInBackground(
      'i=1; while [ $i -le 5 ]; do echo "tick $i"; i=$((i+1)); sleep 0.1; done; sleep 10',
      10_000,
    )
    await sleep(150)

    const toolUseContext: any = {
      abortController: new AbortController(),
      readFileTimestamps: {},
      setToolJSX: () => {},
      options: {
        tools: [BashTool, TaskOutputTool, KillShellTool],
        commands: [],
        forkNumber: 0,
        messageLogName: 'background-shell-tools-test',
        verbose: false,
        safeMode: false,
        maxThinkingTokens: 0,
        bashLlmGateQuery: async () => {
          return 'ALLOW'
        },
      },
    }

    const queue: any = new __ToolUseQueueForTests({
      toolDefinitions: [BashTool, TaskOutputTool, KillShellTool],
      canUseTool: async () => ({ result: true }),
      toolUseContext,
      siblingToolUseIDs: new Set(['sleep', 'out', 'kill']),
    })

    const assistantMessage = createAssistantMessage('tools')

    queue.addTool(
      makeToolUse('sleep', 'Bash', {
        command: 'sleep 0.3',
        description: 'Wait briefly',
      }),
      assistantMessage,
    )
    queue.addTool(
      makeToolUse('out', 'TaskOutput', { task_id: bashId, block: false }),
      assistantMessage,
    )
    queue.addTool(
      makeToolUse('kill', 'KillShell', { shell_id: bashId }),
      assistantMessage,
    )

    const out: any[] = []
    for await (const msg of queue.getRemainingResults()) out.push(msg)

    const toolResults = out
      .filter(m => m.type === 'user')
      .flatMap(m =>
        Array.isArray(m.message.content)
          ? m.message.content.filter((b: any) => b.type === 'tool_result')
          : [],
      )

    const sleepResult = toolResults.find((b: any) => b.tool_use_id === 'sleep')
    const outResult = toolResults.find((b: any) => b.tool_use_id === 'out')
    const killResult = toolResults.find((b: any) => b.tool_use_id === 'kill')

    expect(sleepResult?.is_error).not.toBe(true)
    expect(outResult?.is_error).not.toBe(true)
    expect(killResult?.is_error).not.toBe(true)

    const contents = toolResults.map((b: any) => String(b.content ?? ''))
    expect(contents.some(c => c.includes('No shell found with ID'))).toBe(false)
    expect(contents.some(c => c.includes('Sibling tool call errored'))).toBe(
      false,
    )
  })
})
