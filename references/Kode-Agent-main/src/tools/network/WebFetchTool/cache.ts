interface CacheEntry {
  bytes: number
  code: number
  codeText: string
  content: string
  contentType: string
  timestamp: number
}

class URLCache {
  private cache = new Map<string, CacheEntry>()
  private readonly CACHE_DURATION = 15 * 60 * 1000

  set(url: string, entry: Omit<CacheEntry, 'timestamp'>): void {
    this.cache.set(url, {
      ...entry,
      timestamp: Date.now(),
    })
  }

  get(url: string): CacheEntry | null {
    const entry = this.cache.get(url)
    if (!entry) {
      return null
    }

    if (Date.now() - entry.timestamp > this.CACHE_DURATION) {
      this.cache.delete(url)
      return null
    }

    return entry
  }

  clear(): void {
    this.cache.clear()
  }

  private cleanExpired(): void {
    const now = Date.now()
    for (const [url, entry] of this.cache.entries()) {
      if (now - entry.timestamp > this.CACHE_DURATION) {
        this.cache.delete(url)
      }
    }
  }

  constructor() {
    setInterval(
      () => {
        this.cleanExpired()
      },
      5 * 60 * 1000,
    )
  }
}

export const urlCache = new URLCache()
