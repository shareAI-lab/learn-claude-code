import { spawn } from 'child_process'
import { existsSync, readFileSync, statSync } from 'fs'
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'fs'
import { tmpdir } from 'os'
import { join } from 'path'
import { minimatch } from 'minimatch'
import { logError } from '@utils/log'
import { getCwd } from '@utils/state'
import { getKodeAgentSessionId } from '@utils/protocol/kodeAgentSessionId'
import { getSessionPlugins } from '@utils/session/sessionPlugins'
import { loadSettingsWithLegacyFallback } from '@utils/config/settingsFiles'

type HookEventName =
  | 'PreToolUse'
  | 'PostToolUse'
  | 'Stop'
  | 'SubagentStop'
  | 'UserPromptSubmit'
  | 'SessionStart'
  | 'SessionEnd'

type CommandHook = {
  type: 'command'
  command: string
  timeout?: number
  pluginRoot?: string
}

type PromptHook = {
  type: 'prompt'
  prompt: string
  timeout?: number
  pluginRoot?: string
}

type Hook = CommandHook | PromptHook

type HookMatcher = {
  matcher: string
  hooks: Hook[]
}

type HookFileEnvelope = {
  description?: unknown
  hooks?: unknown
  [key: string]: unknown
}

type HooksSettings = Partial<Record<HookEventName, HookMatcher[]>> & {
  [key: string]: unknown
}

type SettingsFileWithHooks = {
  hooks?: HooksSettings
  [key: string]: unknown
}

export type PreToolUseHookOutcome =
  | {
      kind: 'allow'
      warnings: string[]
      permissionDecision?: 'allow' | 'ask'
      updatedInput?: Record<string, unknown>
      systemMessages?: string[]
      additionalContexts?: string[]
    }
  | {
      kind: 'block'
      message: string
      systemMessages?: string[]
      additionalContexts?: string[]
    }

type CachedHooks = {
  mtimeMs: number
  byEvent: Partial<Record<HookEventName, HookMatcher[]>>
}

const cache = new Map<string, CachedHooks>()
const pluginHooksCache = new Map<string, CachedHooks>()
const sessionStartCache = new Map<string, { additionalContext: string }>()

type HookRuntimeState = {
  transcriptPath?: string
  queuedSystemMessages: string[]
  queuedAdditionalContexts: string[]
}

const HOOK_RUNTIME_STATE_KEY = '__kodeHookRuntimeState'

function getHookRuntimeState(toolUseContext: any): HookRuntimeState {
  const existing = toolUseContext?.[HOOK_RUNTIME_STATE_KEY]
  if (
    existing &&
    typeof existing === 'object' &&
    Array.isArray((existing as any).queuedSystemMessages) &&
    Array.isArray((existing as any).queuedAdditionalContexts)
  ) {
    return existing as HookRuntimeState
  }
  const created: HookRuntimeState = {
    transcriptPath: undefined,
    queuedSystemMessages: [],
    queuedAdditionalContexts: [],
  }
  if (toolUseContext && typeof toolUseContext === 'object') {
    ;(toolUseContext as any)[HOOK_RUNTIME_STATE_KEY] = created
  }
  return created
}

export function updateHookTranscriptForMessages(
  toolUseContext: any,
  messages: any[],
): void {
  const state = getHookRuntimeState(toolUseContext)
  const sessionId = getKodeAgentSessionId()

  const dir = join(tmpdir(), 'kode-hooks-transcripts')
  try {
    mkdirSync(dir, { recursive: true })
  } catch {}

  if (!state.transcriptPath) {
    state.transcriptPath = join(dir, `${sessionId}.transcript.txt`)
  }

  const lines: string[] = []
  for (const msg of Array.isArray(messages) ? messages : []) {
    if (!msg || typeof msg !== 'object') continue
    if (msg.type !== 'user' && msg.type !== 'assistant') continue

    if (msg.type === 'user') {
      const content = (msg as any)?.message?.content
      if (typeof content === 'string') {
        lines.push(`user: ${content}`)
        continue
      }
      if (Array.isArray(content)) {
        const parts: string[] = []
        for (const block of content) {
          if (!block || typeof block !== 'object') continue
          if (block.type === 'text') parts.push(String(block.text ?? ''))
          if (block.type === 'tool_result')
            parts.push(`[tool_result] ${String(block.content ?? '')}`)
        }
        lines.push(`user: ${parts.join('')}`)
      }
      continue
    }

    const content = (msg as any)?.message?.content
    if (typeof content === 'string') {
      lines.push(`assistant: ${content}`)
      continue
    }
    if (!Array.isArray(content)) continue

    const parts: string[] = []
    for (const block of content) {
      if (!block || typeof block !== 'object') continue
      if (block.type === 'text') parts.push(String(block.text ?? ''))
      if (block.type === 'tool_use' || block.type === 'server_tool_use') {
        parts.push(
          `[tool_use:${String(block.name ?? '')}] ${hookValueForPrompt(block.input)}`,
        )
      }
      if (block.type === 'mcp_tool_use') {
        parts.push(
          `[mcp_tool_use:${String(block.name ?? '')}] ${hookValueForPrompt(block.input)}`,
        )
      }
    }
    lines.push(`assistant: ${parts.join('')}`)
  }

  try {
    writeFileSync(state.transcriptPath, lines.join('\n') + '\n', 'utf8')
  } catch {}
}

export function drainHookSystemPromptAdditions(toolUseContext: any): string[] {
  const state = getHookRuntimeState(toolUseContext)
  const systemMessages = state.queuedSystemMessages.splice(
    0,
    state.queuedSystemMessages.length,
  )
  const contexts = state.queuedAdditionalContexts.splice(
    0,
    state.queuedAdditionalContexts.length,
  )

  const additions: string[] = []
  if (systemMessages.length > 0) {
    additions.push(
      ['\n# Hook system messages', ...systemMessages.map(m => m.trim())]
        .filter(Boolean)
        .join('\n\n'),
    )
  }
  if (contexts.length > 0) {
    additions.push(
      ['\n# Hook additional context', ...contexts.map(m => m.trim())]
        .filter(Boolean)
        .join('\n\n'),
    )
  }
  return additions
}

export function getHookTranscriptPath(toolUseContext: any): string | undefined {
  return getHookRuntimeState(toolUseContext).transcriptPath
}

export function queueHookSystemMessages(
  toolUseContext: any,
  messages: string[],
): void {
  const state = getHookRuntimeState(toolUseContext)
  for (const msg of messages) {
    const trimmed = String(msg ?? '').trim()
    if (trimmed) state.queuedSystemMessages.push(trimmed)
  }
}

