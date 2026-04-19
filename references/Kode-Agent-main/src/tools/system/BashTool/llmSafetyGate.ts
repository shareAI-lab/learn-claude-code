import { randomUUID } from 'crypto'
import { mkdirSync, writeFileSync } from 'fs'
import { join } from 'path'
import { CACHE_PATHS, dateToFilename, logError } from '@utils/log'
import type { CommandSource } from './commandSource'
import {
  getBashGateFindings,
  shouldReviewBashCommand,
  type BashGateFinding,
} from './bashGateRules'

export type BashLlmGateVerdict = {
  action: 'allow' | 'block'
  summary: string
}

const DEFAULT_GATE_TIMEOUT_MS = 300_000
const DEFAULT_GATE_STOP_SEQUENCES = ['</final>']

export type BashLlmGateErrorType =
  | 'api'
  | 'timeout'
  | 'invalid_output'
  | 'unknown'

function parseVerdictFromText(text: string): BashLlmGateVerdict {
  const trimmed = text.trim()
  if (!trimmed) throw new Error('LLM gate produced empty output')

  if (/^allow$/i.test(trimmed)) return { action: 'allow', summary: '' }
  if (/^block$/i.test(trimmed)) return { action: 'block', summary: '' }

  const finals = Array.from(
    trimmed.matchAll(/<final\b[^>]*>[\s\S]*?<\/final>/gi),
  )
  const xml = finals.length > 0 ? finals[finals.length - 1]![0]! : trimmed
  const decisionTag = xml.match(/<decision>\s*(allow|block)\s*<\/decision>/i)
  if (decisionTag) {
    const action = decisionTag[1]!.trim().toLowerCase() as 'allow' | 'block'
    const reasonTag = xml.match(/<reason>\s*([^<]{0,180})\s*<\/reason>/i)
    return { action, summary: (reasonTag?.[1] ?? '').trim() }
  }

  const nonEmptyLines = trimmed
    .split(/\r?\n/)
    .map(l => l.trim())
    .filter(Boolean)
  for (let i = nonEmptyLines.length - 1; i >= 0; i--) {
    const line = nonEmptyLines[i]!
    const m = line.match(
      /^(?:[-*•]|\d+\.)?\s*(allow|block)\s*(?:(?:[:\\-]\s*)(.{0,200}))?\s*$/i,
    )
    if (!m) continue
    const action = m[1]!.toLowerCase() as 'allow' | 'block'
    const summary = (m[2] ?? '').trim().slice(0, 140)
    return { action, summary }
  }

  const bareDecisionTag = trimmed.match(
    /<decision>\s*(allow|block)\s*<\/decision>/i,
  )
  if (bareDecisionTag) {
    const action = bareDecisionTag[1]!.trim().toLowerCase() as 'allow' | 'block'
    const reasonTag = trimmed.match(/<reason>\s*([^<]{0,180})\s*<\/reason>/i)
    const summary = (reasonTag?.[1] ?? '').trim()
    return { action, summary }
  }

  const preview = trimmed.length > 240 ? `${trimmed.slice(0, 240)}…` : trimmed
  throw new Error(
    `Unable to parse LLM gate verdict. Output preview: ${preview}`,
  )
}

