import { afterEach, describe, expect, test } from 'bun:test'
import React, { useMemo, useState } from 'react'
import { PassThrough } from 'stream'
import stripAnsi from 'strip-ansi'
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'fs'
import { tmpdir } from 'os'
import { join } from 'path'
import { Box, Text, render } from 'ink'
import PromptInput from '@components/PromptInput'
import { PermissionProvider } from '@context/PermissionContext'
import { AskUserQuestionPermissionRequest } from '@components/permissions/ask-user-question-permission-request/AskUserQuestionPermissionRequest'
import { AskUserQuestionTool } from '@tools/interaction/AskUserQuestionTool/AskUserQuestionTool'
import { BashToolRunInBackgroundOverlay } from '@tools/BashTool/BashToolRunInBackgroundOverlay'
import {
  createAssistantMessage,
  createProgressMessage,
  normalizeMessages,
  reorderMessages,
} from '@utils/messages'
import type { Message as KodeMessage } from '@query'
import { Message } from '@components/Message'
import { MessageResponse } from '@components/MessageResponse'
import { setCwd } from '@utils/state'

type InkTestHarness = {
  stdin: PassThrough & {
    isTTY?: boolean
    setRawMode?: (enabled: boolean) => void
    isRaw?: boolean
  }
  stdout: PassThrough & { isTTY?: boolean; columns?: number; rows?: number }
  unmount: () => void
  rerender: (element: React.ReactElement) => void
  clearOutput: () => void
  getOutput: () => string
  wait: (ms: number) => Promise<void>
}

class TestErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { error: string | null }
> {
  state: { error: string | null } = { error: null }

  static getDerivedStateFromError(error: unknown): { error: string } {
    return {
      error:
        error instanceof Error ? error.stack || error.message : String(error),
    }
  }

  render(): React.ReactNode {
    if (this.state.error) {
      return (
        <Box flexDirection="column">
          <Text>TestErrorBoundary</Text>
          <Text>{this.state.error}</Text>
        </Box>
      )
    }
    return (this as any).props.children
  }
}

function createInkTestHarness(element: React.ReactElement): InkTestHarness {
  const stdin = new PassThrough()
  ;(stdin as any).isTTY = true
  ;(stdin as any).isRaw = true
  ;(stdin as any).setRawMode = () => {}
  ;(stdin as any).ref = () => {}
  ;(stdin as any).unref = () => {}
  stdin.setEncoding('utf8')
  stdin.resume()

  const stdout = new PassThrough()
  ;(stdout as any).isTTY = true
  ;(stdout as any).columns = 100
  ;(stdout as any).rows = 30

  let rawOutput = ''
  stdout.on('data', chunk => {
    rawOutput += chunk.toString('utf8')
  })

  const instance = render(<TestErrorBoundary>{element}</TestErrorBoundary>, {
    stdin: stdin as any,
    stdout: stdout as any,
    exitOnCtrlC: false,
  })

  return {
    stdin,
    stdout,
    unmount: () => instance.unmount(),
    rerender: next => instance.rerender(next),
    clearOutput: () => {
      rawOutput = ''
    },
    getOutput: () => stripAnsi(rawOutput),
    wait: async ms => new Promise(resolve => setTimeout(resolve, ms)),
  }
}

const mounted: InkTestHarness[] = []

afterEach(async () => {
  while (mounted.length > 0) {
    try {
      mounted.pop()!.unmount()
    } catch {}
  }
})

function PromptInputHarness({
  conversationKey,
}: {
  conversationKey: string
}): React.ReactNode {
  const [input, setInput] = useState('')
  const [mode, setMode] = useState<'bash' | 'prompt' | 'koding'>('prompt')
  const [submitCount, setSubmitCount] = useState(0)
  const [abortController, setAbortController] =
    useState<AbortController | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  return (
    <PermissionProvider
      conversationKey={conversationKey}
      isBypassPermissionsModeAvailable={true}
    >
      <PromptInput
        commands={[]}
        forkNumber={0}
        messageLogName="tui"
        isDisabled={false}
        isLoading={isLoading}
        onQuery={async () => {}}
        debug={false}
        verbose={false}
        messages={[]}
        setToolJSX={() => {}}
        tools={[]}
        input={input}
        onInputChange={setInput}
        mode={mode}
        onModeChange={setMode}
        submitCount={submitCount}
        onSubmitCountChange={updater => setSubmitCount(prev => updater(prev))}
        setIsLoading={setIsLoading}
        setAbortController={setAbortController}
        onShowMessageSelector={() => {}}
        setForkConvoWithMessagesOnTheNextRender={() => {}}
        readFileTimestamps={{}}
        abortController={abortController}
      />
    </PermissionProvider>
  )
}

