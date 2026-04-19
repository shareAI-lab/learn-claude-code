import { describe, expect, test } from 'bun:test'
import type { Command } from '@commands'
import { processUserInput } from '@utils/messages'
import { __getCompletionContextForTests } from '@hooks/useUnifiedCompletion'

describe('--disable-slash-commands (Reference CLI parity)', () => {
  test('processUserInput treats /cmd as command only when enabled', async () => {
    const helpCommand = {
      type: 'local',
      name: 'help',
      description: 'help',
      isEnabled: true,
      isHidden: false,
      userFacingName() {
        return 'help'
      },
      async call() {
        return 'OK'
      },
    } satisfies Command

    const baseContext = {
      options: {
        commands: [helpCommand],
        tools: [],
        verbose: false,
        permissionMode: 'default',
        disableSlashCommands: false,
      },
      messageId: undefined,
      abortController: new AbortController(),
      readFileTimestamps: {},
      setForkConvoWithMessagesOnTheNextRender() {},
    } as any

    const enabled = await processUserInput(
      '/help',
      'prompt',
      () => {},
      baseContext,
      null,
    )
    expect(enabled.length).toBe(2)
    expect(enabled[0]?.type).toBe('user')
    expect((enabled[0] as any).message.content).toContain(
      '<command-name>help</command-name>',
    )
    expect(enabled[1]?.type).toBe('assistant')
    expect((enabled[1] as any).message.content[0]?.text).toContain(
      '<local-command-stdout>OK</local-command-stdout>',
    )

    const disabled = await processUserInput(
      '/help',
      'prompt',
      () => {},
      {
        ...baseContext,
        options: { ...baseContext.options, disableSlashCommands: true },
      },
      null,
    )
    expect(disabled.length).toBe(1)
    expect(disabled[0]?.type).toBe('user')
    expect((disabled[0] as any).message.content).toBe('/help')
  })

  test('unified completion does not classify /foo as command when disabled', () => {
    const enabled = __getCompletionContextForTests({
      input: '/he',
      cursorOffset: 3,
      disableSlashCommands: false,
    })
    expect(enabled?.type).toBe('command')
    expect(enabled?.prefix).toBe('he')

    const disabled = __getCompletionContextForTests({
      input: '/he',
      cursorOffset: 3,
      disableSlashCommands: true,
    })
    expect(disabled?.type).toBe('file')
    expect(disabled?.prefix).toBe('/he')
  })
})
