import { execFileNoThrow } from './execFileNoThrow'

export async function openBrowser(url: string): Promise<boolean> {
  const platform = process.platform
  const command =
    platform === 'win32' ? 'start' : platform === 'darwin' ? 'open' : 'xdg-open'

  try {
    const { code } = await execFileNoThrow(command, [url])
    return code === 0
  } catch (_) {
    return false
  }
}
