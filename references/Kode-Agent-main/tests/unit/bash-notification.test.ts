import { describe, expect, test } from 'bun:test'
import { BunShell, renderBashNotification } from '@utils/bun/shell'

function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms))
}

describe('bash-notification parity (Reference CLI Rt1)', () => {
  test('completed task notifies once and includes output-file + read instruction', async () => {
    if (process.platform === 'win32') return

    BunShell.restart()
    const shell = BunShell.getInstance()

    const { bashId } = shell.execInBackground('echo done', 10_000)

    for (let i = 0; i < 50; i++) {
      const bg = shell.getBackgroundOutput(bashId)
      if (bg && bg.code !== null) break
      await sleep(50)
    }

    const [notification] = shell.flushBashNotifications()
    expect(notification).toBeTruthy()
    expect(notification!.taskId).toBe(bashId)
    expect(notification!.status).toBe('completed')

    const text = renderBashNotification(notification!)
    expect(text).toContain('<bash-notification>')
    expect(text).toContain(`<shell-id>${bashId}</shell-id>`)
    expect(text).toContain(
      `<output-file>${notification!.outputFile}</output-file>`,
    )
    expect(text).toContain('<status>completed</status>')
    expect(text).toContain('Read the output file to retrieve the output.')

    const none = shell.flushBashNotifications()
    expect(none.length).toBe(0)
  })

  test('killed task notifies with status killed', async () => {
    if (process.platform === 'win32') return

    BunShell.restart()
    const shell = BunShell.getInstance()

    const { bashId } = shell.execInBackground('sleep 10', 10_000)
    await sleep(100)
    expect(shell.killBackgroundShell(bashId)).toBe(true)

    const [notification] = shell.flushBashNotifications()
    expect(notification).toBeTruthy()
    expect(notification!.taskId).toBe(bashId)
    expect(notification!.status).toBe('killed')

    const text = renderBashNotification(notification!)
    expect(text).toContain('<status>killed</status>')
    expect(text).toContain('was killed')
  })

  test('failed task notifies with status failed and exit code', async () => {
    if (process.platform === 'win32') return

    BunShell.restart()
    const shell = BunShell.getInstance()

    const { bashId } = shell.execInBackground('exit 42', 10_000)

    for (let i = 0; i < 50; i++) {
      const bg = shell.getBackgroundOutput(bashId)
      if (bg && bg.code !== null) break
      await sleep(50)
    }

    const [notification] = shell.flushBashNotifications()
    expect(notification).toBeTruthy()
    expect(notification!.taskId).toBe(bashId)
    expect(notification!.status).toBe('failed')
    expect(notification!.exitCode).toBe(42)

    const text = renderBashNotification(notification!)
    expect(text).toContain('<status>failed</status>')
    expect(text).toContain('failed with exit code 42')
  })
})
