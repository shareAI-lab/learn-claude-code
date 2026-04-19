import { describe, expect, test } from 'bun:test'
import { AskUserQuestionTool } from '@tools/interaction/AskUserQuestionTool/AskUserQuestionTool'

function makeValidInput(overrides?: Partial<any>) {
  return {
    questions: [
      {
        question: 'Which option?',
        header: 'Header',
        options: [
          { label: 'A', description: 'Option A' },
          { label: 'B', description: 'Option B' },
        ],
        multiSelect: false,
      },
    ],
    ...overrides,
  }
}

describe('AskUserQuestionTool schema parity', () => {
  test('accepts 1-4 questions and 2-4 options', () => {
    expect(
      AskUserQuestionTool.inputSchema.safeParse(makeValidInput()).success,
    ).toBe(true)

    expect(
      AskUserQuestionTool.inputSchema.safeParse(
        makeValidInput({
          questions: Array.from({ length: 4 }, (_, index) => ({
            question: `Q${index}?`,
            header: `H${index}`,
            options: [
              { label: 'A', description: 'A' },
              { label: 'B', description: 'B' },
            ],
            multiSelect: false,
          })),
        }),
      ).success,
    ).toBe(true)

    expect(
      AskUserQuestionTool.inputSchema.safeParse(
        makeValidInput({
          questions: [
            {
              question: 'Q?',
              header: 'H',
              options: [
                { label: 'A', description: 'A' },
                { label: 'B', description: 'B' },
                { label: 'C', description: 'C' },
                { label: 'D', description: 'D' },
              ],
              multiSelect: false,
            },
          ],
        }),
      ).success,
    ).toBe(true)
  })

  test('rejects out-of-range question counts', () => {
    expect(
      AskUserQuestionTool.inputSchema.safeParse({ questions: [] }).success,
    ).toBe(false)

    expect(
      AskUserQuestionTool.inputSchema.safeParse(
        makeValidInput({
          questions: Array.from({ length: 5 }, (_, index) => ({
            question: `Q${index}?`,
            header: `H${index}`,
            options: [
              { label: 'A', description: 'A' },
              { label: 'B', description: 'B' },
            ],
            multiSelect: false,
          })),
        }),
      ).success,
    ).toBe(false)
  })

  test('rejects out-of-range option counts', () => {
    expect(
      AskUserQuestionTool.inputSchema.safeParse(
        makeValidInput({
          questions: [
            {
              question: 'Q?',
              header: 'H',
              options: [{ label: 'A', description: 'A' }],
              multiSelect: false,
            },
          ],
        }),
      ).success,
    ).toBe(false)

    expect(
      AskUserQuestionTool.inputSchema.safeParse(
        makeValidInput({
          questions: [
            {
              question: 'Q?',
              header: 'H',
              options: [
                { label: 'A', description: 'A' },
                { label: 'B', description: 'B' },
                { label: 'C', description: 'C' },
                { label: 'D', description: 'D' },
                { label: 'E', description: 'E' },
              ],
              multiSelect: false,
            },
          ],
        }),
      ).success,
    ).toBe(false)
  })

  test('does not enforce header length (CLI truncates in UI instead)', () => {
    expect(
      AskUserQuestionTool.inputSchema.safeParse(
        makeValidInput({
          questions: [
            {
              question: 'Q?',
              header: 'This header is definitely longer than 12 chars',
              options: [
                { label: 'A', description: 'A' },
                { label: 'B', description: 'B' },
              ],
              multiSelect: false,
            },
          ],
        }),
      ).success,
    ).toBe(true)
  })

  test('requires unique question texts and option labels', () => {
    expect(
      AskUserQuestionTool.inputSchema.safeParse(
        makeValidInput({
          questions: [
            {
              question: 'Same?',
              header: 'H1',
              options: [
                { label: 'A', description: 'A' },
                { label: 'B', description: 'B' },
              ],
              multiSelect: false,
            },
            {
              question: 'Same?',
              header: 'H2',
              options: [
                { label: 'A', description: 'A' },
                { label: 'B', description: 'B' },
              ],
              multiSelect: false,
            },
          ],
        }),
      ).success,
    ).toBe(false)

    expect(
      AskUserQuestionTool.inputSchema.safeParse(
        makeValidInput({
          questions: [
            {
              question: 'Q?',
              header: 'H',
              options: [
                { label: 'A', description: 'A' },
                { label: 'A', description: 'A2' },
              ],
              multiSelect: false,
            },
          ],
        }),
      ).success,
    ).toBe(false)
  })

  test('is strict at the top level but tolerant for nested objects', () => {
    expect(
      AskUserQuestionTool.inputSchema.safeParse(
        makeValidInput({ extra: 'nope' }),
      ).success,
    ).toBe(false)

    expect(
      AskUserQuestionTool.inputSchema.safeParse(
        makeValidInput({
          questions: [
            {
              question: 'Q?',
              header: 'H',
              extraQuestionField: 123,
              options: [
                { label: 'A', description: 'A', extraOptionField: true },
                { label: 'B', description: 'B', extraOptionField: false },
              ],
              multiSelect: false,
            },
          ],
        }),
      ).success,
    ).toBe(true)
  })

  test('renderResultForAssistant matches reference CLI formatting', () => {
    const result = AskUserQuestionTool.renderResultForAssistant({
      questions: [] as any,
      answers: { 'Q1?': 'A', 'Q2?': 'B, C' },
    })

    expect(result).toBe(
      `User has answered your questions: "Q1?"="A", "Q2?"="B, C". You can now continue with the user's answers in mind.`,
    )
  })
})
