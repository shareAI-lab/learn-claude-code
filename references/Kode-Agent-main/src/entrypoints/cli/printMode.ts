import { addToHistory } from '@history'
import { hasPermissionsToUseTool } from '@permissions'
import { dateToFilename } from '@utils/log'
import { createStdioCanUseTool } from './stdio/canUseTool'
import { createPrintModeControlRequestHandler } from './stdio/controlRequestHandler'
import { runPrintModeStreamJsonSession } from './stdio/streamJsonSession'
import { createPrintModeStructuredStdio } from './stdio/structuredStdio'

export type RunPrintModeArgs = {
  prompt: string | undefined
  stdinContent: string
  inputPrompt: string

  cwd: string
  safe?: boolean
  verbose?: boolean

  outputFormat?: string
  inputFormat?: string
  jsonSchema?: string
  permissionPromptTool?: string | null
  replayUserMessages?: boolean

  cliTools?: unknown
  tools: any[]
  commands: any[]
  ask: (args: any) => Promise<{ resultText: string }>

  initialMessages?: any[]
  sessionPersistence?: boolean

  systemPromptOverride?: string
  appendSystemPrompt?: string
  disableSlashCommands?: boolean

  allowedTools?: unknown
  disallowedTools?: unknown
  addDir?: unknown
  permissionMode?: string
  dangerouslySkipPermissions?: boolean
  allowDangerouslySkipPermissions?: boolean

  model?: string
  mcpClients: any[]
}

