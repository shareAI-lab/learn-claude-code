import { describe, expect, test } from 'bun:test'
import { FileEditTool } from '@tools/FileEditTool/FileEditTool'
import { FileWriteTool } from '@tools/FileWriteTool/FileWriteTool'

describe('Regression: rejected tool messages are sync', () => {
  test('FileWriteTool.renderToolUseRejectedMessage does not return a Promise', () => {
    const result = FileWriteTool.renderToolUseRejectedMessage(
      { file_path: '/tmp/kode-test-nonexistent.txt', content: 'hello' },
      { columns: 80, verbose: false },
    )

    expect(result).not.toBeInstanceOf(Promise)
  })

  test('FileEditTool.renderToolUseRejectedMessage does not return a Promise', () => {
    const result = FileEditTool.renderToolUseRejectedMessage(
      {
        file_path: '/tmp/kode-test-nonexistent.txt',
        old_string: '',
        new_string: 'hello',
        replace_all: false,
      },
      { columns: 80, verbose: false },
    )

    expect(result).not.toBeInstanceOf(Promise)
  })
})
