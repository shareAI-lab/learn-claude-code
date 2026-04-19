import { randomUUID } from 'crypto'

let currentSessionId: string = randomUUID()

export function setKodeAgentSessionId(nextSessionId: string): void {
  currentSessionId = nextSessionId
}

export function resetKodeAgentSessionIdForTests(): void {
  currentSessionId = randomUUID()
}

export function getKodeAgentSessionId(): string {
  return currentSessionId
}
