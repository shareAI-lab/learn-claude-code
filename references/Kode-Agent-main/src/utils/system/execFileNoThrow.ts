import { execFile } from 'child_process'
import { getCwd } from '@utils/state'
import { logError } from '@utils/log'

const MS_IN_SECOND = 1000
const SECONDS_IN_MINUTE = 60

export function execFileNoThrow(
  file: string,
  args: string[],
  abortSignal?: AbortSignal,
  timeout = 10 * SECONDS_IN_MINUTE * MS_IN_SECOND,
  preserveOutputOnError = true,
): Promise<{ stdout: string; stderr: string; code: number }> {
  return new Promise(resolve => {
    try {
      execFile(
        file,
        args,
        {
          maxBuffer: 1_000_000,
          signal: abortSignal,
          timeout,
          cwd: getCwd(),
        },
        (error, stdout, stderr) => {
          if (error) {
            if (preserveOutputOnError) {
              const errorCode = typeof error.code === 'number' ? error.code : 1
              resolve({
                stdout: stdout || '',
                stderr: stderr || '',
                code: errorCode,
              })
            } else {
              resolve({ stdout: '', stderr: '', code: 1 })
            }
          } else {
            resolve({ stdout, stderr, code: 0 })
          }
        },
      )
    } catch (error) {
      logError(error)
      resolve({ stdout: '', stderr: '', code: 1 })
    }
  })
}