export function queueHookAdditionalContexts(
  toolUseContext: any,
  contexts: string[],
): void {
  const state = getHookRuntimeState(toolUseContext)
  for (const ctx of contexts) {
    const trimmed = String(ctx ?? '').trim()
    if (trimmed) state.queuedAdditionalContexts.push(trimmed)
  }
}

function isCommandHook(value: unknown): value is CommandHook {
  return (
    value !== null &&
    typeof value === 'object' &&
    (value as any).type === 'command' &&
    typeof (value as any).command === 'string' &&
    Boolean((value as any).command.trim())
  )
}

function isPromptHook(value: unknown): value is PromptHook {
  return (
    value !== null &&
    typeof value === 'object' &&
    (value as any).type === 'prompt' &&
    typeof (value as any).prompt === 'string' &&
    Boolean((value as any).prompt.trim())
  )
}

function isHook(value: unknown): value is Hook {
  return isCommandHook(value) || isPromptHook(value)
}

function parseHookMatchers(value: unknown): HookMatcher[] {
  if (!Array.isArray(value)) return []

  const out: HookMatcher[] = []
  for (const item of value) {
    if (!item || typeof item !== 'object') continue
    const matcher =
      typeof (item as any).matcher === 'string'
        ? (item as any).matcher.trim()
        : ''
    const effectiveMatcher = matcher || '*'
    const hooksRaw = (item as any).hooks
    const hooks = Array.isArray(hooksRaw) ? hooksRaw.filter(isHook) : []
    if (hooks.length === 0) continue
    out.push({ matcher: effectiveMatcher, hooks })
  }
  return out
}

function parseHooksByEvent(
  rawHooks: unknown,
): Partial<Record<HookEventName, HookMatcher[]>> {
  if (!rawHooks || typeof rawHooks !== 'object') return {}
  const hooks: any = rawHooks
  return {
    PreToolUse: parseHookMatchers(hooks.PreToolUse),
    PostToolUse: parseHookMatchers(hooks.PostToolUse),
    Stop: parseHookMatchers(hooks.Stop),
    SubagentStop: parseHookMatchers(hooks.SubagentStop),
    UserPromptSubmit: parseHookMatchers(hooks.UserPromptSubmit),
    SessionStart: parseHookMatchers(hooks.SessionStart),
    SessionEnd: parseHookMatchers(hooks.SessionEnd),
  }
}

function loadInlinePluginHooksByEvent(plugin: {
  manifestPath: string
  manifest: unknown
}): Partial<Record<HookEventName, HookMatcher[]>> | null {
  const manifestHooks = (plugin.manifest as any)?.hooks
  if (
    !manifestHooks ||
    typeof manifestHooks !== 'object' ||
    Array.isArray(manifestHooks)
  )
    return null

  const hookObj =
    (manifestHooks as any).hooks &&
    typeof (manifestHooks as any).hooks === 'object' &&
    !Array.isArray((manifestHooks as any).hooks)
      ? (manifestHooks as any).hooks
      : manifestHooks

  const cacheKey = `${plugin.manifestPath}#inlineHooks`
  try {
    const stat = statSync(plugin.manifestPath)
    const cached = pluginHooksCache.get(cacheKey)
    if (cached && cached.mtimeMs === stat.mtimeMs) return cached.byEvent

    const byEvent = parseHooksByEvent(hookObj)
    pluginHooksCache.set(cacheKey, { mtimeMs: stat.mtimeMs, byEvent })
    return byEvent
  } catch (err) {
    logError(err)
    pluginHooksCache.delete(cacheKey)
    return null
  }
}

function loadPreToolUseMatchers(projectDir: string): HookMatcher[] {
  const loaded = loadSettingsWithLegacyFallback({
    destination: 'projectSettings',
    projectDir,
    migrateToPrimary: true,
  })
  const settingsPath = loaded.usedPath
  if (!settingsPath) return []
  try {
    const stat = statSync(settingsPath)
    const cached = cache.get(settingsPath)
    if (cached && cached.mtimeMs === stat.mtimeMs)
      return cached.byEvent.PreToolUse ?? []

    const parsed = loaded.settings as SettingsFileWithHooks | null
    const byEvent = parseHooksByEvent(parsed?.hooks)
    cache.set(settingsPath, { mtimeMs: stat.mtimeMs, byEvent })
    return byEvent.PreToolUse ?? []
  } catch {
    cache.delete(settingsPath)
    return []
  }
}

function loadSettingsMatchers(
  projectDir: string,
  event: HookEventName,
): HookMatcher[] {
  const loaded = loadSettingsWithLegacyFallback({
    destination: 'projectSettings',
    projectDir,
    migrateToPrimary: true,
  })
  const settingsPath = loaded.usedPath
  if (!settingsPath) return []
  try {
    const stat = statSync(settingsPath)
    const cached = cache.get(settingsPath)
    if (cached && cached.mtimeMs === stat.mtimeMs)
      return cached.byEvent[event] ?? []

    const parsed = loaded.settings as SettingsFileWithHooks | null
    const byEvent = parseHooksByEvent(parsed?.hooks)
    cache.set(settingsPath, { mtimeMs: stat.mtimeMs, byEvent })
    return byEvent[event] ?? []
  } catch {
    cache.delete(settingsPath)
    return []
  }
}

function matcherMatchesTool(matcher: string, toolName: string): boolean {
  if (!matcher) return false
  if (matcher === '*' || matcher === 'all') return true
  if (matcher === toolName) return true
  try {
    if (minimatch(toolName, matcher, { dot: true, nocase: false })) return true
  } catch {
  }
  try {
    if (new RegExp(matcher).test(toolName)) return true
  } catch {
  }
  return false
}

function buildShellCommand(command: string): string[] {
  if (process.platform === 'win32') {
    return ['cmd.exe', '/d', '/s', '/c', command]
  }
  return ['/bin/sh', '-c', command]
}