function buildGateSystemPrompt(): string[] {
  return [
    [
      'You are a safety + intent-alignment reviewer for a coding agent about to run a shell command on the user machine.',
      'A local rule pool produced one or more risk findings. Your job is to decide whether to ALLOW or BLOCK executing the command now.',
      '',
      'You must evaluate BOTH:',
      '1) Safety of the behavior (risk of data loss, irreversible changes, privilege escalation, remote code execution, infra destruction).',
      '2) Alignment: does the command match the user request (USER_PROMPT) and the initiator description (DESCRIPTION)?',
      '',
      'Output (required): EXACTLY ONE LINE of XML and nothing else:',
      '<final><decision>allow|block</decision><reason>...</reason></final>',
      '- If allow: <reason> may be empty.',
      '- If block: <reason> is required (<=140 chars).',
      '',
      'No analysis. No markdown. No numbered lists.',
      '',
      'Few-shot examples (follow the output format strictly):',
      '',
      'Example A (rm, user asked to delete a temp file):',
      'USER_PROMPT: Remove the generated temp file',
      'DESCRIPTION: Delete temp output',
      'COMMAND: rm -f ./tmp/output.log',
      '<final><decision>allow</decision><reason></reason></final>',
      '',
      'Example B (rm -rf ., mismatch):',
      'USER_PROMPT: Check git status',
      'DESCRIPTION: Check repo state',
      'COMMAND: rm -rf .',
      '<final><decision>block</decision><reason>Destructive delete does not match the request</reason></final>',
      '',
      'Example C (git reset --hard, explicitly requested):',
      'USER_PROMPT: Discard my local changes and go back to HEAD',
      'DESCRIPTION: Reset working tree to HEAD',
      'COMMAND: git reset --hard',
      '<final><decision>allow</decision><reason></reason></final>',
      '',
      'Example D (git clean -fdx, unclear intent):',
      'USER_PROMPT: Run tests',
      'DESCRIPTION: Clean repository',
      'COMMAND: git clean -fdx',
      '<final><decision>block</decision><reason>Deletes untracked/ignored files; user did not request cleanup</reason></final>',
    ].join('\n'),
  ]
}

type GateQueryFn = (args: {
  systemPrompt: string[]
  userInput: string
  signal: AbortSignal
  model?: 'quick' | 'main'
}) => Promise<string>

function collectTextBlocks(content: any): string {
  if (typeof content === 'string') return content
  if (!Array.isArray(content)) return ''
  return content
    .flatMap((b: any) => {
      if (!b || typeof b !== 'object') return []
      if (b.type === 'text' && typeof b.text === 'string') return [b.text]
      if (b.type === 'thinking' && typeof b.thinking === 'string')
        return [b.thinking]
      if (
        (b.type === undefined || b.type === null) &&
        typeof (b as any).text === 'string'
      )
        return [(b as any).text]
      if (
        (b.type === undefined || b.type === null) &&
        typeof (b as any).thinking === 'string'
      )
        return [(b as any).thinking]
      return []
    })
    .join('\n')
}

function formatParseError(error: unknown): string {
  return error instanceof Error ? error.message : String(error)
}

async function defaultGateQuery(args: {
  systemPrompt: string[]
  userInput: string
  signal: AbortSignal
  model?: 'quick' | 'main'
}): Promise<string> {
  const { API_ERROR_MESSAGE_PREFIX, queryLLM } = await import('@services/llm')
  const messages: any[] = [
    {
      type: 'user',
      uuid: randomUUID(),
      message: { role: 'user', content: args.userInput },
    },
  ]

  const assistant = await queryLLM(
    messages as any,
    args.systemPrompt,
    0,
    [],
    args.signal,
    {
      safeMode: false,
      model: args.model ?? 'quick',
      prependCLISysprompt: false,
      stopSequences: DEFAULT_GATE_STOP_SEQUENCES,
    },
  )

  const text = collectTextBlocks((assistant as any)?.message?.content)
  const trimmed = text.trim()
  if ((assistant as any)?.isApiErrorMessage) {
    const preview = trimmed.length > 240 ? `${trimmed.slice(0, 240)}…` : trimmed
    throw new Error(`LLM gate model error: ${preview}`)
  }
  if (trimmed.startsWith(API_ERROR_MESSAGE_PREFIX)) {
    const preview = trimmed.length > 240 ? `${trimmed.slice(0, 240)}…` : trimmed
    throw new Error(`LLM gate model error: ${preview}`)
  }
  return text
}

