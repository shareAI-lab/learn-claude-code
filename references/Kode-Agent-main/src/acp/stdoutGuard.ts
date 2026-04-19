import { format } from 'node:util'

type WriteFn = typeof process.stdout.write

type GuardHandle = {
  writeAcpLine: (line: string) => void
  restore: () => void
  originalStdoutWrite: WriteFn
}

function writeTo(
  write: WriteFn,
  chunk: unknown,
  encoding?: BufferEncoding,
  cb?: (err?: Error | null) => void,
): boolean {
  if (typeof encoding === 'function') {
    return write(chunk as any, undefined as any, encoding as any)
  }
  return write(chunk as any, encoding as any, cb as any)
}

export function installStdoutGuard(): GuardHandle {
  const originalStdoutWrite = process.stdout.write.bind(process.stdout)
  const originalStderrWrite = process.stderr.write.bind(process.stderr)

  const originalConsoleLog = console.log.bind(console)
  const originalConsoleInfo = console.info.bind(console)
  const originalConsoleDebug = console.debug.bind(console)
  const originalConsoleWarn = console.warn.bind(console)
  const originalConsoleError = console.error.bind(console)

  const writeAcpLine = (line: string) => {
    writeTo(originalStdoutWrite, `${line}\n`)
  }

  const writeLogToStderr = (...args: unknown[]) => {
    writeTo(originalStderrWrite, `${format(...args)}\n`)
  }

  console.log = writeLogToStderr as any
  console.info = writeLogToStderr as any
  console.debug = writeLogToStderr as any
  console.warn = writeLogToStderr as any
  console.error = writeLogToStderr as any

  process.stdout.write = ((chunk: any, encoding?: any, cb?: any) => {
    return writeTo(originalStderrWrite, chunk, encoding, cb)
  }) as any

  const restore = () => {
    process.stdout.write = originalStdoutWrite as any
    console.log = originalConsoleLog as any
    console.info = originalConsoleInfo as any
    console.debug = originalConsoleDebug as any
    console.warn = originalConsoleWarn as any
    console.error = originalConsoleError as any
  }

  return { writeAcpLine, restore, originalStdoutWrite }
}