async function runCommandHook(args: {
  command: string
  stdinJson: unknown
  cwd: string
  env?: Record<string, string>
  signal?: AbortSignal
}): Promise<{ exitCode: number; stdout: string; stderr: string }> {
  const cmd = buildShellCommand(args.command)
  const proc = spawn(cmd[0], cmd.slice(1), {
    cwd: args.cwd,
    env: { ...(process.env as any), ...(args.env ?? {}) },
    stdio: ['pipe', 'pipe', 'pipe'],
    windowsHide: true,
  })

  let wasAborted = false
  const onAbort = () => {
    wasAborted = true
    try {
      proc.kill()
    } catch {}
  }
  if (args.signal) {
    if (args.signal.aborted) onAbort()
    args.signal.addEventListener('abort', onAbort, { once: true })
  }

  try {
    const input = JSON.stringify(args.stdinJson)
    try {
      proc.stdin?.write(input)
      proc.stdin?.end()
    } catch {}

    let stdout = ''
    let stderr = ''

    const collect = (
      stream: NodeJS.ReadableStream | null,
      append: (chunk: string) => void,
    ): { done: Promise<void>; cleanup: () => void } => {
      if (!stream) {
        return { done: Promise.resolve(), cleanup: () => {} }
      }
      try {
        ;(stream as any).setEncoding?.('utf8')
      } catch {}

      let resolveDone: (() => void) | null = null
      const done = new Promise<void>(resolve => {
        resolveDone = resolve
      })

      const finish = () => {
        cleanup()
        if (!resolveDone) return
        resolveDone()
        resolveDone = null
      }

      const onData = (chunk: unknown) => {
        append(
          typeof chunk === 'string'
            ? chunk
            : Buffer.isBuffer(chunk)
              ? chunk.toString('utf8')
              : String(chunk),
        )
      }

      const onError = () => finish()

      const cleanup = () => {
        stream.off('data', onData)
        stream.off('end', finish)
        stream.off('close', finish)
        stream.off('error', onError)
      }

      stream.on('data', onData)
      stream.once('end', finish)
      stream.once('close', finish)
      stream.once('error', onError)

      return { done, cleanup }
    }

    const stdoutCollector = collect(proc.stdout, chunk => {
      stdout += chunk
    })
    const stderrCollector = collect(proc.stderr, chunk => {
      stderr += chunk
    })

    const exitCode = await new Promise<number>(resolve => {
      proc.once('exit', (code, signal) => {
        if (typeof code === 'number') return resolve(code)
        if (signal) return resolve(143)
        return resolve(0)
      })
      proc.once('error', () => resolve(1))
    })

    await Promise.race([
      Promise.allSettled([stdoutCollector.done, stderrCollector.done]),
      new Promise(resolve => setTimeout(resolve, 250)),
    ])
    stdoutCollector.cleanup()
    stderrCollector.cleanup()

    return {
      exitCode: wasAborted && exitCode === 0 ? 143 : exitCode,
      stdout,
      stderr,
    }
  } finally {
    if (args.signal) {
      try {
        args.signal.removeEventListener('abort', onAbort)
      } catch {}
    }
  }
}

function mergeAbortSignals(signals: Array<AbortSignal | undefined>): {
  signal: AbortSignal
  cleanup: () => void
} {
  const controller = new AbortController()
  const onAbort = () => controller.abort()

  const cleanups: Array<() => void> = []
  for (const signal of signals) {
    if (!signal) continue
    if (signal.aborted) {
      controller.abort()
      continue
    }
    signal.addEventListener('abort', onAbort, { once: true })
    cleanups.push(() => {
      try {
        signal.removeEventListener('abort', onAbort)
      } catch {}
    })
  }

  return {
    signal: controller.signal,
    cleanup: () => cleanups.forEach(fn => fn()),
  }
}

function withHookTimeout(args: {
  timeoutSeconds?: number
  parentSignal?: AbortSignal
  fallbackTimeoutMs: number
}): { signal: AbortSignal; cleanup: () => void } {
  const timeoutMs =
    typeof args.timeoutSeconds === 'number' &&
    Number.isFinite(args.timeoutSeconds)
      ? Math.max(0, Math.floor(args.timeoutSeconds * 1000))
      : args.fallbackTimeoutMs

  const timeoutSignal =
    typeof AbortSignal !== 'undefined' &&
    typeof (AbortSignal as any).timeout === 'function'
      ? (AbortSignal as any).timeout(timeoutMs)
      : (() => {
          const controller = new AbortController()
          const timer = setTimeout(() => controller.abort(), timeoutMs)
          const signal = controller.signal
          ;(signal as any).__cleanup = () => clearTimeout(timer)
          return signal
        })()

  const merged = mergeAbortSignals([args.parentSignal, timeoutSignal])
  const timeoutCleanup =
    typeof (timeoutSignal as any).__cleanup === 'function'
      ? (timeoutSignal as any).__cleanup
      : () => {}

  return {
    signal: merged.signal,
    cleanup: () => {
      merged.cleanup()
      timeoutCleanup()
    },
  }
}

function coerceHookMessage(stdout: string, stderr: string): string {
  const s = (stderr || '').trim()
  if (s) return s
  const o = (stdout || '').trim()
  if (o) return o
  return 'Hook blocked the tool call.'
}

function coerceHookPermissionMode(mode: unknown): 'ask' | 'allow' {
  if (mode === 'acceptEdits' || mode === 'bypassPermissions') return 'allow'
  return 'ask'
}

function extractFirstJsonObject(text: string): string | null {
  let start = -1
  let depth = 0
  let inString = false
  let escaped = false

  for (let i = 0; i < text.length; i++) {
    const ch = text[i]

    if (start === -1) {
      if (ch === '{') {
        start = i
        depth = 1
      }
      continue
    }

    if (inString) {
      if (escaped) {
        escaped = false
        continue
      }
      if (ch === '\\') {
        escaped = true
        continue
      }
      if (ch === '"') {
        inString = false
      }
      continue
    }

    if (ch === '"') {
      inString = true
      continue
    }

    if (ch === '{') {
      depth++
      continue
    }
    if (ch === '}') {
      depth--
      if (depth === 0) return text.slice(start, i + 1)
    }
  }

  return null
}

function parseSessionStartAdditionalContext(stdout: string): string | null {
  const trimmed = String(stdout ?? '').trim()
  if (!trimmed) return null

  const jsonStr = extractFirstJsonObject(trimmed) ?? trimmed
  try {
    const parsed = JSON.parse(jsonStr)
    const additional =
      parsed &&
      typeof parsed === 'object' &&
      (parsed as any).hookSpecificOutput &&
      typeof (parsed as any).hookSpecificOutput.additionalContext === 'string'
        ? String((parsed as any).hookSpecificOutput.additionalContext)
        : null
    return additional && additional.trim() ? additional : null
  } catch {
    return null
  }
}

function tryParseHookJson(stdout: string): any | null {
  const trimmed = String(stdout ?? '').trim()
  if (!trimmed) return null
  const jsonStr = extractFirstJsonObject(trimmed) ?? trimmed
  try {
    const parsed = JSON.parse(jsonStr)
    return parsed && typeof parsed === 'object' ? parsed : null
  } catch {
    return null
  }
}

function normalizePermissionDecision(
  value: unknown,
): 'allow' | 'deny' | 'ask' | 'passthrough' | null {
  if (typeof value !== 'string') return null
  const normalized = value.trim().toLowerCase()
  if (normalized === 'allow' || normalized === 'approve') return 'allow'
  if (normalized === 'deny' || normalized === 'block') return 'deny'
  if (normalized === 'ask') return 'ask'
  if (normalized === 'passthrough' || normalized === 'continue')
    return 'passthrough'
  return null
}

