import { afterAll, describe, expect, test } from 'bun:test'
import { mkdtempSync, rmSync, writeFileSync } from 'fs'
import { join } from 'path'
import { FileReadTool } from '@tools/FileReadTool/FileReadTool'

const tmpRoot = mkdtempSync(join(process.cwd(), '.tmp-test-file-read-tool-'))

afterAll(() => {
  rmSync(tmpRoot, { recursive: true, force: true })
})

async function runRead(input: {
  file_path: string
  offset?: number
  limit?: number
}) {
  const ctx = { readFileTimestamps: {} as Record<string, number> }
  const gen = FileReadTool.call(input as any, ctx as any)
  for await (const item of gen as any) {
    if (item?.type === 'result') return item.data
  }
  return null
}

describe('FileReadTool parity: offset semantics', () => {
  test('offset=1 reads from first line and reports startLine=1', async () => {
    const filePath = join(tmpRoot, 'offset-1.txt')
    writeFileSync(filePath, 'a\nb\nc', 'utf8')

    const data = await runRead({ file_path: filePath, offset: 1, limit: 2 })
    expect(data?.type).toBe('text')
    expect(data.file.startLine).toBe(1)
    expect(data.file.content).toBe('a\nb')
  })

  test('offset=2 reads from second line and reports startLine=2', async () => {
    const filePath = join(tmpRoot, 'offset-2.txt')
    writeFileSync(filePath, 'a\nb\nc', 'utf8')

    const data = await runRead({ file_path: filePath, offset: 2, limit: 1 })
    expect(data?.type).toBe('text')
    expect(data.file.startLine).toBe(2)
    expect(data.file.content).toBe('b')
  })

  test('offset=0 is allowed and reports startLine=0', async () => {
    const filePath = join(tmpRoot, 'offset-0.txt')
    writeFileSync(filePath, 'a\nb\nc', 'utf8')

    const data = await runRead({ file_path: filePath, offset: 0, limit: 1 })
    expect(data?.type).toBe('text')
    expect(data.file.startLine).toBe(0)
    expect(data.file.content).toBe('a')
  })
})

describe('FileReadTool parity: validateInput gating', () => {
  test('rejects large file when offset/limit are missing', async () => {
    const filePath = join(tmpRoot, 'large.txt')
    writeFileSync(filePath, 'a'.repeat(300_000), 'utf8')

    const result = await FileReadTool.validateInput({
      file_path: filePath,
    } as any)
    expect(result.result).toBe(false)
    expect(result.message).toContain('offset and limit')
  })

  test('rejects binary extensions as text reads', async () => {
    const filePath = join(tmpRoot, 'sound.mp3')
    writeFileSync(filePath, 'not really an mp3', 'utf8')

    const result = await FileReadTool.validateInput({
      file_path: filePath,
    } as any)
    expect(result.result).toBe(false)
    expect(result.message).toContain('cannot read binary files')
  })

  test('rejects empty image files', async () => {
    const filePath = join(tmpRoot, 'empty.png')
    writeFileSync(filePath, '', 'utf8')

    const result = await FileReadTool.validateInput({
      file_path: filePath,
    } as any)
    expect(result.result).toBe(false)
    expect(result.message).toContain('Empty image files')
  })
})
