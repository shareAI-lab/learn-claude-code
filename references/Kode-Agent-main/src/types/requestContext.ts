// Request Context for perfect state isolation
// Based on official Kode patterns

export interface RequestContext {
  id: string
  abortController: AbortController
  startTime: number
  isActive: boolean
  type: 'query' | 'tool' | 'koding'
}

export interface AbortBarrier {
  requestId: string
  checkAbort(): boolean
  onAbort(callback: () => void): void
  cleanup(): void
}

export function createRequestContext(
  type: RequestContext['type'] = 'query',
): RequestContext {
  return {
    id: crypto.randomUUID(),
    abortController: new AbortController(),
    startTime: Date.now(),
    isActive: true,
    type,
  }
}

export function createAbortBarrier(
  requestContext: RequestContext,
): AbortBarrier {
  let cleanupCallbacks: (() => void)[] = []

  return {
    requestId: requestContext.id,

    checkAbort(): boolean {
      // Only respond to aborts for THIS specific request
      return (
        requestContext.isActive && requestContext.abortController.signal.aborted
      )
    },

    onAbort(callback: () => void): void {
      if (requestContext.isActive) {
        const abortHandler = () => {
          if (requestContext.isActive) {
            callback()
          }
        }
        requestContext.abortController.signal.addEventListener(
          'abort',
          abortHandler,
        )
        cleanupCallbacks.push(() => {
          requestContext.abortController.signal.removeEventListener(
            'abort',
            abortHandler,
          )
        })
      }
    },

    cleanup(): void {
      cleanupCallbacks.forEach(cleanup => cleanup())
      cleanupCallbacks = []
      requestContext.isActive = false
    },
  }
}