function normalizeStopDecision(value: unknown): 'approve' | 'block' | null {
  if (typeof value !== 'string') return null
  const normalized = value.trim().toLowerCase()
  if (normalized === 'approve' || normalized === 'allow') return 'approve'
  if (normalized === 'block' || normalized === 'deny') return 'block'
  return null
}

function hookValueForPrompt(value: unknown): string {
  if (value === null || value === undefined) return ''
  if (typeof value === 'string') return value
  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return String(value)
  }
}

function interpolatePromptHookTemplate(
  template: string,
  hookInput: Record<string, unknown>,
): string {
  return String(template ?? '')
    .replaceAll('$TOOL_INPUT', hookValueForPrompt(hookInput.tool_input))
    .replaceAll('$TOOL_RESULT', hookValueForPrompt(hookInput.tool_result))
    .replaceAll('$TOOL_RESPONSE', hookValueForPrompt(hookInput.tool_response))
    .replaceAll('$USER_PROMPT', hookValueForPrompt(hookInput.user_prompt))
    .replaceAll('$PROMPT', hookValueForPrompt(hookInput.prompt))
    .replaceAll('$REASON', hookValueForPrompt(hookInput.reason))
}

function extractAssistantText(message: any): string {
  const content = (message as any)?.message?.content
  if (typeof content === 'string') return content
  if (!Array.isArray(content)) return ''
  return content
    .filter((b: any) => b && typeof b === 'object' && b.type === 'text')
    .map((b: any) => String(b.text ?? ''))
    .join('')
}

async function runPromptHook(args: {
  hook: PromptHook
  hookEvent: HookEventName
  hookInput: Record<string, unknown>
  safeMode: boolean
  parentSignal?: AbortSignal
  fallbackTimeoutMs: number
}): Promise<{ exitCode: number; stdout: string; stderr: string }> {
  const { signal, cleanup } = withHookTimeout({
    timeoutSeconds: args.hook.timeout,
    parentSignal: args.parentSignal,
    fallbackTimeoutMs: args.fallbackTimeoutMs,
  })

  try {
    const { queryQuick } = await import('@services/llmLazy')

    const systemPrompt = [
      'You are executing a Kode prompt hook.',
      'Return a single JSON object only (no markdown, no prose).',
      `hook_event_name: ${args.hookEvent}`,
      'Valid fields include:',
      '- systemMessage: string',
      '- decision: \"approve\" | \"block\" (Stop/SubagentStop only)',
      '- reason: string (Stop/SubagentStop only)',
      '- hookSpecificOutput.permissionDecision: \"allow\" | \"deny\" | \"ask\" | \"passthrough\" (PreToolUse only)',
      '- hookSpecificOutput.updatedInput: object (PreToolUse only)',
      '- hookSpecificOutput.additionalContext: string (SessionStart/any)',
    ]

    const promptText = interpolatePromptHookTemplate(
      args.hook.prompt,
      args.hookInput,
    )
    const userPrompt = `${promptText}\n\n# Hook input JSON\n${hookValueForPrompt(args.hookInput)}`

    const response = await queryQuick({
      systemPrompt,
      userPrompt,
      signal,
    })

    return { exitCode: 0, stdout: extractAssistantText(response), stderr: '' }
  } catch (err) {
    return {
      exitCode: 1,
      stdout: '',
      stderr: err instanceof Error ? err.message : String(err),
    }
  } finally {
    cleanup()
  }
}

function applyEnvFileToProcessEnv(envFilePath: string): void {
  let raw: string
  try {
    raw = readFileSync(envFilePath, 'utf8')
  } catch {
    return
  }

  const lines = raw.split(/\r?\n/)
  for (const line of lines) {
    const trimmed = line.trim()
    if (!trimmed || trimmed.startsWith('#')) continue

    const withoutExport = trimmed.startsWith('export ')
      ? trimmed.slice('export '.length).trim()
      : trimmed

    const eq = withoutExport.indexOf('=')
    if (eq <= 0) continue

    const key = withoutExport.slice(0, eq).trim()
    let value = withoutExport.slice(eq + 1).trim()
    if (!key) continue

    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1)
    }

    process.env[key] = value
  }
}

function loadPluginPreToolUseMatchers(projectDir: string): HookMatcher[] {
  const plugins = getSessionPlugins()
  if (plugins.length === 0) return []

  const out: HookMatcher[] = []
  for (const plugin of plugins) {
    for (const hookPath of plugin.hooksFiles ?? []) {
      try {
        const stat = statSync(hookPath)
        const cached = pluginHooksCache.get(hookPath)
        if (cached && cached.mtimeMs === stat.mtimeMs) {
          out.push(
            ...(cached.byEvent.PreToolUse ?? []).map(m => ({
              matcher: m.matcher,
              hooks: m.hooks.map(h => ({ ...h, pluginRoot: plugin.rootDir })),
            })),
          )
          continue
        }

        const raw = readFileSync(hookPath, 'utf8')
        const parsed = JSON.parse(raw) as HookFileEnvelope
        const hookObj =
          parsed && typeof parsed === 'object' && parsed.hooks
            ? parsed.hooks
            : parsed
        const byEvent = parseHooksByEvent(hookObj)
        pluginHooksCache.set(hookPath, { mtimeMs: stat.mtimeMs, byEvent })
        out.push(
          ...(byEvent.PreToolUse ?? []).map(m => ({
            matcher: m.matcher,
            hooks: m.hooks.map(h => ({ ...h, pluginRoot: plugin.rootDir })),
          })),
        )
      } catch (err) {
        logError(err)
        continue
      }
    }

    const inlineByEvent = loadInlinePluginHooksByEvent(plugin)
    if (inlineByEvent?.PreToolUse) {
      out.push(
        ...inlineByEvent.PreToolUse.map(m => ({
          matcher: m.matcher,
          hooks: m.hooks.map(h => ({ ...h, pluginRoot: plugin.rootDir })),
        })),
      )
    }
  }

  return out
}

