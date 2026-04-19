import { getProjectDocs } from '@context'
import { debug as debugLogger } from '@utils/log/debugLogger'
import { logError } from '@utils/log'

class KodeContextManager {
  private static instance: KodeContextManager
  private projectDocsCache = ''
  private cacheInitialized = false
  private initPromise: Promise<void> | null = null

  static getInstance(): KodeContextManager {
    if (!KodeContextManager.instance) {
      KodeContextManager.instance = new KodeContextManager()
    }
    return KodeContextManager.instance
  }

  private async initialize(): Promise<void> {
    if (this.initPromise) return this.initPromise

    this.initPromise = (async () => {
      try {
        const projectDocs = await getProjectDocs()
        this.projectDocsCache = projectDocs || ''
        this.cacheInitialized = true
      } catch (error) {
        logError(error)
        debugLogger.warn('KODE_CONTEXT_LOAD_FAILED', {
          error: error instanceof Error ? error.message : String(error),
        })
        this.projectDocsCache = ''
        this.cacheInitialized = true
      }
    })()

    return this.initPromise
  }

  public getKodeContext(): string {
    if (!this.cacheInitialized) {
      this.initialize().catch(error => {
        logError(error)
        debugLogger.warn('KODE_CONTEXT_LOAD_FAILED', {
          error: error instanceof Error ? error.message : String(error),
        })
      })
      return ''
    }
    return this.projectDocsCache
  }

  public async refreshCache(): Promise<void> {
    this.cacheInitialized = false
    this.initPromise = null
    await this.initialize()
  }
}

const kodeContextManager = KodeContextManager.getInstance()

export const generateKodeContext = (): string => {
  return kodeContextManager.getKodeContext()
}

export const refreshKodeContext = async (): Promise<void> => {
  await kodeContextManager.refreshCache()
}

if (process.env.NODE_ENV !== 'test') {
  setTimeout(() => {
    refreshKodeContext().catch(() => {})
  }, 0)
}
