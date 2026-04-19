
import { existsSync } from 'fs'
import { appendFile, mkdir, open, readFile, stat, writeFile } from 'fs/promises'
import { dirname } from 'path'
import { logError } from '@utils/log'

export async function readFileBun(filepath: string): Promise<string | null> {
  try {
    if (!existsSync(filepath)) {
      return null
    }
    return await readFile(filepath, 'utf8')
  } catch (error) {
    logError(`readFileBun error for ${filepath}: ${error}`)
    return null
  }
}

export async function writeFileBun(
  filepath: string,
  content: string | Buffer,
): Promise<boolean> {
  try {
    await mkdir(dirname(filepath), { recursive: true })
    await writeFile(filepath, content)
    return true
  } catch (error) {
    logError(`writeFileBun error for ${filepath}: ${error}`)
    return false
  }
}

export function fileExistsBun(filepath: string): boolean {
  return existsSync(filepath)
}

export async function getFileSizeBun(filepath: string): Promise<number> {
  try {
    if (!existsSync(filepath)) {
      return 0
    }
    const s = await stat(filepath)
    return s.size
  } catch (error) {
    logError(`getFileSizeBun error for ${filepath}: ${error}`)
    return 0
  }
}

export async function readPartialFileBun(
  filepath: string,
  maxBytes?: number,
): Promise<string | null> {
  try {
    if (!existsSync(filepath)) {
      return null
    }
    if (!maxBytes) {
      return await readFile(filepath, 'utf8')
    }
    const handle = await open(filepath, 'r')
    try {
      const buffer = Buffer.alloc(maxBytes)
      const { bytesRead } = await handle.read(buffer, 0, maxBytes, 0)
      return buffer.subarray(0, bytesRead).toString('utf8')
    } finally {
      try {
        await handle.close()
      } catch {}
    }
  } catch (error) {
    logError(`readPartialFileBun error for ${filepath}: ${error}`)
    return null
  }
}

export async function appendFileBun(
  filepath: string,
  content: string,
): Promise<boolean> {
  try {
    await mkdir(dirname(filepath), { recursive: true })
    await appendFile(filepath, content, 'utf8')
    return true
  } catch (error) {
    logError(`appendFileBun error for ${filepath}: ${error}`)
    return false
  }
}