function loadPluginMatchers(
  projectDir: string,
  event: HookEventName,
): HookMatcher[] {
  const plugins = getSessionPlugins()
  if (plugins.length === 0) return []

  const out: HookMatcher[] = []
  for (const plugin of plugins) {
    for (const hookPath of plugin.hooksFiles ?? []) {
      try {
        const stat = statSync(hookPath)
        const cached = pluginHooksCache.get(hookPath)
        if (cached && cached.mtimeMs === stat.mtimeMs) {
          out.push(
            ...(cached.byEvent[event] ?? []).map(m => ({
              matcher: m.matcher,
              hooks: m.hooks.map(h => ({ ...h, pluginRoot: plugin.rootDir })),
            })),
          )
          continue
        }

        const raw = readFileSync(hookPath, 'utf8')
        const parsed = JSON.parse(raw) as HookFileEnvelope
        const hookObj =
          parsed && typeof parsed === 'object' && parsed.hooks
            ? parsed.hooks
            : parsed
        const byEvent = parseHooksByEvent(hookObj)
        pluginHooksCache.set(hookPath, { mtimeMs: stat.mtimeMs, byEvent })
        out.push(
          ...(byEvent[event] ?? []).map(m => ({
            matcher: m.matcher,
            hooks: m.hooks.map(h => ({ ...h, pluginRoot: plugin.rootDir })),
          })),
        )
      } catch (err) {
        logError(err)
        continue
      }
    }

    const inlineByEvent = loadInlinePluginHooksByEvent(plugin)
    if (inlineByEvent?.[event]) {
      out.push(
        ...(inlineByEvent[event] ?? []).map(m => ({
          matcher: m.matcher,
          hooks: m.hooks.map(h => ({ ...h, pluginRoot: plugin.rootDir })),
        })),
      )
    }
  }
  return out
}

function parseSessionStartHooks(value: unknown): CommandHook[] {
  if (!Array.isArray(value)) return []
  const out: CommandHook[] = []
  for (const item of value) {
    if (!item || typeof item !== 'object') continue
    const hooksRaw = (item as any).hooks
    const hooks = Array.isArray(hooksRaw) ? hooksRaw.filter(isCommandHook) : []
    out.push(...hooks)
  }
  return out
}

export async function getSessionStartAdditionalContext(args?: {
  permissionMode?: unknown
  cwd?: string
  signal?: AbortSignal
}): Promise<string> {
  const sessionId = getKodeAgentSessionId()
  const cached = sessionStartCache.get(sessionId)
  if (cached) return cached.additionalContext

  const projectDir = args?.cwd ?? getCwd()
  const plugins = getSessionPlugins()
  if (plugins.length === 0) {
    sessionStartCache.set(sessionId, { additionalContext: '' })
    return ''
  }

  const envFileDir = mkdtempSync(join(tmpdir(), 'kode-env-'))
  const envFilePath = join(envFileDir, `${sessionId}.env`)
  try {
    writeFileSync(envFilePath, '', 'utf8')
  } catch {
  }

  const additionalContexts: string[] = []

  try {
    for (const plugin of plugins) {
      for (const hookPath of plugin.hooksFiles ?? []) {
        let hookObj: any
        try {
          const raw = readFileSync(hookPath, 'utf8')
          const parsed = JSON.parse(raw) as HookFileEnvelope
          hookObj =
            parsed && typeof parsed === 'object' && parsed.hooks
              ? parsed.hooks
              : parsed
        } catch {
          continue
        }

        const hooks = parseSessionStartHooks(hookObj?.SessionStart).map(h => ({
          ...h,
          pluginRoot: plugin.rootDir,
        }))
        if (hooks.length === 0) continue

        for (const hook of hooks) {
          const payload = {
            session_id: sessionId,
            cwd: projectDir,
            hook_event_name: 'SessionStart',
            permission_mode: coerceHookPermissionMode(args?.permissionMode),
          }

          const result = await runCommandHook({
            command: hook.command,
            stdinJson: payload,
            cwd: projectDir,
            env: {
              CLAUDE_PROJECT_DIR: projectDir,
              ...(hook.pluginRoot
                ? { CLAUDE_PLUGIN_ROOT: hook.pluginRoot }
                : {}),
              CLAUDE_ENV_FILE: envFilePath,
            },
            signal: args?.signal,
          })

          if (result.exitCode !== 0) continue
          const injected = parseSessionStartAdditionalContext(result.stdout)
          if (injected) additionalContexts.push(injected)
        }
      }

      const inlineHooks = (plugin.manifest as any)?.hooks
      if (
        inlineHooks &&
        typeof inlineHooks === 'object' &&
        !Array.isArray(inlineHooks)
      ) {
        const hookObj =
          (inlineHooks as any).hooks &&
          typeof (inlineHooks as any).hooks === 'object' &&
          !Array.isArray((inlineHooks as any).hooks)
            ? (inlineHooks as any).hooks
            : inlineHooks

        const hooks = parseSessionStartHooks(
          (hookObj as any)?.SessionStart,
        ).map(h => ({
          ...h,
          pluginRoot: plugin.rootDir,
        }))
        if (hooks.length > 0) {
          for (const hook of hooks) {
            const payload = {
              session_id: sessionId,
              cwd: projectDir,
              hook_event_name: 'SessionStart',
              permission_mode: coerceHookPermissionMode(args?.permissionMode),
            }

            const result = await runCommandHook({
              command: hook.command,
              stdinJson: payload,
              cwd: projectDir,
              env: {
                CLAUDE_PROJECT_DIR: projectDir,
                ...(hook.pluginRoot
                  ? { CLAUDE_PLUGIN_ROOT: hook.pluginRoot }
                  : {}),
                CLAUDE_ENV_FILE: envFilePath,
              },
              signal: args?.signal,
            })

            if (result.exitCode !== 0) continue
            const injected = parseSessionStartAdditionalContext(result.stdout)
            if (injected) additionalContexts.push(injected)
          }
        }
      }
    }
  } finally {
    applyEnvFileToProcessEnv(envFilePath)
    try {
      rmSync(envFileDir, { recursive: true, force: true })
    } catch {}
  }

  const additionalContext = additionalContexts.filter(Boolean).join('\n\n')
  sessionStartCache.set(sessionId, { additionalContext })
  return additionalContext
}

