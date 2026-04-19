type StartupEvent = 'first_render' | 'prompt_ready'

function isTruthyEnv(value: string | undefined): boolean {
  if (!value) return false
  return ['1', 'true', 'yes', 'on'].includes(value.trim().toLowerCase())
}

function isEnabled(): boolean {
  return isTruthyEnv(process.env.KODE_STARTUP_PROFILE)
}

const seen = new Set<StartupEvent>()

export function logStartupProfile(event: StartupEvent): void {
  if (!isEnabled()) return
  if (seen.has(event)) return
  seen.add(event)

  const ms = Math.round(process.uptime() * 1000)
  process.stderr.write(`[startup] ${event}=${ms}ms\n`)
}
