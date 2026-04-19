import type { Message } from '@query'
import type { CanUseToolFn } from '@kode-types/canUseTool'
import type { ToolUseContext } from '@tool'
import { createUserMessage } from '@utils/messages'
import {
  kodeMessageToSdkMessage,
  makeSdkResultMessage,
  type SdkMessage,
} from './kodeAgentStreamJson'
import type { KodeAgentStructuredStdio } from './kodeAgentStructuredStdio'

type QueryFn = (
  messages: Message[],
  systemPrompt: string[],
  context: { [k: string]: string },
  canUseTool: CanUseToolFn,
  toolUseContext: ToolUseContext & { setToolJSX: (jsx: any) => void },
) => AsyncGenerator<Message, void>

export async function runKodeAgentStreamJsonSession(args: {
  structured: KodeAgentStructuredStdio
  query: QueryFn
  writeSdkLine: (obj: SdkMessage) => void
  sessionId: string
  systemPrompt: string[]
  jsonSchema?: Record<string, unknown> | null
  context: { [k: string]: string }
  canUseTool: CanUseToolFn
  toolUseContextBase: Omit<ToolUseContext, 'abortController'> & {
    abortController?: never
    setToolJSX: (jsx: any) => void
  }
  replayUserMessages: boolean
  getTotalCostUsd: () => number
  onActiveTurnAbortControllerChanged?: (
    controller: AbortController | null,
  ) => void
  initialMessages?: Message[]
}): Promise<void> {
  const conversation: Message[] = [...(args.initialMessages ?? [])]
  const seenUserUuids = new Set<string>()

  while (true) {
    let sdkUser: any
    try {
      sdkUser = await args.structured.nextUserMessage()
    } catch {
      return
    }

    const sdkMessage = sdkUser?.message
    const sdkContent = sdkMessage?.content
    if (typeof sdkContent !== 'string' && !Array.isArray(sdkContent)) {
      throw new Error('Error: Invalid stream-json user message content')
    }

    const providedUuid =
      typeof sdkUser?.uuid === 'string' && sdkUser.uuid
        ? String(sdkUser.uuid)
        : null

    const userMsg = createUserMessage(sdkContent as any) as any
    if (providedUuid) {
      userMsg.uuid = providedUuid
    }

    const isDuplicate = Boolean(providedUuid && seenUserUuids.has(providedUuid))

    if (args.replayUserMessages) {
      const sdkUserOut = kodeMessageToSdkMessage(userMsg, args.sessionId)
      if (sdkUserOut) args.writeSdkLine(sdkUserOut)
    }

    if (isDuplicate) {
      continue
    }

    if (providedUuid) seenUserUuids.add(providedUuid)

    conversation.push(userMsg)

    const costBefore = args.getTotalCostUsd()
    const startedAt = Date.now()
    const turnAbortController = new AbortController()
    args.onActiveTurnAbortControllerChanged?.(turnAbortController)

    let lastAssistant: any | null = null
    let queryError: unknown = null
    const toAppend: Message[] = []

    try {
      const inputForTurn = [...conversation]
      for await (const m of args.query(
        inputForTurn,
        args.systemPrompt,
        args.context,
        args.canUseTool,
        {
          ...args.toolUseContextBase,
          abortController: turnAbortController,
        } as any,
      )) {
        if (m.type === 'assistant') lastAssistant = m as any
        if (m.type !== 'progress') {
          toAppend.push(m)
        }

        const sdk = kodeMessageToSdkMessage(m as any, args.sessionId)
        if (sdk) args.writeSdkLine(sdk)
      }
    } catch (e) {
      queryError = e
      try {
        turnAbortController.abort()
      } catch {}
    } finally {
      args.onActiveTurnAbortControllerChanged?.(null)
    }

    conversation.push(...toAppend)

    const textFromAssistant = lastAssistant?.message?.content?.find(
      (c: any) => c.type === 'text',
    )?.text
    const resultText =
      typeof textFromAssistant === 'string'
        ? textFromAssistant
        : queryError instanceof Error
          ? queryError.message
          : queryError
            ? String(queryError)
            : ''

    let structuredOutput: Record<string, unknown> | undefined
    if (args.jsonSchema && !queryError) {
      try {
        const fenced = String(resultText).trim()
        const unfenced = (() => {
          const m = fenced.match(/^```(?:json)?\\s*([\\s\\S]*?)\\s*```$/i)
          return m ? m[1]!.trim() : fenced
        })()

        const parsed = JSON.parse(unfenced)
        const Ajv = (await import('ajv')).default as any
        const ajv = new Ajv({ allErrors: true, strict: false })
        const validate = ajv.compile(args.jsonSchema)
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
        queryError = e
      }
    }

    const usage = lastAssistant?.message?.usage
    const durationMs = Date.now() - startedAt
    const totalCostUsd = Math.max(0, args.getTotalCostUsd() - costBefore)
    const isError = Boolean(queryError) || turnAbortController.signal.aborted

    args.writeSdkLine(
      makeSdkResultMessage({
        sessionId: args.sessionId,
        result: String(resultText),
        structuredOutput,
        numTurns: 1,
        usage,
        totalCostUsd,
        durationMs,
        durationApiMs: 0,
        isError,
      }) as any,
    )
  }
}