export async function runPreToolUseHooks(args: {
  toolName: string
  toolInput: Record<string, unknown>
  toolUseId: string
  permissionMode?: unknown
  cwd?: string
  transcriptPath?: string
  safeMode?: boolean
  signal?: AbortSignal
}): Promise<PreToolUseHookOutcome> {
  const projectDir = args.cwd ?? getCwd()
  const matchers = [
    ...loadSettingsMatchers(projectDir, 'PreToolUse'),
    ...loadPluginMatchers(projectDir, 'PreToolUse'),
  ]
  if (matchers.length === 0) return { kind: 'allow', warnings: [] }

  const applicable = matchers.filter(m =>
    matcherMatchesTool(m.matcher, args.toolName),
  )
  if (applicable.length === 0) return { kind: 'allow', warnings: [] }

  const hookInput: Record<string, unknown> = {
    session_id: getKodeAgentSessionId(),
    transcript_path: args.transcriptPath,
    cwd: projectDir,
    hook_event_name: 'PreToolUse',
    permission_mode: coerceHookPermissionMode(args.permissionMode),
    tool_name: args.toolName,
    tool_input: args.toolInput,
    tool_use_id: args.toolUseId,
  }

  const warnings: string[] = []
  const systemMessages: string[] = []
  const additionalContexts: string[] = []

  let mergedUpdatedInput: Record<string, unknown> | undefined
  let permissionDecision: 'allow' | 'ask' | null = null

  const executions: Array<
    Promise<{
      hook: Hook
      result: { exitCode: number; stdout: string; stderr: string }
    }>
  > = []

  for (const entry of applicable) {
    for (const hook of entry.hooks) {
      if (hook.type === 'prompt') {
        executions.push(
          runPromptHook({
            hook,
            hookEvent: 'PreToolUse',
            hookInput,
            safeMode: args.safeMode ?? false,
            parentSignal: args.signal,
            fallbackTimeoutMs: 30_000,
          }).then(result => ({ hook, result })),
        )
        continue
      }

      const { signal, cleanup } = withHookTimeout({
        timeoutSeconds: hook.timeout,
        parentSignal: args.signal,
        fallbackTimeoutMs: 60_000,
      })
      executions.push(
        runCommandHook({
          command: hook.command,
          stdinJson: hookInput,
          cwd: projectDir,
          env: {
            CLAUDE_PROJECT_DIR: projectDir,
            ...(hook.pluginRoot ? { CLAUDE_PLUGIN_ROOT: hook.pluginRoot } : {}),
          },
          signal,
        })
          .then(result => ({ hook, result }))
          .finally(cleanup),
      )
    }
  }

  const settled = await Promise.allSettled(executions)
  for (const item of settled) {
    if (item.status === 'rejected') {
      logError(item.reason)
      warnings.push(`Hook failed to run: ${String(item.reason ?? '')}`)
      continue
    }

    const { hook, result } = item.value

    if (result.exitCode === 2) {
      return {
        kind: 'block',
        message: coerceHookMessage(result.stdout, result.stderr),
      }
    }

    if (result.exitCode !== 0) {
      warnings.push(coerceHookMessage(result.stdout, result.stderr))
      continue
    }

    const json = tryParseHookJson(result.stdout)
    if (!json) continue

    if (typeof json.systemMessage === 'string' && json.systemMessage.trim()) {
      systemMessages.push(json.systemMessage.trim())
    }

    const additional =
      json.hookSpecificOutput &&
      typeof json.hookSpecificOutput === 'object' &&
      typeof json.hookSpecificOutput.additionalContext === 'string'
        ? String(json.hookSpecificOutput.additionalContext)
        : null
    if (additional && additional.trim()) {
      additionalContexts.push(additional.trim())
    }

    const decision = normalizePermissionDecision(
      json.hookSpecificOutput?.permissionDecision,
    )
    if (decision === 'deny') {
      const msg =
        systemMessages.length > 0
          ? systemMessages.join('\n\n')
          : coerceHookMessage(result.stdout, result.stderr)
      return {
        kind: 'block',
        message: msg,
        systemMessages,
        additionalContexts,
      }
    }

    if (decision === 'ask') {
      permissionDecision = 'ask'
    } else if (decision === 'allow') {
      if (!permissionDecision) permissionDecision = 'allow'
    }

    const updated =
      json.hookSpecificOutput &&
      typeof json.hookSpecificOutput === 'object' &&
      json.hookSpecificOutput.updatedInput &&
      typeof json.hookSpecificOutput.updatedInput === 'object'
        ? (json.hookSpecificOutput.updatedInput as Record<string, unknown>)
        : null
    if (updated) {
      mergedUpdatedInput = { ...(mergedUpdatedInput ?? {}), ...updated }
    }
  }

  return {
    kind: 'allow',
    warnings,
    permissionDecision:
      permissionDecision === 'allow'
        ? 'allow'
        : permissionDecision === 'ask'
          ? 'ask'
          : undefined,
    updatedInput:
      permissionDecision === 'allow' ? mergedUpdatedInput : undefined,
    systemMessages,
    additionalContexts,
  }
}

export async function runPostToolUseHooks(args: {
  toolName: string
  toolInput: Record<string, unknown>
  toolResult: unknown
  toolUseId: string
  permissionMode?: unknown
  cwd?: string
  transcriptPath?: string
  safeMode?: boolean
  signal?: AbortSignal
}): Promise<{
  warnings: string[]
  systemMessages: string[]
  additionalContexts: string[]
}> {
  const projectDir = args.cwd ?? getCwd()
  const matchers = [
    ...loadSettingsMatchers(projectDir, 'PostToolUse'),
    ...loadPluginMatchers(projectDir, 'PostToolUse'),
  ]
  if (matchers.length === 0) {
    return { warnings: [], systemMessages: [], additionalContexts: [] }
  }

  const applicable = matchers.filter(m =>
    matcherMatchesTool(m.matcher, args.toolName),
  )
  if (applicable.length === 0) {
    return { warnings: [], systemMessages: [], additionalContexts: [] }
  }

  const hookInput: Record<string, unknown> = {
    session_id: getKodeAgentSessionId(),
    transcript_path: args.transcriptPath,
    cwd: projectDir,
    hook_event_name: 'PostToolUse',
    permission_mode: coerceHookPermissionMode(args.permissionMode),
    tool_name: args.toolName,
    tool_input: args.toolInput,
    tool_result: args.toolResult,
    tool_response: args.toolResult,
    tool_use_id: args.toolUseId,
  }

  const warnings: string[] = []
  const systemMessages: string[] = []
  const additionalContexts: string[] = []

  const executions: Array<
    Promise<{
      hook: Hook
      result: { exitCode: number; stdout: string; stderr: string }
    }>
  > = []

  for (const entry of applicable) {
    for (const hook of entry.hooks) {
      if (hook.type === 'prompt') {
        executions.push(
          runPromptHook({
            hook,
            hookEvent: 'PostToolUse',
            hookInput,
            safeMode: args.safeMode ?? false,
            parentSignal: args.signal,
            fallbackTimeoutMs: 30_000,
          }).then(result => ({ hook, result })),
        )
        continue
      }

      const { signal, cleanup } = withHookTimeout({
        timeoutSeconds: hook.timeout,
        parentSignal: args.signal,
        fallbackTimeoutMs: 60_000,
      })
      executions.push(
        runCommandHook({
          command: hook.command,
          stdinJson: hookInput,
          cwd: projectDir,
          env: {
            CLAUDE_PROJECT_DIR: projectDir,
            ...(hook.pluginRoot ? { CLAUDE_PLUGIN_ROOT: hook.pluginRoot } : {}),
          },
          signal,
        })
          .then(result => ({ hook, result }))
          .finally(cleanup),
      )
    }
  }

  const settled = await Promise.allSettled(executions)
  for (const item of settled) {
    if (item.status === 'rejected') {
      logError(item.reason)
      warnings.push(`Hook failed to run: ${String(item.reason ?? '')}`)
      continue
    }

    const { result } = item.value
    if (result.exitCode !== 0) {
      warnings.push(coerceHookMessage(result.stdout, result.stderr))
      continue
    }

    const json = tryParseHookJson(result.stdout)
    if (!json) continue

    if (typeof json.systemMessage === 'string' && json.systemMessage.trim()) {
      systemMessages.push(json.systemMessage.trim())
    }

    const additional =
      json.hookSpecificOutput &&
      typeof json.hookSpecificOutput === 'object' &&
      typeof json.hookSpecificOutput.additionalContext === 'string'
        ? String(json.hookSpecificOutput.additionalContext)
        : null
    if (additional && additional.trim()) {
      additionalContexts.push(additional.trim())
    }
  }

  return { warnings, systemMessages, additionalContexts }
}

