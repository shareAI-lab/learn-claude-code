export type SessionPlugin = {
  name: string
  rootDir: string
  manifestPath: string
  manifest: unknown
  commandsDirs: string[]
  skillsDirs: string[]
  agentsDirs: string[]
  hooksFiles: string[]
  outputStylesDirs: string[]
  mcpConfigFiles: string[]
}

let sessionPlugins: SessionPlugin[] = []

export function setSessionPlugins(next: SessionPlugin[]): void {
  sessionPlugins = next
}

export function getSessionPlugins(): SessionPlugin[] {
  return sessionPlugins
}

export function clearSessionPlugins(): void {
  sessionPlugins = []
}

export function __resetSessionPluginsForTests(): void {
  sessionPlugins = []
}
