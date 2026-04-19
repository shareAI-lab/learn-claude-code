import { describe, expect, test } from 'bun:test'
import {
  BunShell,
  renderBackgroundShellStatusAttachment,
} from '@utils/bun/shell'

function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms))
}

describe('background_shell_status attachments parity (Reference CLI Bz5)', () => {
  test('running task with new output emits output-file hint', async () => {
    if (process.platform === 'win32') return

    BunShell.restart()
    const shell = BunShell.getInstance()

    const { bashId } = shell.execInBackground('echo hi; sleep 1', 10_000)
    await sleep(200)

    const attachments = shell.flushBackgroundShellStatusAttachments()
    const running = attachments.find(a => a.taskId === bashId)
    expect(running).toBeTruthy()

    const text = renderBackgroundShellStatusAttachment(running!)
    expect(text).toContain(`Background bash ${bashId} has new output:`)
    expect(text).toContain(`Read ${running!.outputFile} to see output.`)
  })
})
