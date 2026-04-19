import { createHash, type UUID } from 'crypto'
import { mkdirSync, readFileSync, writeFileSync } from 'fs'
import { dirname } from 'path'
import type { AssistantMessage, UserMessage } from '@query'
import { existsSync } from 'fs'
import { env } from '@utils/config/env'
import { getCwd } from '@utils/state'
import * as path from 'path'
import { mapValues } from 'lodash-es'
import type { ContentBlock } from '@anthropic-ai/sdk/resources/index.mjs'

export async function withVCR(
  messages: (UserMessage | AssistantMessage)[],
  f: () => Promise<AssistantMessage>,
): Promise<AssistantMessage> {
  if (process.env.NODE_ENV !== 'test') {
    return await f()
  }

  const dehydratedInput = mapMessages(
    messages.map(_ => _.message.content),
    dehydrateValue,
  )
  const filename = `./fixtures/${dehydratedInput.map(_ => createHash('sha1').update(JSON.stringify(_)).digest('hex').slice(0, 6)).join('-')}.json`

  if (existsSync(filename)) {
    const cached = JSON.parse(readFileSync(filename, 'utf-8'))
    return mapAssistantMessage(cached.output, hydrateValue)
  }

  if (env.isCI) {
    process.stderr.write(
      `Anthropic API fixture missing. Re-run bun test locally, then commit the result. ${JSON.stringify({ input: dehydratedInput }, null, 2)}\n`,
    )
  }

  const result = await f()
  if (env.isCI) {
    return result
  }

  if (!existsSync(dirname(filename))) {
    mkdirSync(dirname(filename), { recursive: true })
  }
  writeFileSync(
    filename,
    JSON.stringify(
      {
        input: dehydratedInput,
        output: mapAssistantMessage(result, dehydrateValue),
      },
      null,
      2,
    ),
  )
  return result
}

function mapMessages(
  messages: (UserMessage | AssistantMessage)['message']['content'][],
  f: (s: unknown) => unknown,
): (UserMessage | AssistantMessage)['message']['content'][] {
  return messages.map(_ => {
    if (typeof _ === 'string') {
      return f(_)
    }
    return _.map(_ => {
      switch (_.type) {
        case 'tool_result':
          if (typeof _.content === 'string') {
            return { ..._, content: f(_.content) }
          }
          if (Array.isArray(_.content)) {
            return {
              ..._,
              content: _.content.map(_ => {
                switch (_.type) {
                  case 'text':
                    return { ..._, text: f(_.text) }
                  case 'image':
                    return _
                }
              }),
            }
          }
          return _
        case 'text':
          return { ..._, text: f(_.text) }
        case 'tool_use':
          return {
            ..._,
            input: mapValues(_.input as Record<string, unknown>, f),
          }
        case 'image':
          return _
      }
    })
  }) as (UserMessage | AssistantMessage)['message']['content'][]
}

function mapAssistantMessage(
  message: AssistantMessage,
  f: (s: unknown) => unknown,
): AssistantMessage {
  return {
    durationMs: 'DURATION' as unknown as number,
    costUSD: 'COST' as unknown as number,
    uuid: 'UUID' as unknown as UUID,
    message: {
      ...message.message,
      content: message.message.content
        .map(_ => {
          switch (_.type) {
            case 'text':
              return {
                ..._,
                text: f(_.text) as string,
                citations: _.citations || [],
              }
            case 'tool_use':
              return {
                ..._,
                input: mapValues(_.input as Record<string, unknown>, f),
              }
            default:
              return _
          }
        })
        .filter(Boolean) as ContentBlock[],
    },
    type: 'assistant',
  }
}

function dehydrateValue(s: unknown): unknown {
  if (typeof s !== 'string') {
    return s
  }
  const s1 = s
    .replace(/num_files="\d+"/g, 'num_files="[NUM]"')
    .replace(/duration_ms="\d+"/g, 'duration_ms="[DURATION]"')
    .replace(/cost_usd="\d+"/g, 'cost_usd="[COST]"')
    .replace(/\//g, path.sep)
    .replaceAll(getCwd(), '[CWD]')
  if (s1.includes('Files modified by user:')) {
    return 'Files modified by user: [FILES]'
  }
  return s1
}

function hydrateValue(s: unknown): unknown {
  if (typeof s !== 'string') {
    return s
  }
  return s
    .replaceAll('[NUM]', '1')
    .replaceAll('[DURATION]', '100')
    .replaceAll('[CWD]', getCwd())
}