export type StopHookOutcome =
  | {
      decision: 'approve'
      warnings: string[]
      systemMessages: string[]
      additionalContexts: string[]
    }
  | {
      decision: 'block'
      message: string
      warnings: string[]
      systemMessages: string[]
      additionalContexts: string[]
    }

export async function runStopHooks(args: {
  hookEvent: 'Stop' | 'SubagentStop'
  reason?: string
  agentId?: string
  permissionMode?: unknown
  cwd?: string
  transcriptPath?: string
  safeMode?: boolean
  stopHookActive?: boolean
  signal?: AbortSignal
}): Promise<StopHookOutcome> {
  const projectDir = args.cwd ?? getCwd()
  const matchers = [
    ...loadSettingsMatchers(projectDir, args.hookEvent),
    ...loadPluginMatchers(projectDir, args.hookEvent),
  ]
  if (matchers.length === 0) {
    return {
      decision: 'approve',
      warnings: [],
      systemMessages: [],
      additionalContexts: [],
    }
  }

  const applicable = matchers.filter(m => matcherMatchesTool(m.matcher, '*'))
  if (applicable.length === 0) {
    return {
      decision: 'approve',
      warnings: [],
      systemMessages: [],
      additionalContexts: [],
    }
  }

  const hookInput: Record<string, unknown> = {
    session_id: getKodeAgentSessionId(),
    transcript_path: args.transcriptPath,
    cwd: projectDir,
    hook_event_name: args.hookEvent,
    permission_mode: coerceHookPermissionMode(args.permissionMode),
    reason: args.reason,
    stop_hook_active: args.stopHookActive === true,
    ...(args.hookEvent === 'SubagentStop'
      ? { agent_id: args.agentId, agent_transcript_path: args.transcriptPath }
      : {}),
  }

  const warnings: string[] = []
  const systemMessages: string[] = []
  const additionalContexts: string[] = []

  const executions: Array<
    Promise<{
      hook: Hook
      result: { exitCode: number; stdout: string; stderr: string }
    }>
  > = []

  for (const entry of applicable) {
    for (const hook of entry.hooks) {
      if (hook.type === 'prompt') {
        executions.push(
          runPromptHook({
            hook,
            hookEvent: args.hookEvent,
            hookInput,
            safeMode: args.safeMode ?? false,
            parentSignal: args.signal,
            fallbackTimeoutMs: 30_000,
          }).then(result => ({ hook, result })),
        )
        continue
      }

      const { signal, cleanup } = withHookTimeout({
        timeoutSeconds: hook.timeout,
        parentSignal: args.signal,
        fallbackTimeoutMs: 60_000,
      })
      executions.push(
        runCommandHook({
          command: hook.command,
          stdinJson: hookInput,
          cwd: projectDir,
          env: {
            CLAUDE_PROJECT_DIR: projectDir,
            ...(hook.pluginRoot ? { CLAUDE_PLUGIN_ROOT: hook.pluginRoot } : {}),
          },
          signal,
        })
          .then(result => ({ hook, result }))
          .finally(cleanup),
      )
    }
  }

  const settled = await Promise.allSettled(executions)
  for (const item of settled) {
    if (item.status === 'rejected') {
      logError(item.reason)
      warnings.push(`Hook failed to run: ${String(item.reason ?? '')}`)
      continue
    }

    const { result } = item.value

    if (result.exitCode === 2) {
      return {
        decision: 'block',
        message: coerceHookMessage(result.stdout, result.stderr),
        warnings,
        systemMessages,
        additionalContexts,
      }
    }

    if (result.exitCode !== 0) {
      warnings.push(coerceHookMessage(result.stdout, result.stderr))
      continue
    }

    const json = tryParseHookJson(result.stdout)
    if (!json) continue

    if (typeof json.systemMessage === 'string' && json.systemMessage.trim()) {
      systemMessages.push(json.systemMessage.trim())
    }

    const additional =
      json.hookSpecificOutput &&
      typeof json.hookSpecificOutput === 'object' &&
      typeof json.hookSpecificOutput.additionalContext === 'string'
        ? String(json.hookSpecificOutput.additionalContext)
        : null
    if (additional && additional.trim()) {
      additionalContexts.push(additional.trim())
    }

    const stopDecision = normalizeStopDecision(json.decision)
    if (stopDecision === 'block') {
      const reason =
        typeof json.reason === 'string' && json.reason.trim()
          ? json.reason.trim()
          : null
      const msg =
        reason ||
        (systemMessages.length > 0
          ? systemMessages.join('\n\n')
          : coerceHookMessage(result.stdout, result.stderr))
      return {
        decision: 'block',
        message: msg,
        warnings,
        systemMessages,
        additionalContexts,
      }
    }
  }

  return { decision: 'approve', warnings, systemMessages, additionalContexts }
}

export type UserPromptHookOutcome =
  | {
      decision: 'allow'
      warnings: string[]
      systemMessages: string[]
      additionalContexts: string[]
    }
  | {
      decision: 'block'
      message: string
      warnings: string[]
      systemMessages: string[]
      additionalContexts: string[]
    }