export async function runPrintMode({
  prompt,
  stdinContent,
  inputPrompt,
  cwd,
  safe,
  verbose,
  outputFormat,
  inputFormat,
  jsonSchema,
  permissionPromptTool,
  replayUserMessages,
  cliTools,
  tools,
  commands,
  ask,
  initialMessages,
  sessionPersistence,
  systemPromptOverride,
  appendSystemPrompt,
  disableSlashCommands,
  allowedTools,
  disallowedTools,
  addDir,
  permissionMode,
  dangerouslySkipPermissions,
  allowDangerouslySkipPermissions,
  model,
  mcpClients,
}: RunPrintModeArgs): Promise<void> {
  const normalizedOutputFormat = String(outputFormat || 'text')
    .toLowerCase()
    .trim()
  const normalizedInputFormat = String(inputFormat || 'text')
    .toLowerCase()
    .trim()

  if (!['text', 'stream-json'].includes(normalizedInputFormat)) {
    console.error(
      `Error: Invalid --input-format "${inputFormat}". Expected one of: text, stream-json`,
    )
    process.exit(1)
  }

  if (!['text', 'json', 'stream-json'].includes(normalizedOutputFormat)) {
    console.error(
      `Error: Invalid --output-format "${outputFormat}". Expected one of: text, json, stream-json`,
    )
    process.exit(1)
  }

  if (normalizedOutputFormat === 'stream-json' && !verbose) {
    console.error(
      'Error: When using --print, --output-format=stream-json requires --verbose',
    )
    process.exit(1)
  }

  const normalizedPermissionPromptTool = permissionPromptTool
    ? String(permissionPromptTool).trim()
    : null

  if (normalizedPermissionPromptTool) {
    if (normalizedPermissionPromptTool !== 'stdio') {
      console.error(
        `Error: Unsupported --permission-prompt-tool "${normalizedPermissionPromptTool}". Only "stdio" is supported in Kode right now.`,
      )
      process.exit(1)
    }
    if (normalizedInputFormat !== 'stream-json') {
      console.error(
        'Error: --permission-prompt-tool=stdio requires --input-format=stream-json',
      )
      process.exit(1)
    }
    if (normalizedOutputFormat !== 'stream-json') {
      console.error(
        'Error: --permission-prompt-tool=stdio requires --output-format=stream-json',
      )
      process.exit(1)
    }
  }

  if (
    normalizedInputFormat === 'stream-json' &&
    normalizedOutputFormat !== 'stream-json'
  ) {
    console.error(
      'Error: --input-format=stream-json requires --output-format=stream-json',
    )
    process.exit(1)
  }

  if (replayUserMessages) {
    if (
      normalizedInputFormat !== 'stream-json' ||
      normalizedOutputFormat !== 'stream-json'
    ) {
      console.error(
        'Error: --replay-user-messages requires --input-format=stream-json and --output-format=stream-json',
      )
      process.exit(1)
    }
  }

  if (normalizedInputFormat === 'stream-json') {
    if (prompt) {
      console.error(
        'Error: --input-format=stream-json cannot be used with a prompt argument',
      )
      process.exit(1)
    }
    if (stdinContent) {
      console.error(
        'Error: --input-format=stream-json cannot be used with stdin prompt text',
      )
      process.exit(1)
    }
  } else {
    if (!inputPrompt) {
      console.error(
        'Error: Input must be provided either through stdin or as a prompt argument when using --print',
      )
      process.exit(1)
    }
  }

  const toolsForPrint = (() => {
    if (!cliTools) return tools
    const raw = Array.isArray(cliTools) ? cliTools : [cliTools]
    const flattened = raw
      .flatMap(v => String(v ?? '').split(','))
      .map(v => v.trim())
    if (flattened.length === 0) return tools

    if (flattened.length === 1 && flattened[0] === '') return []
    if (flattened.length === 1 && flattened[0] === 'default') return tools

    const wanted = new Set(flattened.filter(v => v && v !== 'default'))
    const unknown = [...wanted].filter(
      name => !tools.some(t => t.name === name),
    )
    if (unknown.length > 0) {
      console.error(`Error: Unknown tool(s) in --tools: ${unknown.join(', ')}`)
      process.exit(1)
    }

    return tools.filter(t => wanted.has(t.name))
  })()

  if (normalizedOutputFormat === 'text') {
    addToHistory(inputPrompt)
    const { resultText: response } = await ask({
      commands,
      hasPermissionsToUseTool,
      messageLogName: dateToFilename(new Date()),
      prompt: inputPrompt,
      cwd,
      tools: toolsForPrint,
      safeMode: safe,
      initialMessages,
      persistSession: sessionPersistence !== false,
    })
    process.stdout.write(`${response}\n`)
    process.exit(0)
  }

  const { createUserMessage } = await import('@utils/messages')
  const { getSystemPrompt } = await import('@constants/prompts')
  const { getContext } = await import('@context')
  const { getTotalCost } = await import('@costTracker')
  const { query } = await import('@query')
  const { getKodeAgentSessionId } =
    await import('@utils/protocol/kodeAgentSessionId')
  const { kodeMessageToSdkMessage, makeSdkInitMessage, makeSdkResultMessage } =
    await import('@utils/protocol/kodeAgentStreamJson')
  const { KodeAgentStructuredStdio } =
    await import('@utils/protocol/kodeAgentStructuredStdio')
  const {
    loadToolPermissionContextFromDisk,
    persistToolPermissionUpdateToDisk,
  } = await import('@utils/permissions/toolPermissionSettings')
  const { applyToolPermissionContextUpdates } =
    await import('@kode-types/toolPermissionContext')

  const sessionIdForSdk = getKodeAgentSessionId()
  const startedAt = Date.now()
  const sdkMessages: any[] = []

  const baseSystemPrompt =
    typeof systemPromptOverride === 'string' && systemPromptOverride.trim()
      ? [systemPromptOverride]
      : await getSystemPrompt({ disableSlashCommands })
  const systemPrompt =
    typeof appendSystemPrompt === 'string' && appendSystemPrompt.trim()
      ? [...baseSystemPrompt, appendSystemPrompt]
      : baseSystemPrompt

  const normalizedJsonSchema =
    typeof jsonSchema === 'string' ? jsonSchema.trim() : ''
  const parsedJsonSchema = (() => {
    if (!normalizedJsonSchema) return null
    try {
      const parsed = JSON.parse(normalizedJsonSchema)
      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
        throw new Error('Schema must be a JSON object')
      }
      return parsed as Record<string, unknown>
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error)
      console.error(`Error: Invalid --json-schema: ${msg}`)
      process.exit(1)
    }
  })()

  if (parsedJsonSchema) {
    systemPrompt.push(
      [
        'You MUST respond with ONLY valid JSON.',
        'The JSON MUST validate against the following JSON Schema.',
        'Do not wrap the JSON in markdown code fences and do not add extra commentary.',
        '',
        `<json_schema>${JSON.stringify(parsedJsonSchema)}</json_schema>`,
      ].join('\n'),
    )
  }
  const ctx = await getContext()

  const isBypassAvailable =
    !safe ||
    Boolean(allowDangerouslySkipPermissions) ||
    Boolean(dangerouslySkipPermissions)

  let toolPermissionContext = loadToolPermissionContextFromDisk({
    projectDir: cwd,
    includeKodeProjectConfig: true,
    isBypassPermissionsModeAvailable: isBypassAvailable,
  })

  const cliRuleList = (value: unknown): string[] => {
    if (!value) return []
    const raw = Array.isArray(value) ? value : [value]
    return raw
      .flatMap(v => String(v ?? '').split(','))
      .map(v => v.trim())
      .filter(Boolean)
  }

  const allowedRules = cliRuleList(allowedTools)
  const deniedRules = cliRuleList(disallowedTools)
  const additionalDirs = cliRuleList(addDir)

  const updates: any[] = []
  if (allowedRules.length > 0) {
    updates.push({
      type: 'addRules',
      destination: 'cliArg',
      behavior: 'allow',
      rules: allowedRules,
    })
  }
  if (deniedRules.length > 0) {
    updates.push({
      type: 'addRules',
      destination: 'cliArg',
      behavior: 'deny',
      rules: deniedRules,
    })
  }
  if (additionalDirs.length > 0) {
    updates.push({
      type: 'addDirectories',
      destination: 'cliArg',
      directories: additionalDirs,
    })
  }

  const normalizedPermissionMode =
    typeof permissionMode === 'string' ? permissionMode.trim() : ''
  if (normalizedPermissionMode) {
    const normalized =
      normalizedPermissionMode === 'delegate'
        ? 'default'
        : normalizedPermissionMode
    const allowed = new Set([
      'acceptEdits',
      'bypassPermissions',
      'default',
      'dontAsk',
      'plan',
    ])
    if (!allowed.has(normalized)) {
      console.error(
        `Error: Invalid --permission-mode "${normalizedPermissionMode}". Expected one of: acceptEdits, bypassPermissions, default, delegate, dontAsk, plan`,
      )
      process.exit(1)
    }
    updates.push({
      type: 'setMode',
      destination: 'cliArg',
      mode: normalized,
    })
  }

  if (dangerouslySkipPermissions) {
    updates.push({
      type: 'setMode',
      destination: 'cliArg',
      mode: 'bypassPermissions',
    })
  }

  if (updates.length > 0) {
    toolPermissionContext = applyToolPermissionContextUpdates(
      toolPermissionContext,
      updates,
    )
  }

  const printOptions = {
    commands,
    tools: toolsForPrint,
    verbose: true,
    safeMode: safe,
    forkNumber: 0,
    messageLogName: 'unused',
    maxThinkingTokens: 0,
    persistSession: sessionPersistence !== false,
    toolPermissionContext,
    mcpClients,
    shouldAvoidPermissionPrompts: normalizedInputFormat !== 'stream-json',
    model:
      typeof model === 'string' && model.trim()
        ? model.trim()
        : (undefined as any),
  }

  const availableTools = toolsForPrint.map(t => t.name)
  const slashCommands =
    disableSlashCommands === true
      ? undefined
      : commands.filter(c => !c.isHidden).map(c => `/${c.userFacingName()}`)
  const initMsg = makeSdkInitMessage({
    sessionId: sessionIdForSdk,
    cwd,
    tools: availableTools,
    slashCommands,
  })

  const writeSdkLine = (obj: any) => {
    process.stdout.write(JSON.stringify(obj) + '\n')
  }

  if (normalizedOutputFormat === 'stream-json') {
    writeSdkLine(initMsg)
  } else {
    sdkMessages.push(initMsg)
  }

  let activeTurnAbortController: AbortController | null = null
  const structured = createPrintModeStructuredStdio({
    enabled: normalizedInputFormat === 'stream-json',
    stdin: process.stdin,
    stdout: process.stdout,
    onInterrupt: () => {
      activeTurnAbortController?.abort()
    },
    onControlRequest: createPrintModeControlRequestHandler({
      printOptions,
      mcpClients,
    }),
  })

  if (structured) structured.start()

  const permissionTimeoutMs = (() => {
    const raw = process.env.KODE_STDIO_PERMISSION_TIMEOUT_MS
    const n = raw ? Number(raw) : NaN
    return Number.isFinite(n) && n > 0 ? n : 30_000
  })()

  const canUseTool = createStdioCanUseTool({
    normalizedPermissionPromptTool,
    structured,
    permissionTimeoutMs,
    cwd,
    printOptions,
    hasPermissionsToUseTool,
    applyToolPermissionContextUpdates,
    persistToolPermissionUpdateToDisk,
  })

  if (normalizedInputFormat === 'stream-json') {
    if (!structured) {
      console.error('Error: Structured stdin is not available')
      process.exit(1)
    }

    await runPrintModeStreamJsonSession({
      structured,
      query,
      writeSdkLine,
      sessionId: sessionIdForSdk,
      systemPrompt,
      jsonSchema: parsedJsonSchema,
      context: ctx,
      canUseTool,
      toolUseContextBase: {
        options: printOptions,
        messageId: undefined,
        readFileTimestamps: {},
        setToolJSX: () => {},
      },
      replayUserMessages: Boolean(replayUserMessages),
      getTotalCostUsd: () => getTotalCost(),
      onActiveTurnAbortControllerChanged: controller => {
        activeTurnAbortController = controller
      },
      initialMessages: initialMessages as any,
    })

    process.exit(0)
  }


  const abortController = new AbortController()
  const userMsg = await (async () => {
    if (normalizedInputFormat !== 'stream-json') {
      addToHistory(inputPrompt)
      return createUserMessage(inputPrompt)
    }
    if (!structured) {
      console.error('Error: Structured stdin is not available')
      process.exit(1)
    }

    const sdkUser = await structured.nextUserMessage({
      signal: abortController.signal,
      timeoutMs: 30_000,
    })

    if (!sdkUser || typeof sdkUser !== 'object') {
      console.error('Error: Invalid stream-json input (missing user message)')
      process.exit(1)
    }

    const sdkMessage = (sdkUser as any).message
    const sdkContent = sdkMessage?.content
    if (typeof sdkContent !== 'string' && !Array.isArray(sdkContent)) {
      console.error('Error: Invalid stream-json user message content')
      process.exit(1)
    }

    const m = createUserMessage(sdkContent as any)
    if (typeof (sdkUser as any).uuid === 'string' && (sdkUser as any).uuid) {
      ;(m as any).uuid = String((sdkUser as any).uuid)
    }
    return m
  })()

  const baseMessages = [...(initialMessages ?? []), userMsg]

  const sdkUser = kodeMessageToSdkMessage(userMsg as any, sessionIdForSdk)
  if (sdkUser) {
    if (normalizedOutputFormat === 'stream-json') {
      writeSdkLine(sdkUser)
    } else {
      sdkMessages.push(sdkUser)
    }
  }

  let lastAssistant: any | null = null
  let queryError: unknown = null
  try {
    for await (const m of query(baseMessages, systemPrompt, ctx, canUseTool, {
      options: printOptions,
      abortController,
      messageId: undefined,
      readFileTimestamps: {},
      setToolJSX: () => {},
    })) {
      if (m.type === 'assistant') lastAssistant = m
      const sdk = kodeMessageToSdkMessage(m, sessionIdForSdk)
      if (!sdk) continue

      if (normalizedOutputFormat === 'stream-json') {
        writeSdkLine(sdk)
      } else {
        sdkMessages.push(sdk)
      }
    }
  } catch (e) {
    abortController.abort()
    queryError = e
  }

  const textFromAssistant = lastAssistant?.message?.content?.find(
    (c: any) => c.type === 'text',
  )?.text
  let text =
    typeof textFromAssistant === 'string'
      ? textFromAssistant
      : queryError instanceof Error
        ? queryError.message
        : queryError
          ? String(queryError)
          : ''

  let structuredOutput: Record<string, unknown> | undefined
  if (parsedJsonSchema && !queryError) {
    try {
      const raw = typeof textFromAssistant === 'string' ? textFromAssistant : ''
      const fenced = raw.trim()
      const unfenced = (() => {
        const m = fenced.match(/^```(?:json)?\\s*([\\s\\S]*?)\\s*```$/i)
        return m ? m[1]!.trim() : fenced
      })()

      const parsed = JSON.parse(unfenced)
      const Ajv = (await import('ajv')).default as any
      const ajv = new Ajv({ allErrors: true, strict: false })
      const validate = ajv.compile(parsedJsonSchema)
      const ok = validate(parsed)
      if (!ok) {
        const errorText =
          typeof ajv.errorsText === 'function'
            ? ajv.errorsText(validate.errors, { separator: '; ' })
            : JSON.stringify(validate.errors ?? [])
        throw new Error(
          `Structured output failed JSON schema validation: ${errorText}`,
        )
      }
      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
        throw new Error('Structured output must be a JSON object')
      }
      structuredOutput = parsed as Record<string, unknown>
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e)
      queryError = new Error(msg)
      text = msg
    }
  }

  const usage = lastAssistant?.message?.usage
  const totalCostUsd = getTotalCost()
  const durationMs = Date.now() - startedAt
  const resultMsg = makeSdkResultMessage({
    sessionId: sessionIdForSdk,
    result: String(text),
    structuredOutput,
    numTurns: 1,
    usage,
    totalCostUsd,
    durationMs,
    durationApiMs: 0,
    isError: Boolean(queryError),
  })

  if (normalizedOutputFormat === 'stream-json') {
    writeSdkLine(resultMsg)
    process.exit(0)
  }

  sdkMessages.push(resultMsg)
  if (verbose) {
    process.stdout.write(`${JSON.stringify(sdkMessages, null, 2)}\n`)
  } else {
    process.stdout.write(`${JSON.stringify(resultMsg, null, 2)}\n`)
  }
  process.exit(0)
}
