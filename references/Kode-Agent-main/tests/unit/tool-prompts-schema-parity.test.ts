import { describe, expect, test } from 'bun:test'
import { BashTool } from '@tools/BashTool/BashTool'
import { TaskOutputTool } from '@tools/TaskOutputTool/TaskOutputTool'
import { KillShellTool } from '@tools/KillShellTool/KillShellTool'
import { TodoWriteTool } from '@tools/interaction/TodoWriteTool/TodoWriteTool'
import { WebFetchTool } from '@tools/network/WebFetchTool/WebFetchTool'

describe('Tool prompt/description/schema parity', () => {
  test('BashTool description uses input.description or falls back', async () => {
    expect(
      await BashTool.description?.({ description: 'List files' } as any),
    ).toBe('List files')

    expect(await BashTool.description?.({ command: 'ls' } as any)).toBe(
      'Run shell command',
    )
  })

  test('BashTool prompt contains reference sections', async () => {
    const prompt = await BashTool.prompt()
    expect(prompt).toContain(
      'Executes a given bash command in a persistent shell session with optional timeout, ensuring proper handling and security measures.',
    )
    expect(prompt).toContain(
      'IMPORTANT: This tool is for terminal operations like git, npm, docker, etc. DO NOT use it for file operations (reading, writing, editing, searching, finding files) - use the specialized tools for this instead.',
    )
    expect(prompt).toContain('# Committing changes with git')
    expect(prompt).toContain('# Creating pull requests')
    expect(prompt).toContain('Git Safety Protocol:')
  })

  test('BashTool schema description includes examples', () => {
    const schema: any = BashTool.inputSchema as any
    const description = schema.shape.description?._def?.description
    expect(description).toContain('Examples:')
    expect(description).toContain('Input: ls')
    expect(description).toContain("Output: Create directory 'foo'")
  })

  test('BashTool schema matches reference CLI keys', () => {
    const schema: any = BashTool.inputSchema as any
    const keys = Object.keys(schema.shape).sort()
    expect(keys).toEqual(
      [
        'command',
        'dangerouslyDisableSandbox',
        'description',
        'run_in_background',
        'timeout',
      ].sort(),
    )
  })

  test('BashTool validateInput rejects timeouts above 600000ms', async () => {
    const result = await BashTool.validateInput?.({
      command: 'echo hi',
      timeout: 600_001,
    } as any)

    expect(result?.result).toBe(false)
    expect(result?.message).toContain('Maximum allowed timeout')
  })

  test('TaskOutputTool prompt matches reference wording', async () => {
    const prompt = await TaskOutputTool.prompt()
    expect(prompt).toContain('Task IDs can be found using the /tasks command')
  })

  test('KillShellTool prompt matches reference wording', async () => {
    const prompt = await KillShellTool.prompt()
    expect(prompt).toContain('Shell IDs can be found using the /tasks command')
  })

  test('TodoWriteTool description matches reference wording', async () => {
    const description = await TodoWriteTool.description()
    expect(description).toContain(
      'Update the todo list for the current session.',
    )
    expect(description).toContain(
      'Always provide both content (imperative) and activeForm',
    )
  })

  test('WebFetchTool description matches reference wording', async () => {
    expect(
      await WebFetchTool.description?.({
        url: 'https://example.com',
        prompt: 'x',
      } as any),
    ).toBe('Kode Agent wants to fetch content from example.com')

    expect(
      await WebFetchTool.description?.({ url: '', prompt: 'x' } as any),
    ).toBe('Kode Agent wants to fetch content from this URL')
  })
})
