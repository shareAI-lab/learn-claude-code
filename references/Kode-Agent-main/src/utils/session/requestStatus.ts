export type RequestStatusKind = 'idle' | 'thinking' | 'streaming' | 'tool'

export type RequestStatus = {
  kind: RequestStatusKind
  detail?: string
  updatedAt: number
}

let current: RequestStatus = { kind: 'idle', updatedAt: Date.now() }
const listeners = new Set<(status: RequestStatus) => void>()

export function getRequestStatus(): RequestStatus {
  return current
}

export function setRequestStatus(
  status: Omit<RequestStatus, 'updatedAt'>,
): void {
  current = { ...status, updatedAt: Date.now() }
  for (const listener of listeners) listener(current)
}

export function subscribeRequestStatus(
  listener: (status: RequestStatus) => void,
): () => void {
  listeners.add(listener)
  return () => listeners.delete(listener)
}
