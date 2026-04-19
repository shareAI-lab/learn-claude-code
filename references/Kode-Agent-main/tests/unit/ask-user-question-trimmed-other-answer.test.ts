import { describe, expect, test } from 'bun:test'
import { __getTrimmedOtherAnswerForTests } from '@components/permissions/ask-user-question-permission-request/AskUserQuestionPermissionRequest'

describe('AskUserQuestion Other answer trimming (Reference CLI parity)', () => {
  test('returns null for empty/whitespace-only input', () => {
    expect(__getTrimmedOtherAnswerForTests('')).toBeNull()
    expect(__getTrimmedOtherAnswerForTests('   ')).toBeNull()
    expect(__getTrimmedOtherAnswerForTests('\n')).toBeNull()
    expect(__getTrimmedOtherAnswerForTests('\t')).toBeNull()
  })

  test('accepts English and CJK text', () => {
    expect(__getTrimmedOtherAnswerForTests('html with three js')).toBe(
      'html with three js',
    )
    expect(__getTrimmedOtherAnswerForTests('  html with three js  ')).toBe(
      'html with three js',
    )
    expect(__getTrimmedOtherAnswerForTests('实现')).toBe('实现')
    expect(__getTrimmedOtherAnswerForTests('  你好  ')).toBe('你好')
  })
})
