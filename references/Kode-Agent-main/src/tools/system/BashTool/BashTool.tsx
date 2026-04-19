import { statSync } from 'fs'
import { EOL } from 'os'
import { isAbsolute, relative, resolve } from 'path'
import * as React from 'react'
import { z } from 'zod'
import { FallbackToolUseRejectedMessage } from '@components/FallbackToolUseRejectedMessage'
import { PRODUCT_NAME } from '@constants/product'
import { Tool, ValidationResult, ToolUseContext } from '@tool'
import { splitCommand } from '@utils/commands'
import { isInDirectory } from '@utils/fs/file'
import { logError } from '@utils/log'
import { createAssistantMessage } from '@utils/messages'
import { BunShell } from '@utils/bun/shell'
import { getBunShellSandboxPlan } from '@utils/sandbox/bunShellSandboxPlan'
import { ensureSandboxNetworkInfrastructure } from '@utils/sandbox/sandboxNetworkInfrastructure'
import { getCwd, getOriginalCwd } from '@utils/state'
import { decideSystemSandboxForBashTool } from '@utils/sandbox/systemSandbox'
import { isBashCommandReadOnly } from '@utils/permissions/bashReadOnly'
import { getBashDestructiveCommandBlock } from '@utils/sandbox/destructiveCommandGuard'
import { getTaskOutputFilePath } from '@utils/log/taskOutputStore'
import {
  formatBashLlmGateBlockMessage,
  runBashLlmSafetyGate,
} from './llmSafetyGate'
import BashToolResultMessage from './BashToolResultMessage'
import { BashToolRunInBackgroundOverlay } from './BashToolRunInBackgroundOverlay'
import { DEFAULT_TIMEOUT_MS, getBashToolPrompt } from './prompt'
import { formatOutput, getCommandFilePaths } from './utils'
import { getCommandSource, type CommandSource } from './commandSource'
import { WebFetchTool } from '@tools/network/WebFetchTool/WebFetchTool'
import { WebFetchPermissionRequest } from '@components/permissions/web-fetch-permission-request/WebFetchPermissionRequest'

function formatDuration(ms: number): string {
  if (ms < 60_000) {
    if (ms === 0) return '0s'
    if (ms < 1) return `${(ms / 1000).toFixed(1)}s`
    return `${Math.round(ms / 1000).toString()}s`
  }

  let hours = Math.floor(ms / 3_600_000)
  let minutes = Math.floor((ms % 3_600_000) / 60_000)
  let seconds = Math.round((ms % 60_000) / 1000)

  if (seconds === 60) {
    seconds = 0
    minutes++
  }
  if (minutes === 60) {
    minutes = 0
    hours++
  }

  if (hours > 0) return `${hours}h ${minutes}m ${seconds}s`
  if (minutes > 0) return `${minutes}m ${seconds}s`
  return `${seconds}s`
}

function normalizeLineEndings(text: string): string {
  return text.replace(/\r\n/g, '\n').replace(/\r/g, '\n')
}

function countNewlines(text: string): number {
  let count = 0
  for (let i = 0; i < text.length; i++) {
    if (text[i] === '\n') count++
  }
  return count
}

export const inputSchema = z.strictObject({
  command: z.string().describe('The command to execute'),
  timeout: z
    .number()
    .optional()
    .describe('Optional timeout in milliseconds (max 600000)'),
  description: z
    .string()
    .optional()
    .describe(
      `Clear, concise description of what this command does in 5-10 words, in active voice. Examples:
Input: ls
Output: List files in current directory

Input: git status
Output: Show working tree status

Input: npm install
Output: Install package dependencies

Input: mkdir foo
Output: Create directory 'foo'`,
    ),
  run_in_background: z
    .boolean()
    .optional()
    .describe(
      'Set to true to run this command in the background. Use TaskOutput to read the output later.',
    ),
  dangerouslyDisableSandbox: z
    .boolean()
    .optional()
    .describe(
      'Set this to true to dangerously override sandbox mode and run commands without sandboxing.',
    ),
})

