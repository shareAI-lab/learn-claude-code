import { describe, expect, test } from 'bun:test'
import {
  parseToolUsePartialJson,
  parseToolUsePartialJsonOrThrow,
} from '@utils/tooling/toolUsePartialJson'

describe('tool_use input_json_delta partial JSON parsing', () => {
  test('closes unclosed objects/arrays', () => {
    expect(parseToolUsePartialJson('{"a":1')).toEqual({ a: 1 })
    expect(parseToolUsePartialJson('{"a":{"b":2')).toEqual({ a: { b: 2 } })
    expect(parseToolUsePartialJson('[1,2')).toEqual([1])
    expect(parseToolUsePartialJson('{"a":[1,2')).toEqual({ a: [1] })
  })

  test('trims trailing separators/delimiters and incomplete numbers', () => {
    expect(parseToolUsePartialJson('{"a":1,')).toEqual({ a: 1 })
    expect(parseToolUsePartialJson('{"a":')).toEqual({})
    expect(parseToolUsePartialJson('[1,')).toEqual([1])
    expect(parseToolUsePartialJson('{"a":1.')).toEqual({})
    expect(parseToolUsePartialJson('{"a":-')).toEqual({})
  })

  test('handles string escapes and incomplete strings', () => {
    expect(parseToolUsePartialJson('{"a":"b\\\"c"}')).toEqual({ a: 'b"c' })
    expect(parseToolUsePartialJson('{"a":"b\\\"c')).toEqual({})
  })

  test('error message matches reference wording', () => {
    const bad = '{"a": }'
    expect(() => parseToolUsePartialJsonOrThrow(bad)).toThrow(
      /Unable to parse tool parameter JSON from model\. Please retry your request or adjust your prompt\. Error: SyntaxError:/,
    )
    expect(() => parseToolUsePartialJsonOrThrow(bad)).toThrow(
      new RegExp(
        `\\. JSON: ${bad.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&')}$`,
      ),
    )
  })
})
