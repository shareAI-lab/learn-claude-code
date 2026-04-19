import { TextBlock, ToolUseBlock } from '@anthropic-ai/sdk/resources/index.mjs'
import type { AssistantMessage, BinaryFeedbackResult } from './query'
import { isEqual, zip } from 'lodash-es'

export type BinaryFeedbackChoice =
  | 'prefer-left'
  | 'prefer-right'
  | 'neither'
  | 'no-preference'

export type BinaryFeedbackChoose = (choice: BinaryFeedbackChoice) => void

type BinaryFeedbackConfig = {
  sampleFrequency: number
}

async function getBinaryFeedbackConfig(): Promise<BinaryFeedbackConfig> {
  return { sampleFrequency: 0 }
}

function getMessageBlockSequence(m: AssistantMessage) {
  return m.message.content.map(cb => {
    if (cb.type === 'text') return 'text'
    if (cb.type === 'tool_use') return cb.name
    return cb.type
  })
}


function textContentBlocksEqual(cb1: TextBlock, cb2: TextBlock): boolean {
  return cb1.text === cb2.text
}

function contentBlocksEqual(
  cb1: TextBlock | ToolUseBlock,
  cb2: TextBlock | ToolUseBlock,
): boolean {
  if (cb1.type !== cb2.type) {
    return false
  }
  if (cb1.type === 'text') {
    return textContentBlocksEqual(cb1, cb2 as TextBlock)
  }
  cb2 = cb2 as ToolUseBlock
  return cb1.name === cb2.name && isEqual(cb1.input, cb2.input)
}

function allContentBlocksEqual(
  content1: (TextBlock | ToolUseBlock)[],
  content2: (TextBlock | ToolUseBlock)[],
): boolean {
  if (content1.length !== content2.length) {
    return false
  }
  return zip(content1, content2).every(([cb1, cb2]) =>
    contentBlocksEqual(cb1!, cb2!),
  )
}

export async function shouldUseBinaryFeedback(): Promise<boolean> {
  if (process.env.DISABLE_BINARY_FEEDBACK) {
    return false
  }
  if (process.env.FORCE_BINARY_FEEDBACK) {
    return true
  }
  if (process.env.USER_TYPE !== 'ant') {
    return false
  }
  if (process.env.NODE_ENV === 'test') {
    return false
  }

  const config = await getBinaryFeedbackConfig()
  if (config.sampleFrequency === 0) {
    return false
  }
  if (Math.random() > config.sampleFrequency) {
    return false
  }
  return true
}

export function messagePairValidForBinaryFeedback(
  m1: AssistantMessage,
  m2: AssistantMessage,
): boolean {
  const logPass = () => {}
  const logFail = (_reason: string) => {}

  const nonThinkingBlocks1 = m1.message.content.filter(
    b => b.type !== 'thinking' && b.type !== 'redacted_thinking',
  )
  const nonThinkingBlocks2 = m2.message.content.filter(
    b => b.type !== 'thinking' && b.type !== 'redacted_thinking',
  )
  const hasToolUse =
    nonThinkingBlocks1.some(b => b.type === 'tool_use') ||
    nonThinkingBlocks2.some(b => b.type === 'tool_use')

  if (!hasToolUse) {
    if (allContentBlocksEqual(nonThinkingBlocks1, nonThinkingBlocks2)) {
      logFail('contents_identical')
      return false
    }
    logPass()
    return true
  }

  if (
    allContentBlocksEqual(
      nonThinkingBlocks1.filter(b => b.type === 'tool_use'),
      nonThinkingBlocks2.filter(b => b.type === 'tool_use'),
    )
  ) {
    logFail('contents_identical')
    return false
  }

  logPass()
  return true
}

export function getBinaryFeedbackResultForChoice(
  m1: AssistantMessage,
  m2: AssistantMessage,
  choice: BinaryFeedbackChoice,
): BinaryFeedbackResult {
  switch (choice) {
    case 'prefer-left':
      return { message: m1, shouldSkipPermissionCheck: true }
    case 'prefer-right':
      return { message: m2, shouldSkipPermissionCheck: true }
    case 'no-preference':
      return {
        message: Math.random() < 0.5 ? m1 : m2,
        shouldSkipPermissionCheck: false,
      }
    case 'neither':
      return { message: null, shouldSkipPermissionCheck: false }
  }
}
export async function logBinaryFeedbackEvent(
  _m1: AssistantMessage,
  _m2: AssistantMessage,
  _choice: BinaryFeedbackChoice,
): Promise<void> {}
