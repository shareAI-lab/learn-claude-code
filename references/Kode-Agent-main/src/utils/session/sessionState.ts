type SessionState = {
  modelErrors: Record<string, unknown>
  currentError: string | null
}

const isDebug =
  process.argv.includes('--debug') ||
  process.argv.includes('-d') ||
  process.env.DEBUG === 'true'

const sessionState: SessionState = {
  modelErrors: {},
  currentError: null,
} as const

function setSessionState<K extends keyof SessionState>(
  key: K,
  value: SessionState[K],
): void
function setSessionState(partialState: Partial<SessionState>): void
function setSessionState(
  keyOrState: keyof SessionState | Partial<SessionState>,
  value?: any,
): void {
  if (typeof keyOrState === 'string') {
    sessionState[keyOrState] = value
  } else {
    Object.assign(sessionState, keyOrState)
  }
}

function getSessionState(): SessionState
function getSessionState<K extends keyof SessionState>(key: K): SessionState[K]
function getSessionState<K extends keyof SessionState>(key?: K) {
  return key === undefined ? sessionState : sessionState[key]
}

export type { SessionState }
export { setSessionState, getSessionState }
export default sessionState
