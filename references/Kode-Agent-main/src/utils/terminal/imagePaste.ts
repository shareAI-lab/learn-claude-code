import { execSync } from 'child_process'
import { readFileSync } from 'fs'

const SCREENSHOT_PATH = '/tmp/kode_cli_latest_screenshot.png'

export const CLIPBOARD_ERROR_MESSAGE =
  'No image found in clipboard. Use Cmd + Ctrl + Shift + 4 to copy a screenshot to clipboard.'

export function getImageFromClipboard(): string | null {
  if (process.platform !== 'darwin') {
    return null
  }

  try {
    execSync(`osascript -e 'the clipboard as «class PNGf»'`, {
      stdio: 'ignore',
    })

    execSync(
      `osascript -e 'set png_data to (the clipboard as «class PNGf»)' -e 'set fp to open for access POSIX file "${SCREENSHOT_PATH}" with write permission' -e 'write png_data to fp' -e 'close access fp'`,
      { stdio: 'ignore' },
    )

    const imageBuffer = readFileSync(SCREENSHOT_PATH)
    const base64Image = imageBuffer.toString('base64')

    execSync(`rm -f "${SCREENSHOT_PATH}"`, { stdio: 'ignore' })

    return base64Image
  } catch {
    return null
  }
}
