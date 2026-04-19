import { describe, expect, test } from 'bun:test'
import {
  __formatMultiSelectAnswerForTests,
  __getTabHeadersForTests,
} from '@components/permissions/ask-user-question-permission-request/AskUserQuestionPermissionRequest'

describe('AskUserQuestionPermissionRequest helpers', () => {
  test('formats multiSelect answers like reference CLI (comma-separated, Other appended)', () => {
    expect(__formatMultiSelectAnswerForTests(['A', 'B'], '')).toBe('A, B')
    expect(__formatMultiSelectAnswerForTests(['__other__', 'A'], 'foo')).toBe(
      'A, foo',
    )
    expect(__formatMultiSelectAnswerForTests(['__other__'], '   ')).toBe('')
    expect(__formatMultiSelectAnswerForTests([], 'foo')).toBe('')
  })

  test('tab header truncation keeps array length stable', () => {
    const questions = [
      {
        question: 'Q1?',
        header: 'This is a very long header',
        options: [],
        multiSelect: false,
      },
      {
        question: 'Q2?',
        header: 'Another very long header',
        options: [],
        multiSelect: false,
      },
    ]

    const headers = __getTabHeadersForTests({
      questions: questions as any,
      currentQuestionIndex: 0,
      columns: 20,
      hideSubmitTab: false,
    })

    expect(headers).toHaveLength(2)
    expect(headers[0]!.length).toBeGreaterThan(0)
  })
})
