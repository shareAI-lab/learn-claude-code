import { Box, Text } from 'ink'
import React from 'react'
import { z } from 'zod'
import { BLACK_CIRCLE } from '@constants/figures'
import { Tool } from '@tool'
import { getTheme } from '@utils/theme'
import { DESCRIPTION, PROMPT, TOOL_NAME_FOR_PROMPT } from './prompt'

const optionSchema = z.object({
  label: z.string(),
  description: z.string(),
})

const questionSchema = z.object({
  question: z.string(),
  header: z.string(),
  options: z.array(optionSchema).min(2).max(4),
  multiSelect: z.boolean(),
})

const inputSchema = z
  .strictObject({
    questions: z.array(questionSchema).min(1).max(4),
    answers: z.record(z.string(), z.string()).optional(),
  })
  .refine(
    input => {
      const questionTexts = input.questions.map(q => q.question)
      if (questionTexts.length !== new Set(questionTexts).size) return false

      for (const question of input.questions) {
        const optionLabels = question.options.map(option => option.label)
        if (optionLabels.length !== new Set(optionLabels).size) return false
      }

      return true
    },
    {
      message:
        'Question texts must be unique, option labels must be unique within each question',
    },
  )

type Input = z.infer<typeof inputSchema>
type Output = {
  questions: Input['questions']
  answers: Record<string, string>
}

export const AskUserQuestionTool = {
  name: TOOL_NAME_FOR_PROMPT,
  async description() {
    return DESCRIPTION
  },
  userFacingName() {
    return ''
  },
  inputSchema,
  isReadOnly() {
    return true
  },
  isConcurrencySafe() {
    return true
  },
  async isEnabled() {
    return true
  },
  needsPermissions() {
    return true
  },
  requiresUserInteraction() {
    return true
  },
  async prompt() {
    return PROMPT
  },
  renderToolUseMessage() {
    return null
  },
  renderToolUseRejectedMessage() {
    const theme = getTheme()
    return (
      <Box flexDirection="row" marginTop={1}>
        <Text color={theme.text}>{BLACK_CIRCLE}&nbsp;</Text>
        <Text>User declined to answer questions</Text>
      </Box>
    )
  },
  renderToolResultMessage(output: Output, _options: { verbose: boolean }) {
    const theme = getTheme()
    return (
      <Box flexDirection="column" marginTop={1}>
        <Box flexDirection="row">
          <Text color={theme.text}>{BLACK_CIRCLE}&nbsp;</Text>
          <Text>User answered Kode Agent&apos;s questions:</Text>
        </Box>
        <Box flexDirection="column" paddingLeft={2}>
          {Object.entries(output.answers).map(([question, answer]) => (
            <Box key={question}>
              <Text dimColor>
                · {question} → {answer}
              </Text>
            </Box>
          ))}
        </Box>
      </Box>
    )
  },
  renderResultForAssistant(output: Output) {
    const formatted = Object.entries(output.answers)
      .map(([question, answer]) => `"${question}"="${answer}"`)
      .join(', ')
    return `User has answered your questions: ${formatted}. You can now continue with the user's answers in mind.`
  },
  async *call({ questions, answers: prefilled }: Input) {
    const output: Output = { questions, answers: prefilled ?? {} }
    yield {
      type: 'result',
      data: output,
      resultForAssistant: this.renderResultForAssistant(output),
    }
  },
} satisfies Tool<typeof inputSchema, Output>