export async function runUserPromptSubmitHooks(args: {
  prompt: string
  permissionMode?: unknown
  cwd?: string
  transcriptPath?: string
  safeMode?: boolean
  signal?: AbortSignal
}): Promise<UserPromptHookOutcome> {
  const projectDir = args.cwd ?? getCwd()
  const matchers = [
    ...loadSettingsMatchers(projectDir, 'UserPromptSubmit'),
    ...loadPluginMatchers(projectDir, 'UserPromptSubmit'),
  ]
  if (matchers.length === 0) {
    return {
      decision: 'allow',
      warnings: [],
      systemMessages: [],
      additionalContexts: [],
    }
  }

  const applicable = matchers.filter(m => matcherMatchesTool(m.matcher, '*'))
  if (applicable.length === 0) {
    return {
      decision: 'allow',
      warnings: [],
      systemMessages: [],
      additionalContexts: [],
    }
  }

  const hookInput: Record<string, unknown> = {
    session_id: getKodeAgentSessionId(),
    transcript_path: args.transcriptPath,
    cwd: projectDir,
    hook_event_name: 'UserPromptSubmit',
    permission_mode: coerceHookPermissionMode(args.permissionMode),
    user_prompt: args.prompt,
    prompt: args.prompt,
  }

  const warnings: string[] = []
  const systemMessages: string[] = []
  const additionalContexts: string[] = []

  const executions: Array<
    Promise<{
      hook: Hook
      result: { exitCode: number; stdout: string; stderr: string }
    }>
  > = []

  for (const entry of applicable) {
    for (const hook of entry.hooks) {
      if (hook.type === 'prompt') {
        executions.push(
          runPromptHook({
            hook,
            hookEvent: 'UserPromptSubmit',
            hookInput,
            safeMode: args.safeMode ?? false,
            parentSignal: args.signal,
            fallbackTimeoutMs: 30_000,
          }).then(result => ({ hook, result })),
        )
        continue
      }

      const { signal, cleanup } = withHookTimeout({
        timeoutSeconds: hook.timeout,
        parentSignal: args.signal,
        fallbackTimeoutMs: 60_000,
      })
      executions.push(
        runCommandHook({
          command: hook.command,
          stdinJson: hookInput,
          cwd: projectDir,
          env: {
            CLAUDE_PROJECT_DIR: projectDir,
            ...(hook.pluginRoot ? { CLAUDE_PLUGIN_ROOT: hook.pluginRoot } : {}),
          },
          signal,
        })
          .then(result => ({ hook, result }))
          .finally(cleanup),
      )
    }
  }

  const settled = await Promise.allSettled(executions)
  for (const item of settled) {
    if (item.status === 'rejected') {
      logError(item.reason)
      warnings.push(`Hook failed to run: ${String(item.reason ?? '')}`)
      continue
    }

    const { result } = item.value

    if (result.exitCode === 2) {
      return {
        decision: 'block',
        message: coerceHookMessage(result.stdout, result.stderr),
        warnings,
        systemMessages,
        additionalContexts,
      }
    }

    if (result.exitCode !== 0) {
      warnings.push(coerceHookMessage(result.stdout, result.stderr))
      continue
    }

    const json = tryParseHookJson(result.stdout)
    if (!json) continue

    if (typeof json.systemMessage === 'string' && json.systemMessage.trim()) {
      systemMessages.push(json.systemMessage.trim())
    }

    const additional =
      json.hookSpecificOutput &&
      typeof json.hookSpecificOutput === 'object' &&
      typeof json.hookSpecificOutput.additionalContext === 'string'
        ? String(json.hookSpecificOutput.additionalContext)
        : null
    if (additional && additional.trim()) {
      additionalContexts.push(additional.trim())
    }

    const stopDecision = normalizeStopDecision(json.decision)
    if (stopDecision === 'block') {
      const reason =
        typeof json.reason === 'string' && json.reason.trim()
          ? json.reason.trim()
          : null
      const msg =
        reason ||
        (systemMessages.length > 0
          ? systemMessages.join('\n\n')
          : coerceHookMessage(result.stdout, result.stderr))
      return {
        decision: 'block',
        message: msg,
        warnings,
        systemMessages,
        additionalContexts,
      }
    }
  }

  return { decision: 'allow', warnings, systemMessages, additionalContexts }
}

export async function runSessionEndHooks(args: {
  reason: string
  permissionMode?: unknown
  cwd?: string
  transcriptPath?: string
  safeMode?: boolean
  signal?: AbortSignal
}): Promise<{ warnings: string[]; systemMessages: string[] }> {
  const projectDir = args.cwd ?? getCwd()
  const matchers = [
    ...loadSettingsMatchers(projectDir, 'SessionEnd'),
    ...loadPluginMatchers(projectDir, 'SessionEnd'),
  ]
  if (matchers.length === 0) return { warnings: [], systemMessages: [] }

  const applicable = matchers.filter(m => matcherMatchesTool(m.matcher, '*'))
  if (applicable.length === 0) return { warnings: [], systemMessages: [] }

  const hookInput: Record<string, unknown> = {
    session_id: getKodeAgentSessionId(),
    transcript_path: args.transcriptPath,
    cwd: projectDir,
    hook_event_name: 'SessionEnd',
    permission_mode: coerceHookPermissionMode(args.permissionMode),
    reason: args.reason,
  }

  const warnings: string[] = []
  const systemMessages: string[] = []

  const executions: Array<
    Promise<{
      hook: Hook
      result: { exitCode: number; stdout: string; stderr: string }
    }>
  > = []

  for (const entry of applicable) {
    for (const hook of entry.hooks) {
      if (hook.type === 'prompt') {
        executions.push(
          runPromptHook({
            hook,
            hookEvent: 'SessionEnd',
            hookInput,
            safeMode: args.safeMode ?? false,
            parentSignal: args.signal,
            fallbackTimeoutMs: 30_000,
          }).then(result => ({ hook, result })),
        )
        continue
      }

      const { signal, cleanup } = withHookTimeout({
        timeoutSeconds: hook.timeout,
        parentSignal: args.signal,
        fallbackTimeoutMs: 60_000,
      })
      executions.push(
        runCommandHook({
          command: hook.command,
          stdinJson: hookInput,
          cwd: projectDir,
          env: {
            CLAUDE_PROJECT_DIR: projectDir,
            ...(hook.pluginRoot ? { CLAUDE_PLUGIN_ROOT: hook.pluginRoot } : {}),
          },
          signal,
        })
          .then(result => ({ hook, result }))
          .finally(cleanup),
      )
    }
  }

  const settled = await Promise.allSettled(executions)
  for (const item of settled) {
    if (item.status === 'rejected') {
      logError(item.reason)
      warnings.push(`Hook failed to run: ${String(item.reason ?? '')}`)
      continue
    }

    const { result } = item.value
    if (result.exitCode !== 0) {
      warnings.push(coerceHookMessage(result.stdout, result.stderr))
      continue
    }

    const json = tryParseHookJson(result.stdout)
    if (!json) continue
    if (typeof json.systemMessage === 'string' && json.systemMessage.trim()) {
      systemMessages.push(json.systemMessage.trim())
    }
  }

  return { warnings, systemMessages }
}

export function __resetKodeHooksCacheForTests(): void {
  cache.clear()
  pluginHooksCache.clear()
  sessionStartCache.clear()
}
