import { describe, expect, test } from 'bun:test'
import { __isTextInputCharForTests } from '@components/permissions/ask-user-question-permission-request/AskUserQuestionPermissionRequest'

describe('AskUserQuestion Other text input filtering (Reference CLI parity)', () => {
  test('does not treat Enter / control chars as text input', () => {
    expect(__isTextInputCharForTests('\r', { return: true })).toBe(false)
    expect(__isTextInputCharForTests('\r', { return: false })).toBe(false)
    expect(__isTextInputCharForTests('\n', {})).toBe(false)
    expect(__isTextInputCharForTests('\t', { tab: true })).toBe(false)
    expect(__isTextInputCharForTests('\u001b', {})).toBe(false)
  })

  test('accepts normal printable characters (including space)', () => {
    expect(__isTextInputCharForTests('a', {})).toBe(true)
    expect(__isTextInputCharForTests(' ', {})).toBe(true)
    expect(__isTextInputCharForTests('实现', {})).toBe(true)
    expect(__isTextInputCharForTests('实现', { return: true })).toBe(true)
    expect(__isTextInputCharForTests('你好', {})).toBe(true)
    expect(__isTextInputCharForTests('ab', {})).toBe(true)
  })

  test('rejects meta/ctrl modified keys', () => {
    expect(__isTextInputCharForTests('a', { ctrl: true })).toBe(false)
    expect(__isTextInputCharForTests('a', { meta: true })).toBe(false)
  })

  test('rejects strings containing any control characters', () => {
    expect(__isTextInputCharForTests('a\nb', {})).toBe(false)
    expect(__isTextInputCharForTests('a\rb', {})).toBe(false)
    expect(__isTextInputCharForTests('a\tb', {})).toBe(false)
  })
})