function buildGateUserInput(params: {
  command: string
  userPrompt: string
  description: string
  findings: BashGateFinding[]
  platform: NodeJS.Platform
  commandSource: CommandSource
  safeMode: boolean
  runInBackground: boolean
  willSandbox: boolean
  sandboxRequired: boolean
  cwd: string
  originalCwd: string
}): string {
  const lines: string[] = []
  lines.push(
    'OUTPUT_FORMAT: <final><decision>allow|block</decision><reason>...</reason></final>',
  )
  lines.push('')
  lines.push('FINDINGS:')
  if (params.findings.length === 0) {
    lines.push('- (none)')
  } else {
    for (const f of params.findings.slice(0, 20)) {
      lines.push(
        `- [${f.code}] (${f.severity}/${f.category}) ${f.title}${f.evidence ? ` — ${f.evidence}` : ''}`,
      )
    }
    if (params.findings.length > 20) {
      lines.push(`- ... (${params.findings.length - 20} more)`)
    }
  }
  lines.push('')
  lines.push('USER_PROMPT:')
  lines.push(params.userPrompt.trim() ? params.userPrompt.trim() : '(none)')
  lines.push('')
  lines.push('DESCRIPTION:')
  lines.push(params.description.trim() ? params.description.trim() : '(none)')
  lines.push('')
  lines.push('COMMAND:')
  lines.push(params.command)
  lines.push('')
  lines.push('CONTEXT:')
  lines.push(`- commandSource: ${params.commandSource}`)
  lines.push(`- platform: ${params.platform}`)
  lines.push(`- safeMode: ${params.safeMode ? 'true' : 'false'}`)
  lines.push(`- runInBackground: ${params.runInBackground ? 'true' : 'false'}`)
  lines.push(`- sandbox.willSandbox: ${params.willSandbox ? 'true' : 'false'}`)
  lines.push(`- sandbox.required: ${params.sandboxRequired ? 'true' : 'false'}`)
  lines.push(`- cwd: ${params.cwd}`)
  lines.push(`- originalCwd: ${params.originalCwd}`)
  return lines.join('\n')
}

function writeGateFailureDump(args: {
  command: string
  userPrompt: string
  description: string
  findings: BashGateFinding[]
  input: string
  output?: string
  error: string
}): void {
  try {
    const dir = join(CACHE_PATHS.errors(), 'bash-llm-gate')
    mkdirSync(dir, { recursive: true })
    const filename = `${dateToFilename(new Date())}-${randomUUID()}.txt`
    const path = join(dir, filename)
    const body = [
      '=== Bash LLM gate failure ===',
      '',
      `error: ${args.error}`,
      '',
      '--- command ---',
      args.command,
      '',
      '--- description ---',
      args.description,
      '',
      '--- userPrompt ---',
      args.userPrompt,
      '',
      '--- findings ---',
      args.findings.length
        ? args.findings
            .map(
              f =>
                `[${f.code}] (${f.severity}/${f.category}) ${f.title}${f.evidence ? ` — ${f.evidence}` : ''}`,
            )
            .join('\n')
        : '(none)',
      '',
      '--- gate input ---',
      args.input,
      '',
      args.output !== undefined ? '--- gate output ---' : '',
      args.output ?? '',
      '',
    ]
      .filter(Boolean)
      .join('\n')
    writeFileSync(path, body, 'utf8')
  } catch {
  }
}

type GateAttemptOutput = {
  model: 'quick' | 'main'
  output: string
  error?: string
}

export async function runBashLlmSafetyGate(params: {
  command: string
  userPrompt: string
  description: string
  platform: NodeJS.Platform
  commandSource: CommandSource
  safeMode: boolean
  runInBackground: boolean
  willSandbox: boolean
  sandboxRequired: boolean
  cwd: string
  originalCwd: string
  parentAbortSignal?: AbortSignal
  query?: GateQueryFn
}): Promise<
  | { decision: 'allow'; verdict: BashLlmGateVerdict; fromCache: boolean }
  | { decision: 'block'; verdict: BashLlmGateVerdict; fromCache: boolean }
  | {
      decision: 'error'
      error: string
      errorType: BashLlmGateErrorType
      willSandbox: boolean
      canFailOpen: boolean
    }
  | { decision: 'disabled' }