type In = typeof inputSchema
export type Out = {
  stdout: string
  stdoutLines: number
  stderr: string
  stderrLines: number
  interrupted: boolean
  bashId?: string
  backgroundTaskId?: string
}

export const BashTool = {
  name: 'Bash',
  cachedDescription: 'Run shell command',
  async description(input?: z.infer<typeof inputSchema>) {
    return input?.description || 'Run shell command'
  },
  async prompt() {
    return getBashToolPrompt()
  },
  isReadOnly(input?: z.infer<typeof inputSchema>) {
    if (!input || typeof input.command !== 'string') return false
    return isBashCommandReadOnly(input.command)
  },
  isConcurrencySafe(input?: z.infer<typeof inputSchema>) {
    return this.isReadOnly(input)
  },
  inputSchema,
  userFacingName(input?: z.infer<typeof inputSchema>) {
    if (!input) return 'Bash'

    const raw =
      process.env.KODE_BASH_SANDBOX_SHOW_INDICATOR ??
      process.env.CLAUDE_CODE_BASH_SANDBOX_SHOW_INDICATOR
    const showIndicator = raw
      ? ['1', 'true', 'yes', 'on'].includes(raw.trim().toLowerCase())
      : false
    if (!showIndicator) return 'Bash'

    const plan = getBunShellSandboxPlan({
      command: input.command,
      dangerouslyDisableSandbox: input.dangerouslyDisableSandbox === true,
    })
    return plan.willSandbox ? 'SandboxedBash' : 'Bash'
  },
  async isEnabled() {
    return true
  },
  needsPermissions(): boolean {
    return true
  },
  async validateInput(
    { command, timeout, dangerouslyDisableSandbox },
    context?: ToolUseContext,
  ): Promise<ValidationResult> {
    if (timeout !== undefined) {
      if (!Number.isFinite(timeout) || timeout < 0) {
        return {
          result: false,
          message: `Invalid timeout: ${timeout}. Timeout must be a non-negative number of milliseconds.`,
        }
      }
      if (timeout > 600_000) {
        return {
          result: false,
          message: `Invalid timeout: ${timeout}. Maximum allowed timeout is 600000ms.`,
        }
      }
    }

    const source = (context as any)?.commandSource || 'agent_call'
    const isUserMode = source === 'user_bash_mode'
    const safeMode = Boolean(context?.safeMode ?? context?.options?.safeMode)

    if (
      dangerouslyDisableSandbox === true &&
      safeMode &&
      source === 'agent_call'
    ) {
      return {
        result: false,
        message: 'Sandbox cannot be disabled while safe mode is enabled.',
      }
    }
    const commands = splitCommand(command)

    for (const cmd of commands) {
      const parts = cmd.split(' ')
      const baseCmd = parts[0]

      if (baseCmd === 'cd' && parts[1]) {
        if (isUserMode) {
          continue
        }

        const targetDir = parts[1]!.replace(/^['"]|['"]$/g, '')
        const fullTargetDir = isAbsolute(targetDir)
          ? targetDir
          : resolve(getCwd(), targetDir)
        if (
          !isInDirectory(
            relative(getOriginalCwd(), fullTargetDir),
            relative(getCwd(), getOriginalCwd()),
          )
        ) {
          return {
            result: false,
            message: `ERROR: cd to '${fullTargetDir}' was blocked. For security, ${PRODUCT_NAME} may only change directories to child directories of the original working directory (${getOriginalCwd()}) for this session.`,
          }
        }
      }
    }

    return { result: true }
  },
  renderToolUseMessage(
    { command, run_in_background, description, timeout },
    options?: { verbose: boolean },
  ) {
    const verbose = Boolean(options?.verbose)
    const trimmedDescription = (description?.trim() || '').trim()
    const effectiveTimeout = timeout ?? DEFAULT_TIMEOUT_MS
    const timeoutSuffix = ` (timeout=${formatDuration(effectiveTimeout)})`
    const bgSuffix = run_in_background ? ' [background]' : ''
    const withDescription = (base: string): string => {
      if (!verbose || !trimmedDescription) return base
      const maxLen = 160
      const shown =
        trimmedDescription.length > maxLen
          ? `${trimmedDescription.slice(0, maxLen - 1)}…`
          : trimmedDescription
      return `${base} — ${shown}`
    }

    if (command.includes("\"$(cat <<'EOF'")) {
      const match = command.match(
        /^(.*?)"?\$\(cat <<'EOF'\n([\s\S]*?)\n\s*EOF\n\s*\)"(.*)$/,
      )
      if (match && match[1] && match[2]) {
        const prefix = match[1]
        const content = match[2]
        const suffix = match[3] || ''
        const cleaned = `${prefix.trim()} "${content.trim()}"${suffix.trim()}`
        const base = `${cleaned}${bgSuffix}${timeoutSuffix}`
        return withDescription(base.trim())
      }
    }

    const base = `${command}${bgSuffix}${timeoutSuffix}`
    return withDescription(base.trim())
  },
  renderToolUseRejectedMessage() {
    return <FallbackToolUseRejectedMessage />
  },

  renderToolResultMessage(content) {
    return <BashToolResultMessage content={content} verbose={false} />
  },
  renderResultForAssistant({
    interrupted,
    stdout,
    stderr,
    bashId,
    backgroundTaskId,
  }) {
    let trimmedStdout = stdout
    if (trimmedStdout) {
      trimmedStdout = trimmedStdout.replace(/^(\s*\n)+/, '')
      trimmedStdout = trimmedStdout.trimEnd()
    }

    let trimmedStderr = stderr.trim()
    if (interrupted) {
      if (trimmedStderr) trimmedStderr += EOL
      trimmedStderr += '<error>Command was aborted before completion</error>'
    }

    const id = backgroundTaskId ?? bashId
    const backgroundLine = id
      ? `Command running in background with ID: ${id}. Output is being written to: ${getTaskOutputFilePath(id)}`
      : ''

    return [trimmedStdout, trimmedStderr, backgroundLine]
      .filter(Boolean)
      .join('\n')
  },
  async *call(
    {
      command,
      timeout = DEFAULT_TIMEOUT_MS,
      run_in_background,
      dangerouslyDisableSandbox,
      description,
    },
    context,
  ) {
    const { abortController, readFileTimestamps } = context
    const setToolJSX = (context as any).setToolJSX as
      | ((
          jsx: {
            jsx: React.ReactNode | null
            shouldHidePromptInput: boolean
          } | null,
        ) => void)
      | undefined
    let stdout = ''
    let stderr = ''

    const commandSource = getCommandSource(context as any)
    const safeMode = Boolean(context?.safeMode ?? context?.options?.safeMode)
    const userPrompt =
      typeof context?.options?.lastUserPrompt === 'string'
        ? context.options.lastUserPrompt.trim()
        : ''
    const commandDescription =
      typeof description === 'string' ? description.trim() : ''

    const destructiveBlock = getBashDestructiveCommandBlock({
      command,
      cwd: getCwd(),
      originalCwd: getOriginalCwd(),
      commandSource,
      platform: process.platform,
    })
    if (destructiveBlock) {
      const data: Out = {
        stdout: '',
        stdoutLines: 0,
        stderr: destructiveBlock.message,
        stderrLines: destructiveBlock.message.split(/\r?\n/).length,
        interrupted: false,
      }
      yield {
        type: 'result',
        resultForAssistant: this.renderResultForAssistant(data),
        data,
      }
      return
    }

    const systemSandboxDecision = decideSystemSandboxForBashTool({
      safeMode,
      commandSource,
      dangerouslyDisableSandbox: dangerouslyDisableSandbox === true,
    })

    const systemSandboxOptions = systemSandboxDecision.enabled
      ? {
          enabled: true,
          require: systemSandboxDecision.required,
          allowNetwork: systemSandboxDecision.allowNetwork,
          writableRoots: [getOriginalCwd()],
          chdir: getCwd(),
        }
      : undefined

    const sandboxPlan = getBunShellSandboxPlan({
      command,
      dangerouslyDisableSandbox: dangerouslyDisableSandbox === true,
      toolUseContext: context as any,
    })

    if (sandboxPlan.shouldBlockUnsandboxedCommand) {
      const data: Out = {
        stdout: '',
        stdoutLines: 0,
        stderr:
          'This command must run in the sandbox, but sandboxed execution is not available.',
        stderrLines: 1,
        interrupted: false,
      }
      yield {
        type: 'result',
        resultForAssistant: this.renderResultForAssistant(data),
        data,
      }
      return
    }

    let sandboxOptions =
      sandboxPlan.settings.enabled === true
        ? sandboxPlan.bunShellSandboxOptions
        : systemSandboxOptions

    const bashLlmGateQuery =
      typeof (context as any)?.options?.bashLlmGateQuery === 'function'
        ? ((context as any).options.bashLlmGateQuery as any)
        : undefined

    const llmGateResult = await runBashLlmSafetyGate({
      command,
      userPrompt,
      description: commandDescription,
      platform: process.platform,
      commandSource,
      safeMode,
      runInBackground: run_in_background === true,
      willSandbox: Boolean(sandboxOptions?.enabled),
      sandboxRequired: Boolean(
        sandboxOptions?.enabled && sandboxOptions.require,
      ),
      cwd: getCwd(),
      originalCwd: getOriginalCwd(),
      parentAbortSignal: abortController.signal,
      query: bashLlmGateQuery,
    })

    if (llmGateResult.decision === 'block') {
      const message = formatBashLlmGateBlockMessage(llmGateResult.verdict)
      const data: Out = {
        stdout: '',
        stdoutLines: 0,
        stderr: message,
        stderrLines: message.split(/\r?\n/).length,
        interrupted: false,
      }
      yield {
        type: 'result',
        resultForAssistant: this.renderResultForAssistant(data),
        data,
      }
      return
    }

    if (llmGateResult.decision === 'error' && !llmGateResult.canFailOpen) {
      const userHint =
        llmGateResult.errorType === 'api'
          ? 'Fix your model connection (API key / network) and retry.'
          : llmGateResult.errorType === 'timeout'
            ? 'LLM intent gate timed out. Retry.'
            : 'LLM intent gate returned invalid output. Retry.'
      const userMessage = [
        llmGateResult.willSandbox
          ? 'Blocked: LLM intent gate failed (cannot verify command intent).'
          : 'Blocked: LLM intent gate failed and command would run unsandboxed.',
        `Error: ${llmGateResult.error}`,
        '',
        userHint,
      ]
        .filter(Boolean)
        .join('\n')

      const assistantMessage = [
        llmGateResult.willSandbox
          ? 'Blocked: LLM intent gate unavailable.'
          : 'Blocked: LLM intent gate unavailable (command would run unsandboxed).',
        `Error: ${llmGateResult.error}`,
        llmGateResult.errorType === 'invalid_output'
          ? 'Hint: Retry and include a short `description` for the Bash command.'
          : llmGateResult.errorType === 'timeout'
            ? 'Hint: Retry (or switch to a faster main model).'
            : '',
      ]
        .filter(Boolean)
        .join('\n')
      const data: Out = {
        stdout: '',
        stdoutLines: 0,
        stderr: userMessage,
        stderrLines: userMessage.split(/\r?\n/).length,
        interrupted: false,
      }
      yield {
        type: 'result',
        resultForAssistant: assistantMessage,
        data,
      }
      return
    }

    if (
      sandboxPlan.willSandbox &&
      sandboxOptions?.enabled === true &&
      'needsNetworkRestriction' in sandboxOptions &&
      (sandboxOptions.__platformOverride ?? process.platform) === 'darwin' &&
      sandboxOptions.needsNetworkRestriction === true
    ) {
      const mode = context?.options?.toolPermissionContext?.mode ?? 'default'
      const shouldAvoidPermissionPrompts = Boolean(
        context?.options?.shouldAvoidPermissionPrompts,
      )

      const ports = await ensureSandboxNetworkInfrastructure({
        runtimeConfig: sandboxPlan.runtimeConfig,
        permissionCallback: async ({ host, port }) => {
          if (mode === 'acceptEdits' || mode === 'bypassPermissions')
            return true
          if (mode === 'dontAsk' || shouldAvoidPermissionPrompts) return false
          if (!setToolJSX) return false
          if (abortController.signal.aborted) return false

	          const hostForUrl =
	            host.includes(':') && !host.startsWith('[') ? `[${host}]` : host
	          const url = `http://${hostForUrl}:${port}/`

	          return await new Promise<boolean>(resolve => {
	            const assistantMessage = createAssistantMessage('')
	            if (context.messageId) {
	              ;(assistantMessage.message as any).id = context.messageId
            }

            const toolUseConfirm: any = {
              assistantMessage,
              tool: WebFetchTool,
              description: 'Network request outside of sandbox',
              input: { url },
              commandPrefix: null,
              toolUseContext: context,
              suggestions: undefined,
              riskScore: null,
              onAbort() {
                resolve(false)
              },
              onAllow() {
                resolve(true)
              },
              onReject() {
                resolve(false)
              },
            }

            setToolJSX({
              jsx: (
                <WebFetchPermissionRequest
                  toolUseConfirm={toolUseConfirm}
                  onDone={() => setToolJSX(null)}
                  verbose={Boolean(context?.options?.verbose)}
                />
              ),
              shouldHidePromptInput: true,
            })
          })
        },
      })

      sandboxOptions = {
        ...sandboxOptions,
        httpProxyPort: ports.httpProxyPort,
        socksProxyPort: ports.socksProxyPort,
      }
    }

    if (abortController.signal.aborted) {
      const data: Out = {
        stdout: '',
        stdoutLines: 0,
        stderr: 'Command cancelled before execution',
        stderrLines: 1,
        interrupted: true,
      }

      yield {
        type: 'result',
        resultForAssistant: this.renderResultForAssistant(data),
        data,
      }
      return
    }

    try {
      if (run_in_background) {
        const { bashId } = BunShell.getInstance().execInBackground(
          command,
          timeout,
          {
            sandbox: sandboxOptions,
          },
        )
        const data: Out = {
          stdout: '',
          stdoutLines: 0,
          stderr: '',
          stderrLines: 0,
          interrupted: false,
          bashId,
          backgroundTaskId: bashId,
        }
        yield {
          type: 'result',
          resultForAssistant: this.renderResultForAssistant(data),
          data,
        }
        return
      }

      const startedAt = Date.now()
      const PROGRESS_INITIAL_DELAY_MS = 2000
      const PROGRESS_INTERVAL_MS = 1000
      const PROGRESS_MAX_LINES = 5
      const PROGRESS_TAIL_MAX_CHARS = 100_000

      let combinedTail = ''
      let totalNewlines = 0
      let sawAnyOutput = false

      const onChunk = (chunk: string) => {
        if (!chunk) return
        sawAnyOutput = true
        totalNewlines += countNewlines(chunk)
        combinedTail += chunk
        if (combinedTail.length > PROGRESS_TAIL_MAX_CHARS) {
          combinedTail = combinedTail.slice(-PROGRESS_TAIL_MAX_CHARS)
        }
      }

      const exec = BunShell.getInstance().execPromotable(
        command,
        abortController.signal,
        timeout,
        {
          sandbox: sandboxOptions,
          onStdoutChunk: onChunk,
          onStderrChunk: onChunk,
        },
      )

      let backgroundRequested = false
      let resolveBackground: ((bashId: string) => void) | null = null
      const backgroundPromise = new Promise<string>(resolve => {
        resolveBackground = resolve
      })

      const requestBackground = () => {
        if (backgroundRequested) return
        backgroundRequested = true
        const promoted = exec.background()
        if (!promoted) return
        resolveBackground?.(promoted.bashId)
      }

      const resultPromise = exec.result

      const buildProgressText = (): string => {
        const elapsedMs = Date.now() - startedAt
        const time = `(${formatDuration(elapsedMs)})`

        const normalized = normalizeLineEndings(combinedTail).trim()
        const lines = normalized.length
          ? normalized.split('\n').filter(line => line.length > 0)
          : []

        if (lines.length === 0) {
          return `Running… ${time}`
        }

        const shownLines = lines.slice(-PROGRESS_MAX_LINES)
        const totalLines = sawAnyOutput ? totalNewlines + 1 : 0
        const extraLines = Math.max(0, totalLines - PROGRESS_MAX_LINES)

        const footerParts: string[] = []
        if (extraLines > 0) {
          footerParts.push(
            `+${extraLines} more line${extraLines === 1 ? '' : 's'}`,
          )
        }
        footerParts.push(time)

        return `${shownLines.join('\n')}\n${footerParts.join(' ')}`
      }

      let nextTickAt = startedAt + PROGRESS_INITIAL_DELAY_MS
      let overlayShown = false
      while (true) {
        const now = Date.now()
        const waitMs = Math.max(0, nextTickAt - now)
        const race = await Promise.race([
          resultPromise.then(r => ({ kind: 'done' as const, r })),
          backgroundPromise.then(bashId => ({
            kind: 'background' as const,
            bashId,
          })),
          new Promise<{ kind: 'tick' }>(resolve =>
            setTimeout(() => resolve({ kind: 'tick' }), waitMs),
          ),
        ])

        if (race.kind === 'background') {
          const data: Out = {
            stdout: '',
            stdoutLines: 0,
            stderr: '',
            stderrLines: 0,
            interrupted: false,
            bashId: race.bashId,
            backgroundTaskId: race.bashId,
          }

          yield {
            type: 'result',
            resultForAssistant: this.renderResultForAssistant(data),
            data,
          }
          return
        }

        if (race.kind === 'done') {
          const result = race.r

          stdout += (result.stdout || '').trim() + EOL
          stderr += (result.stderr || '').trim() + EOL
          if (result.code !== 0) {
            stderr += `Exit code ${result.code}`
          }

          if (!isInDirectory(getCwd(), getOriginalCwd())) {
            await BunShell.getInstance().setCwd(getOriginalCwd())
            stderr = `${stderr.trim()}${EOL}Shell cwd was reset to ${getOriginalCwd()}`
          }

          if (process.env.NODE_ENV !== 'test') {
            getCommandFilePaths(command, stdout).then(filePaths => {
              for (const filePath of filePaths) {
                const fullFilePath = isAbsolute(filePath)
                  ? filePath
                  : resolve(getCwd(), filePath)

                try {
                  readFileTimestamps[fullFilePath] =
                    statSync(fullFilePath).mtimeMs
                } catch (e) {
                  logError(e)
                }
              }
            })
          }

          const { totalLines: stdoutLines, truncatedContent: stdoutContent } =
            formatOutput(stdout.trim())
          const { totalLines: stderrLines, truncatedContent: stderrContent } =
            formatOutput(stderr.trim())

          const data: Out = {
            stdout: stdoutContent,
            stdoutLines,
            stderr: stderrContent,
            stderrLines,
            interrupted: result.interrupted,
          }

          yield {
            type: 'result',
            resultForAssistant: this.renderResultForAssistant(data),
            data,
          }
          return
        }

        if (
          !overlayShown &&
          setToolJSX &&
          Date.now() - startedAt >= PROGRESS_INITIAL_DELAY_MS
        ) {
          overlayShown = true
          setToolJSX({
            jsx: (
              <BashToolRunInBackgroundOverlay
                onBackground={requestBackground}
              />
            ),
            shouldHidePromptInput: false,
          })
        }

        const text = buildProgressText()
        yield {
          type: 'progress',
          content: createAssistantMessage(
            `<tool-progress>${text}</tool-progress>`,
          ),
        }

        nextTickAt = Date.now() + PROGRESS_INTERVAL_MS
      }
    } catch (error) {
      const isAborted = abortController.signal.aborted
      const errorMessage = isAborted
        ? 'Command was cancelled by user'
        : `Command failed: ${error instanceof Error ? error.message : String(error)}`

      const data: Out = {
        stdout: stdout.trim(),
        stdoutLines: stdout.split('\n').length,
        stderr: errorMessage,
        stderrLines: 1,
        interrupted: isAborted,
      }

      yield {
        type: 'result',
        resultForAssistant: this.renderResultForAssistant(data),
        data,
      }
    } finally {
      setToolJSX?.(null)
    }
  },
} satisfies Tool<In, Out>
