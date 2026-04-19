import { describe, expect, test } from 'bun:test'
import {
  countLineBreaks,
  getSpecialPasteNewlineThreshold,
  normalizeLineEndings,
  shouldAggregatePasteChunk,
  shouldTreatAsSpecialPaste,
} from '@utils/terminal/paste'

describe('Regression: paste/newline heuristics', () => {
  test('normalizeLineEndings collapses CRLF/CR to LF', () => {
    expect(normalizeLineEndings('a\r\nb')).toBe('a\nb')
    expect(normalizeLineEndings('a\rb')).toBe('a\nb')
    expect(normalizeLineEndings('a\nb')).toBe('a\nb')
    expect(normalizeLineEndings('\r\n')).toBe('\n')
  })

  test('countLineBreaks treats CRLF as one break', () => {
    expect(countLineBreaks('a\r\nb')).toBe(1)
    expect(countLineBreaks('a\rb')).toBe(1)
    expect(countLineBreaks('a\nb')).toBe(1)
    expect(countLineBreaks('a\r\nb\nc')).toBe(2)
  })

  test('single newline insert signal should not start paste aggregation', () => {
    expect(shouldAggregatePasteChunk('\r', false)).toBe(false)
    expect(shouldAggregatePasteChunk('\n', false)).toBe(false)
    expect(shouldAggregatePasteChunk('\x1b\r', false)).toBe(false)
  })

  test('multi-line / large chunks should start paste aggregation', () => {
    expect(shouldAggregatePasteChunk('x\n', false)).toBe(true)
    expect(shouldAggregatePasteChunk('x\ry', false)).toBe(true)
    expect(shouldAggregatePasteChunk('a'.repeat(801), false)).toBe(true)
    expect(shouldAggregatePasteChunk('x', false)).toBe(false)
  })

  test('special paste is gated by length or newline threshold', () => {
    expect(getSpecialPasteNewlineThreshold(24)).toBe(2)
    expect(shouldTreatAsSpecialPaste('\n')).toBe(false)
    expect(shouldTreatAsSpecialPaste('\r')).toBe(false)
    expect(shouldTreatAsSpecialPaste('a\nb')).toBe(false)
    expect(shouldTreatAsSpecialPaste('a\nb\nc\nd')).toBe(true)
    expect(shouldTreatAsSpecialPaste('a'.repeat(801))).toBe(true)
    expect(shouldTreatAsSpecialPaste('a\nb\nc', { terminalRows: 11 })).toBe(
      true,
    )
  })
})
