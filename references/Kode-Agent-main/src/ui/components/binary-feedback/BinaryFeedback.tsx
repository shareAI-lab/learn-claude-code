import { default as React, useCallback } from 'react'
import { useNotifyAfterTimeout } from '@hooks/useNotifyAfterTimeout'
import { AssistantMessage, BinaryFeedbackResult } from '@query'
import type { Tool } from '@tool'
import type { NormalizedMessage } from '@utils/messages'
import { BinaryFeedbackView } from './BinaryFeedbackView'
import {
  type BinaryFeedbackChoose,
  getBinaryFeedbackResultForChoice,
  logBinaryFeedbackEvent,
} from '@app/binaryFeedback'
import { PRODUCT_NAME } from '@constants/product'

type Props = {
  m1: AssistantMessage
  m2: AssistantMessage
  resolve: (result: BinaryFeedbackResult) => void
  debug: boolean
  erroredToolUseIDs: Set<string>
  inProgressToolUseIDs: Set<string>
  normalizedMessages: NormalizedMessage[]
  tools: Tool[]
  unresolvedToolUseIDs: Set<string>
  verbose: boolean
}

export function BinaryFeedback({
  m1,
  m2,
  resolve,
  debug,
  erroredToolUseIDs,
  inProgressToolUseIDs,
  normalizedMessages,
  tools,
  unresolvedToolUseIDs,
  verbose,
}: Props): React.ReactNode {
  const onChoose = useCallback<BinaryFeedbackChoose>(
    choice => {
      logBinaryFeedbackEvent(m1, m2, choice)
      resolve(getBinaryFeedbackResultForChoice(m1, m2, choice))
    },
    [m1, m2, resolve],
  )
  useNotifyAfterTimeout(
    `${PRODUCT_NAME} needs your input on a response comparison`,
  )
  return (
    <BinaryFeedbackView
      debug={debug}
      erroredToolUseIDs={erroredToolUseIDs}
      inProgressToolUseIDs={inProgressToolUseIDs}
      m1={m1}
      m2={m2}
      normalizedMessages={normalizedMessages}
      tools={tools}
      unresolvedToolUseIDs={unresolvedToolUseIDs}
      verbose={verbose}
      onChoose={onChoose}
    />
  )
}