function PromptInputHarnessWithRaw({
  conversationKey,
}: {
  conversationKey: string
}): React.ReactNode {
  const [input, setInput] = useState('')
  const [mode, setMode] = useState<'bash' | 'prompt' | 'koding'>('prompt')
  const [submitCount, setSubmitCount] = useState(0)
  const [abortController, setAbortController] =
    useState<AbortController | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  return (
    <PermissionProvider
      conversationKey={conversationKey}
      isBypassPermissionsModeAvailable={true}
    >
      <Box flexDirection="column">
        <Text>RAW:{JSON.stringify(input)}</Text>
        <PromptInput
          commands={[]}
          forkNumber={0}
          messageLogName="tui"
          isDisabled={false}
          isLoading={isLoading}
          onQuery={async () => {}}
          debug={false}
          verbose={false}
          messages={[]}
          setToolJSX={() => {}}
          tools={[]}
          input={input}
          onInputChange={setInput}
          mode={mode}
          onModeChange={setMode}
          submitCount={submitCount}
          onSubmitCountChange={updater => setSubmitCount(prev => updater(prev))}
          setIsLoading={setIsLoading}
          setAbortController={setAbortController}
          onShowMessageSelector={() => {}}
          setForkConvoWithMessagesOnTheNextRender={() => {}}
          readFileTimestamps={{}}
          abortController={abortController}
        />
      </Box>
    </PermissionProvider>
  )
}