> {
  const trimmedUserPrompt = params.userPrompt.trim()
  const trimmedDescription = params.description.trim()
  const findings = getBashGateFindings(params.command)
  const attemptOutputs: GateAttemptOutput[] = []

  if (!shouldReviewBashCommand(findings)) {
    return {
      decision: 'allow',
      verdict: { action: 'allow', summary: '' },
      fromCache: false,
    }
  }

  const abortController = new AbortController()
  const timeout = setTimeout(
    () => abortController.abort(),
    DEFAULT_GATE_TIMEOUT_MS,
  )
  const onAbort = () => abortController.abort()
  params.parentAbortSignal?.addEventListener('abort', onAbort, { once: true })

  try {
    const baseInput = buildGateUserInput({
      command: params.command,
      userPrompt: trimmedUserPrompt,
      description: trimmedDescription,
      findings,
      platform: params.platform,
      commandSource: params.commandSource,
      safeMode: params.safeMode,
      runInBackground: params.runInBackground,
      willSandbox: params.willSandbox,
      sandboxRequired: params.sandboxRequired,
      cwd: params.cwd,
      originalCwd: params.originalCwd,
    })
    const query = params.query ?? defaultGateQuery
    const attempts: Array<{ model: 'quick' | 'main' }> = [
      { model: 'quick' },
      { model: 'main' },
      { model: 'main' },
    ]

    let lastError: unknown = null
    for (const attempt of attempts) {
      try {
        const output = await query({
          systemPrompt: buildGateSystemPrompt(),
          userInput: baseInput,
          signal: abortController.signal,
          model: attempt.model,
        })
        attemptOutputs.push({ model: attempt.model, output })
        const verdict = parseVerdictFromText(output)
        return {
          decision: verdict.action === 'allow' ? 'allow' : 'block',
          verdict,
          fromCache: false,
        }
      } catch (e) {
        lastError = e
        attemptOutputs.push({
          model: attempt.model,
          output: '',
          error: formatParseError(e),
        })
      }
    }
    throw lastError ?? new Error('LLM gate produced no verdict')
  } catch (error) {
    const errorStr = formatParseError(error)
    const errorType: BashLlmGateErrorType = abortController.signal.aborted
      ? 'timeout'
      : errorStr.startsWith('LLM gate model error:')
        ? 'api'
        : errorStr.startsWith('LLM gate produced empty output') ||
            errorStr.startsWith('Unable to parse LLM gate verdict')
          ? 'invalid_output'
          : 'unknown'
    logError(`Bash LLM gate error: ${errorStr}`)
    const input = buildGateUserInput({
      command: params.command,
      userPrompt: trimmedUserPrompt,
      description: trimmedDescription,
      findings,
      platform: params.platform,
      commandSource: params.commandSource,
      safeMode: params.safeMode,
      runInBackground: params.runInBackground,
      willSandbox: params.willSandbox,
      sandboxRequired: params.sandboxRequired,
      cwd: params.cwd,
      originalCwd: params.originalCwd,
    })
    const output =
      attemptOutputs.length > 0
        ? attemptOutputs
            .map(o => {
              const header = `--- model: ${o.model} ---`
              const body = o.error ? `error: ${o.error}` : o.output
              return `${header}\n${body}`
            })
            .join('\n\n')
        : undefined
    writeGateFailureDump({
      command: params.command,
      userPrompt: trimmedUserPrompt,
      description: trimmedDescription,
      findings,
      input,
      ...(output ? { output } : {}),
      error: errorStr,
    })
    return {
      decision: 'error',
      error: errorStr,
      errorType,
      willSandbox: params.willSandbox,
      canFailOpen: false,
    }
  } finally {
    clearTimeout(timeout)
    params.parentAbortSignal?.removeEventListener('abort', onAbort)
  }
}

export function formatBashLlmGateBlockMessage(
  verdict: BashLlmGateVerdict,
): string {
  const lines: string[] = []
  const summary = verdict.summary?.trim()
  lines.push(
    `Blocked by LLM intent gate: ${summary ? summary : 'No reason provided by gate model'}`,
  )
  return lines.join('\n')
}
