import { afterEach, beforeEach, describe, expect, test } from 'bun:test'
import { existsSync, mkdtempSync, readFileSync, rmSync } from 'fs'
import { tmpdir } from 'os'
import { join } from 'path'
import outputStyle from '@commands/output-style'
import { processUserInput } from '@utils/messages'
import { setCwd } from '@utils/state'
import { clearOutputStyleCache } from '@services/outputStyles'

describe('/output-style (menu + direct set + help)', () => {
  const stripAnsi = (value: string | undefined): string =>
    (value ?? '').replace(/\x1b\[[0-9;]*m/g, '')

  const runnerCwd = process.cwd()
  const originalConfigDir = process.env.KODE_CONFIG_DIR

  let projectDir: string
  let homeDir: string

  beforeEach(async () => {
    clearOutputStyleCache()
    projectDir = mkdtempSync(join(tmpdir(), 'kode-output-style-proj-'))
    homeDir = mkdtempSync(join(tmpdir(), 'kode-output-style-home-'))
    process.env.KODE_CONFIG_DIR = join(homeDir, '.kode')
    await setCwd(projectDir)
  })

  afterEach(async () => {
    clearOutputStyleCache()
    await setCwd(runnerCwd)
    if (originalConfigDir === undefined) delete process.env.KODE_CONFIG_DIR
    else process.env.KODE_CONFIG_DIR = originalConfigDir
    rmSync(projectDir, { recursive: true, force: true })
    rmSync(homeDir, { recursive: true, force: true })
  })

  test('direct set persists outputStyle to .kode/settings.local.json', async () => {
    let message: string | undefined
    const ctx = {} as any

    const jsx = await (outputStyle as any).call(
      (result?: string) => {
        message = result
      },
      ctx,
      'default',
    )

    expect(jsx).toBeNull()
    expect(stripAnsi(message)).toBe('Set output style to default')

    const settingsPath = join(projectDir, '.kode', 'settings.local.json')
    expect(existsSync(settingsPath)).toBe(true)
    const json = JSON.parse(readFileSync(settingsPath, 'utf8'))
    expect(json.outputStyle).toBe('default')
  })

  test('invalid style does not overwrite existing outputStyle', async () => {
    let msg1: string | undefined
    await (outputStyle as any).call(
      (r?: string) => (msg1 = r),
      {} as any,
      'default',
    )
    expect(stripAnsi(msg1)).toBe('Set output style to default')

    let msg2: string | undefined
    await (outputStyle as any).call(
      (r?: string) => (msg2 = r),
      {} as any,
      'not-a-style',
    )
    expect(msg2).toBe('Invalid output style: not-a-style')

    const settingsPath = join(projectDir, '.kode', 'settings.local.json')
    const json = JSON.parse(readFileSync(settingsPath, 'utf8'))
    expect(json.outputStyle).toBe('default')
  })

  test('processUserInput passes args to local-jsx commands', async () => {
    const setToolJSXCalls: any[] = []
    const setToolJSX = (value: any) => setToolJSXCalls.push(value)

    const ctx: any = {
      abortController: new AbortController(),
      messageId: 'm',
      readFileTimestamps: {},
      options: {
        commands: [outputStyle as any],
        tools: [],
        verbose: false,
        safeMode: false,
        forkNumber: 0,
        messageLogName: 'test',
        maxThinkingTokens: 0,
      },
      setForkConvoWithMessagesOnTheNextRender: () => {},
    }

    const messages = await processUserInput(
      '/output-style default',
      'prompt',
      setToolJSX as any,
      ctx,
      null,
    )

    expect(messages).toHaveLength(2)
    expect(messages[0]?.type).toBe('user')
    const second = messages[1]
    expect(second?.type).toBe('assistant')
    if (!second || second.type !== 'assistant') {
      throw new Error('Expected assistant message')
    }
    const rendered =
      typeof second.message.content === 'string'
        ? second.message.content
        : Array.isArray(second.message.content)
          ? second.message.content
              .filter(
                (b: any) => b && typeof b === 'object' && b.type === 'text',
              )
              .map((b: any) => String(b.text ?? ''))
              .join('')
          : ''
    expect(stripAnsi(rendered)).toBe('Set output style to default')

    const settingsPath = join(projectDir, '.kode', 'settings.local.json')
    const json = JSON.parse(readFileSync(settingsPath, 'utf8'))
    expect(json.outputStyle).toBe('default')

    expect(
      setToolJSXCalls.filter(call => call && typeof call === 'object'),
    ).toHaveLength(0)
  })

  test('inline help and current style are non-interactive', async () => {
    let help: string | undefined
    const jsxHelp = await (outputStyle as any).call(
      (r?: string) => (help = r),
      {} as any,
      'help',
    )
    expect(jsxHelp).toBeNull()
    expect(help).toContain('Run /output-style')

    let current: string | undefined
    const jsxCurrent = await (outputStyle as any).call(
      (r?: string) => (current = r),
      {} as any,
      '?',
    )
    expect(jsxCurrent).toBeNull()
    expect(current).toContain('Current output style:')
  })
})
