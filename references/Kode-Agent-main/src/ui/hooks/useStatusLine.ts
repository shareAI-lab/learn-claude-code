import { useEffect, useRef, useState } from 'react'
import { BunShell } from '@utils/bun/shell'
import { getStatusLineCommand } from '@services/statusline'

function normalizeStatusLineText(value: string): string {
  const singleLine = value.replace(/\r?\n/g, ' ').trim()
  return singleLine.length > 300 ? `${singleLine.slice(0, 300)}…` : singleLine
}

export function useStatusLine(): string | null {
  const [text, setText] = useState<string | null>(null)
  const lastCommandRef = useRef<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => {
    const enabled =
      process.env.KODE_STATUSLINE_ENABLED === '1' ||
      process.env.NODE_ENV !== 'test'
    if (!enabled) return

    const shell = BunShell.getInstance()
    let alive = true

    const tick = async () => {
      const command = getStatusLineCommand()
      if (!command) {
        lastCommandRef.current = null
        abortRef.current?.abort()
        abortRef.current = null
        if (alive) setText(null)
        return
      }

      lastCommandRef.current = command
      abortRef.current?.abort()
      const ac = new AbortController()
      abortRef.current = ac

      const result = await shell.exec(command, ac.signal, 1000)
      if (!alive) return
      if (result.interrupted) return

      const raw =
        result.code === 0 ? result.stdout : result.stdout || result.stderr
      const next = raw ? normalizeStatusLineText(raw) : ''
      setText(next || null)
    }

    tick().catch(() => {})
    const id = setInterval(() => {
      tick().catch(() => {})
    }, 2000)

    return () => {
      alive = false
      clearInterval(id)
      abortRef.current?.abort()
    }
  }, [])

  return text
}
