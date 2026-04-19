import { describe, expect, test } from 'bun:test'
import { AskUserQuestionTool } from '@tools/interaction/AskUserQuestionTool/AskUserQuestionTool'
import { TaskOutputTool } from '@tools/TaskOutputTool/TaskOutputTool'
import { BashTool } from '@tools/BashTool/BashTool'
import { FileReadTool } from '@tools/FileReadTool/FileReadTool'
import { FileWriteTool } from '@tools/FileWriteTool/FileWriteTool'
import { GrepTool } from '@tools/search/GrepTool/GrepTool'
import { KillShellTool } from '@tools/KillShellTool/KillShellTool'
import { EnterPlanModeTool } from '@tools/agent/PlanModeTool/EnterPlanModeTool'
import { ExitPlanModeTool } from '@tools/agent/PlanModeTool/ExitPlanModeTool'
import { TaskTool } from '@tools/agent/TaskTool/TaskTool'
import { TodoWriteTool } from '@tools/interaction/TodoWriteTool/TodoWriteTool'
import { WebFetchTool } from '@tools/network/WebFetchTool/WebFetchTool'

describe('Tool isReadOnly/isConcurrencySafe flags (Reference CLI parity)', () => {
  test('key tools match expected flags', () => {
    expect(TaskOutputTool.isReadOnly()).toBe(true)
    expect(TaskOutputTool.isConcurrencySafe()).toBe(true)

    expect(KillShellTool.isReadOnly()).toBe(false)
    expect(KillShellTool.isConcurrencySafe()).toBe(true)

    expect(TodoWriteTool.isReadOnly()).toBe(false)
    expect(TodoWriteTool.isConcurrencySafe()).toBe(false)

    expect(AskUserQuestionTool.isReadOnly()).toBe(true)
    expect(AskUserQuestionTool.isConcurrencySafe()).toBe(true)

    expect(FileReadTool.isReadOnly()).toBe(true)
    expect(FileReadTool.isConcurrencySafe()).toBe(true)

    expect(FileWriteTool.isReadOnly()).toBe(false)
    expect(FileWriteTool.isConcurrencySafe()).toBe(false)

    expect(GrepTool.isReadOnly()).toBe(true)
    expect(GrepTool.isConcurrencySafe()).toBe(true)

    expect(WebFetchTool.isReadOnly()).toBe(true)
    expect(WebFetchTool.isConcurrencySafe()).toBe(true)

    expect(EnterPlanModeTool.isReadOnly()).toBe(true)
    expect(EnterPlanModeTool.isConcurrencySafe()).toBe(true)

    expect(ExitPlanModeTool.isReadOnly()).toBe(false)
    expect(ExitPlanModeTool.isConcurrencySafe()).toBe(true)

    expect(TaskTool.isReadOnly()).toBe(true)
    expect(TaskTool.isConcurrencySafe()).toBe(true)
  })

  test('BashTool concurrency-safe equals read-only (Reference CLI y9)', () => {
    const readOnly = { command: 'pwd' } as any
    const notReadOnly = { command: 'cat foo > bar' } as any

    expect(BashTool.isReadOnly(readOnly)).toBe(true)
    expect(BashTool.isConcurrencySafe(readOnly)).toBe(true)
    expect(BashTool.isReadOnly(notReadOnly)).toBe(false)
    expect(BashTool.isConcurrencySafe(notReadOnly)).toBe(false)
  })
})