describe('TUI E2E regression (Ink render)', () => {
  test('Completion: Space inserts a space (does not accept suggestion)', async () => {
    await setCwd(process.cwd())

    const conversationKey = `tui:${Math.random().toString(16).slice(2)}`
    const h = createInkTestHarness(
      <PromptInputHarnessWithRaw conversationKey={conversationKey} />,
    )
    mounted.push(h)

    await h.wait(25)
    h.clearOutput()

    h.stdin.write('./d')
    await h.wait(75)
    expect(h.getOutput()).toContain('RAW:"./d"')

    h.clearOutput()
    h.stdin.write(' ')
    await h.wait(75)

    const out = h.getOutput()
    expect(out).toContain('RAW:"./d "')
    expect(out).not.toContain('RAW:"./dist/')
    expect(out).not.toContain('RAW:"loading...')
  })

  test('shift+tab cycles permission mode and renders CompactModeIndicator', async () => {
    const conversationKey = `tui:${Math.random().toString(16).slice(2)}`
    const h = createInkTestHarness(
      <PromptInputHarness conversationKey={conversationKey} />,
    )
    mounted.push(h)

    await h.wait(25)
    h.clearOutput()

    h.stdin.write('\u001B[Z')
    await h.wait(50)

    expect(h.getOutput()).toContain('accept edits on')
    expect(h.getOutput()).toContain('(shift+tab to cycle)')
  })

  test('AskUserQuestion: select Other, type, Enter submits answer', async () => {
    let allowed = false
    let done = false
    const input: any = {
      questions: [
        {
          question: 'What type of Snake game would you like?',
          header: 'Snake Game Requirements',
          multiSelect: false,
          options: [
            {
              label: 'HTML5 Canvas version (web browser)',
              description: 'Playable in browser',
            },
            {
              label: 'Terminal/Console version',
              description: 'Playable in terminal',
            },
          ],
        },
      ],
    }

    const toolUseConfirm: any = {
      assistantMessage: createAssistantMessage(''),
      tool: AskUserQuestionTool,
      description: 'Ask user question',
      input,
      commandPrefix: null,
      toolUseContext: {
        messageId: 'm',
        abortController: new AbortController(),
        readFileTimestamps: {},
      },
      riskScore: null,
      onAbort: () => {},
      onAllow: () => {
        allowed = true
      },
      onReject: () => {},
    }

    const h = createInkTestHarness(
      <AskUserQuestionPermissionRequest
        toolUseConfirm={toolUseConfirm}
        onDone={() => {
          done = true
        }}
        verbose={false}
      />,
    )
    mounted.push(h)

    await h.wait(25)

    h.stdin.write('\u001B[B')
    await h.wait(10)
    h.stdin.write('\u001B[B')
    await h.wait(10)

    for (const ch of 'threejs') {
      h.stdin.write(ch)
      await h.wait(5)
    }

    h.stdin.write('\r')
    await h.wait(25)

    expect(allowed).toBe(true)
    expect(done).toBe(true)
    expect(
      (toolUseConfirm.input as any).answers?.[
        'What type of Snake game would you like?'
      ],
    ).toBe('threejs')
  })

  test('Bash overlay: ctrl+b triggers background callback', async () => {
    let backgrounded = false
    const h = createInkTestHarness(
      <BashToolRunInBackgroundOverlay
        onBackground={() => {
          backgrounded = true
        }}
      />,
    )
    mounted.push(h)

    await h.wait(25)

    h.stdin.write('\x02')
    await h.wait(25)

    expect(backgrounded).toBe(true)
  })

  test('queued Waiting… progress is replaced by Running… for same tool_use_id', async () => {
    const toolUseId = 't2'
    const siblings = new Set<string>(['t1', toolUseId])

    const waiting = createProgressMessage(
      toolUseId,
      siblings,
      createAssistantMessage('<tool-progress>Waiting…</tool-progress>'),
      [],
      [],
    )

    const running = createProgressMessage(
      toolUseId,
      siblings,
      createAssistantMessage('<tool-progress>Running…</tool-progress>'),
      [],
      [],
    )

    function MessagesHarness({
      messages,
    }: {
      messages: KodeMessage[]
    }): React.ReactNode {
      const normalized = useMemo(() => normalizeMessages(messages), [messages])
      const ordered = useMemo(() => reorderMessages(normalized), [normalized])

      return (
        <Box flexDirection="column">
          {ordered.map(msg => {
            if (msg.type === 'progress') {
              return (
                <React.Fragment key={msg.uuid}>
                  <MessageResponse
                    children={
                      <Message
                        message={msg.content}
                        messages={msg.normalizedMessages}
                        addMargin={false}
                        tools={msg.tools}
                        verbose={false}
                        debug={false}
                        erroredToolUseIDs={new Set()}
                        inProgressToolUseIDs={new Set()}
                        unresolvedToolUseIDs={new Set()}
                        shouldAnimate={false}
                        shouldShowDot={false}
                      />
                    }
                  />
                </React.Fragment>
              )
            }

            return (
              <React.Fragment key={msg.uuid}>
                <Message
                  message={msg as any}
                  messages={normalized as any}
                  addMargin={true}
                  tools={[]}
                  verbose={false}
                  debug={false}
                  erroredToolUseIDs={new Set()}
                  inProgressToolUseIDs={new Set()}
                  unresolvedToolUseIDs={new Set()}
                  shouldAnimate={false}
                  shouldShowDot={false}
                />
              </React.Fragment>
            )
          })}
        </Box>
      )
    }

    function AutoUpdateMessagesHarness(): React.ReactNode {
      const [messages, setMessages] = useState<KodeMessage[]>([waiting])

      React.useEffect(() => {
        const handle = setTimeout(() => {
          setMessages([waiting, running])
        }, 60)
        return () => clearTimeout(handle)
      }, [])

      return <MessagesHarness messages={messages} />
    }

    const h = createInkTestHarness(<AutoUpdateMessagesHarness />)
    mounted.push(h)
    await h.wait(40)
    expect(h.getOutput()).toContain('Waiting…')

    h.clearOutput()
    await h.wait(90)

    expect(h.getOutput()).toContain('Running…')
    expect(h.getOutput()).not.toContain('Waiting…')
  })

  test('statusline renders when configured', async () => {
    const originalHome = process.env.HOME
    const originalUserProfile = process.env.USERPROFILE
    const originalEnabled = process.env.KODE_STATUSLINE_ENABLED
    const originalConfigDir = process.env.KODE_CONFIG_DIR

    const homeDir = mkdtempSync(join(tmpdir(), 'kode-statusline-home-'))
    process.env.HOME = homeDir
    process.env.USERPROFILE = homeDir
    process.env.KODE_STATUSLINE_ENABLED = '1'
    process.env.KODE_CONFIG_DIR = join(homeDir, '.kode')

    mkdirSync(join(homeDir, '.kode'), { recursive: true })
    const cmd = `${process.execPath} -e "process.stdout.write('hello-statusline')"`
    writeFileSync(
      join(homeDir, '.kode', 'settings.json'),
      JSON.stringify({ statusLine: cmd }, null, 2) + '\n',
      'utf8',
    )

    try {
      const conversationKey = `tui:${Math.random().toString(16).slice(2)}`
      const h = createInkTestHarness(
        <PromptInputHarness conversationKey={conversationKey} />,
      )
      mounted.push(h)

      await h.wait(25)
      await h.wait(1000)

      expect(h.getOutput()).toContain('hello-statusline')
    } finally {
      if (originalHome === undefined) delete process.env.HOME
      else process.env.HOME = originalHome
      if (originalUserProfile === undefined) delete process.env.USERPROFILE
      else process.env.USERPROFILE = originalUserProfile
      if (originalEnabled === undefined)
        delete process.env.KODE_STATUSLINE_ENABLED
      else process.env.KODE_STATUSLINE_ENABLED = originalEnabled
      if (originalConfigDir === undefined) delete process.env.KODE_CONFIG_DIR
      else process.env.KODE_CONFIG_DIR = originalConfigDir
      rmSync(homeDir, { recursive: true, force: true })
    }
  })
})
