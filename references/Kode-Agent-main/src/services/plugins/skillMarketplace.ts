import {
  copyFileSync,
  existsSync,
  lstatSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  renameSync,
  rmSync,
  writeFileSync,
} from 'node:fs'
import { randomUUID } from 'node:crypto'
import { homedir } from 'node:os'
import { basename, dirname, join, resolve, sep } from 'node:path'
import { unzipSync } from 'fflate'
import { z } from 'zod'
import { CONFIG_BASE_DIR } from '@constants/product'
import { getCwd } from '@utils/state'
import { getKodeBaseDir } from '@utils/config/env'

const KNOWN_MARKETPLACES_FILE = 'known_marketplaces.json'
const MARKETPLACES_CACHE_DIR = 'marketplaces'
const INSTALLED_SKILL_PLUGINS_FILE = 'installed-skill-plugins.json'

const MarketplaceSourceSchema = z.discriminatedUnion('source', [
  z.strictObject({
    source: z.literal('github'),
    repo: z.string().min(3),
    ref: z.string().optional(),
    path: z.string().optional(),
  }),
  z.strictObject({
    source: z.literal('git'),
    url: z.string().min(3),
    ref: z.string().optional(),
    path: z.string().optional(),
  }),
  z.strictObject({
    source: z.literal('url'),
    url: z.string().url(),
    headers: z.record(z.string(), z.string()).optional(),
  }),
  z.strictObject({
    source: z.literal('npm'),
    package: z.string().min(1),
  }),
  z.strictObject({
    source: z.literal('file'),
    path: z.string().min(1),
  }),
  z.strictObject({
    source: z.literal('directory'),
    path: z.string().min(1),
  }),
])

export type MarketplaceSource = z.infer<typeof MarketplaceSourceSchema>

const MarketplacePathListSchema = z.preprocess(value => {
  if (typeof value === 'string') return [value]
  return value
}, z.array(z.string()))

const MarketplacePluginSchema = z
  .object({
    name: z.string().min(1),
    description: z.string().optional(),
    source: z.string().optional().default('./'),
    strict: z.boolean().optional(),
    skills: MarketplacePathListSchema.optional(),
    commands: MarketplacePathListSchema.optional(),
  })
  .passthrough()

export const MarketplaceManifestSchema = z
  .object({
    $schema: z.string().optional(),
    description: z.string().optional(),
    name: z.string().min(1),
    owner: z
      .object({
        name: z.string().optional(),
        email: z.string().optional(),
      })
      .passthrough()
      .optional(),
    metadata: z.record(z.string(), z.unknown()).optional().default({}),
    plugins: z.array(MarketplacePluginSchema).default([]),
  })
  .passthrough()

export type MarketplaceManifest = z.infer<typeof MarketplaceManifestSchema>
export type PluginEntry = MarketplaceManifest['plugins'][number]

const KnownMarketplacesSchema = z.record(
  z.string(),
  z.strictObject({
    source: MarketplaceSourceSchema,
    installLocation: z.string().min(1),
    lastUpdated: z.string().min(1),
    autoUpdate: z.boolean().optional(),
  }),
)

export type KnownMarketplacesConfig = z.infer<typeof KnownMarketplacesSchema>

export type PluginScope = 'user' | 'project' | 'local'

type InstalledSkillPlugin = {
  plugin: string
  marketplace: string
  scope: PluginScope
  kind?: 'skill-pack' | 'plugin-pack'
  isEnabled?: boolean
  projectPath?: string
  installedAt: string
  pluginRoot?: string
  skills: string[]
  commands: string[]
  sourceMarketplacePath: string
}

type InstalledSkillPluginsFile = Record<string, InstalledSkillPlugin>

function userKodeDir(): string {
  return getKodeBaseDir()
}

function normalizePluginScope(options?: {
  scope?: PluginScope
  project?: boolean
}): PluginScope {
  if (
    options?.scope === 'user' ||
    options?.scope === 'project' ||
    options?.scope === 'local'
  ) {
    return options.scope
  }
  if (options?.project === true) return 'project'
  return 'user'
}

function scopeBaseDir(scope: PluginScope): string {
  if (scope === 'user') return userKodeDir()
  return join(getCwd(), CONFIG_BASE_DIR)
}

function scopeSkillsDir(scope: PluginScope): string {
  return join(scopeBaseDir(scope), 'skills')
}

function scopeCommandsDir(scope: PluginScope): string {
  return join(scopeBaseDir(scope), 'commands')
}

function scopeDisabledSkillsDir(scope: PluginScope): string {
  return join(scopeBaseDir(scope), 'skills.disabled')
}

function scopeDisabledCommandsDir(scope: PluginScope): string {
  return join(scopeBaseDir(scope), 'commands.disabled')
}

function scopeInstalledPluginsDir(scope: PluginScope): string {
  return join(scopeBaseDir(scope), 'plugins', 'installed')
}

function scopeInstalledPluginRoot(
  scope: PluginScope,
  plugin: string,
  marketplace: string,
): string {
  return join(scopeInstalledPluginsDir(scope), plugin, marketplace)
}

function pluginsDir(): string {
  return join(userKodeDir(), 'plugins')
}

function knownMarketplacesConfigPath(): string {
  return join(pluginsDir(), KNOWN_MARKETPLACES_FILE)
}

function marketplaceCacheBaseDir(): string {
  return join(pluginsDir(), MARKETPLACES_CACHE_DIR)
}

function installedSkillPluginsPath(): string {
  return join(userKodeDir(), INSTALLED_SKILL_PLUGINS_FILE)
}

function ensureDir(path: string): void {
  mkdirSync(path, { recursive: true })
}

function readJsonFile<T>(path: string, fallback: T): T {
  try {
    if (!existsSync(path)) return fallback
    const raw = readFileSync(path, 'utf8')
    return JSON.parse(raw) as T
  } catch {
    return fallback
  }
}

function writeJsonFile(path: string, value: unknown): void {
  ensureDir(dirname(path))
  writeFileSync(path, `${JSON.stringify(value, null, 2)}\n`, 'utf8')
}

function normalizeMarketplaceSubPath(path: string | undefined): string | null {
  if (!path) return null
  const trimmed = path
    .trim()
    .replace(/^\.?\//, '')
    .replace(/^\/+/, '')
  if (!trimmed) return null
  if (trimmed.includes('..')) {
    throw new Error(`Marketplace path contains '..': ${path}`)
  }
  return trimmed.replace(/\\/g, '/').replace(/\/+$/, '')
}

function safeJoinWithin(baseDir: string, relativePath: string): string {
  const normalized = relativePath.replace(/\\/g, '/')
  if (!normalized || normalized.startsWith('/') || normalized.includes('..')) {
    throw new Error(`Unsafe path in archive: ${relativePath}`)
  }
  const joined = resolve(baseDir, normalized.split('/').join(sep))
  const resolvedBase = resolve(baseDir)
  if (!joined.startsWith(resolvedBase + sep) && joined !== resolvedBase) {
    throw new Error(`Path traversal detected: ${relativePath}`)
  }
  return joined
}

function ensureEmptyDir(path: string): void {
  if (existsSync(path)) rmSync(path, { recursive: true, force: true })
  ensureDir(path)
}

function safeCopyDirectory(srcDir: string, destDir: string): void {
  ensureDir(destDir)
  const entries = readdirSync(srcDir, { withFileTypes: true })
  for (const entry of entries) {
    const srcPath = join(srcDir, entry.name)
    const destPath = join(destDir, entry.name)

    if (entry.isDirectory()) {
      safeCopyDirectory(srcPath, destPath)
      continue
    }

    if (entry.isFile()) {
      ensureDir(dirname(destPath))
      copyFileSync(srcPath, destPath)
      continue
    }

  }
}

function readMarketplaceFromDirectory(rootDir: string): MarketplaceManifest {
  const primaryMarketplaceFile = resolve(
    rootDir,
    '.kode-plugin',
    'marketplace.json',
  )
  const legacyMarketplaceFile = resolve(
    rootDir,
    '.claude-plugin',
    'marketplace.json',
  )
  const marketplaceFile = existsSync(primaryMarketplaceFile)
    ? primaryMarketplaceFile
    : legacyMarketplaceFile
  if (!existsSync(marketplaceFile)) {
    throw new Error(
      `Marketplace file not found (expected .kode-plugin/marketplace.json or .claude-plugin/marketplace.json)`,
    )
  }
  const raw = readFileSync(marketplaceFile, 'utf8')
  const parsed = MarketplaceManifestSchema.safeParse(JSON.parse(raw))
  if (!parsed.success) {
    throw new Error(
      `Invalid marketplace.json: ${parsed.error.issues.map(i => i.message).join('; ')}`,
    )
  }
  return parsed.data
}

export function parsePluginSpec(spec: string): {
  plugin: string
  marketplace: string
} {
  const trimmed = spec.trim()
  const parts = trimmed.split('@')
  if (parts.length !== 2) {
    throw new Error(
      `Invalid plugin spec: ${spec}. Expected format: <plugin>@<marketplace>`,
    )
  }
  const plugin = parts[0]!.trim()
  const marketplace = parts[1]!.trim()
  if (!plugin || !marketplace) {
    throw new Error(
      `Invalid plugin spec: ${spec}. Expected format: <plugin>@<marketplace>`,
    )
  }
  return { plugin, marketplace }
}

function resolvePluginForInstall(pluginInput: string): {
  plugin: string
  marketplace: string
  pluginSpec: string
} {
  const trimmed = pluginInput.trim()
  if (!trimmed) throw new Error('Plugin is required')

  if (trimmed.includes('@')) {
    const resolved = parsePluginSpec(trimmed)
    return {
      ...resolved,
      pluginSpec: `${resolved.plugin}@${resolved.marketplace}`,
    }
  }

  const config = loadKnownMarketplaces()
  const matches: { marketplace: string; entry: PluginEntry }[] = []
  for (const [marketplace, entry] of Object.entries(config)) {
    try {
      const manifest = readMarketplaceFromDirectory(entry.installLocation)
      const found = manifest.plugins.find(p => p.name === trimmed)
      if (found) matches.push({ marketplace, entry: found })
    } catch {
    }
  }

  if (matches.length === 0) {
    const availableMarketplaces = Object.keys(config).sort().join(', ')
    throw new Error(
      `Plugin '${trimmed}' not found in any marketplace. Available marketplaces: ${availableMarketplaces || '(none)'}`,
    )
  }

  if (matches.length > 1) {
    const options = matches
      .map(m => `${trimmed}@${m.marketplace}`)
      .sort()
      .join(', ')
    throw new Error(
      `Plugin '${trimmed}' is available in multiple marketplaces. Use an explicit spec: ${options}`,
    )
  }

  return {
    plugin: trimmed,
    marketplace: matches[0]!.marketplace,
    pluginSpec: `${trimmed}@${matches[0]!.marketplace}`,
  }
}

function resolveInstalledPluginSpec(
  pluginInput: string,
  state: InstalledSkillPluginsFile,
): string {
  const trimmed = pluginInput.trim()
  if (!trimmed) throw new Error('Plugin is required')

  if (trimmed.includes('@')) {
    parsePluginSpec(trimmed)
    return trimmed
  }

  const matches = Object.entries(state).filter(
    ([, record]) => record?.plugin === trimmed,
  )
  if (matches.length === 0) {
    throw new Error(`Plugin '${trimmed}' is not installed`)
  }
  if (matches.length > 1) {
    const options = matches
      .map(([spec]) => spec)
      .sort()
      .join(', ')
    throw new Error(
      `Plugin '${trimmed}' is installed from multiple marketplaces. Use an explicit spec: ${options}`,
    )
  }
  return matches[0]![0]
}

function baseDirForInstallRecord(record: InstalledSkillPlugin): string {
  if (record.scope === 'user') return userKodeDir()
  const projectPath =
    typeof record.projectPath === 'string' ? record.projectPath.trim() : ''
  if (!projectPath) {
    throw new Error(
      `Installed plugin '${record.plugin}@${record.marketplace}' is missing projectPath for scope=${record.scope}`,
    )
  }
  return join(projectPath, CONFIG_BASE_DIR)
}

function githubRepoFromUrl(input: string): string | null {
  const ssh = input.match(/^git@github\.com:([^/]+\/[^/]+?)(?:\.git)?$/)
  if (ssh?.[1]) return ssh[1]
  const https = input.match(
    /^https?:\/\/github\.com\/([^/]+\/[^/]+?)(?:\.git)?$/,
  )
  if (https?.[1]) return https[1]
  return null
}

function parseRefAndPath(input: string): {
  base: string
  ref?: string
  path?: string
} {
  const [beforeHash, hashPart] = input.split('#', 2)
  const [base, refPart] = beforeHash.split('@', 2)
  return {
    base,
    ref: refPart?.trim() || undefined,
    path: hashPart?.trim() || undefined,
  }
}

function parseMarketplaceSourceInput(sourceInput: string): MarketplaceSource {
  const raw = sourceInput.trim()
  if (!raw) throw new Error('Marketplace source is required')

  for (const prefix of [
    'github:',
    'git:',
    'url:',
    'npm:',
    'file:',
    'dir:',
  ] as const) {
    if (raw.startsWith(prefix)) {
      const rest = raw.slice(prefix.length).trim()
      const parsed = parseRefAndPath(rest)
      if (prefix === 'github:') {
        return {
          source: 'github',
          repo: parsed.base.trim(),
          ...(parsed.ref ? { ref: parsed.ref } : {}),
          ...(parsed.path ? { path: parsed.path } : {}),
        }
      }
      if (prefix === 'git:') {
        const repo = githubRepoFromUrl(parsed.base.trim())
        if (repo) {
          return {
            source: 'github',
            repo,
            ...(parsed.ref ? { ref: parsed.ref } : {}),
            ...(parsed.path ? { path: parsed.path } : {}),
          }
        }
        return {
          source: 'git',
          url: parsed.base.trim(),
          ...(parsed.ref ? { ref: parsed.ref } : {}),
          ...(parsed.path ? { path: parsed.path } : {}),
        }
      }
      if (prefix === 'url:') {
        return { source: 'url', url: rest }
      }
      if (prefix === 'npm:') {
        return { source: 'npm', package: rest }
      }
      if (prefix === 'file:') {
        return { source: 'file', path: rest }
      }
      if (prefix === 'dir:') {
        return { source: 'directory', path: rest }
      }
    }
  }

  const resolved = resolve(raw)
  if (existsSync(resolved)) {
    const stat = lstatSync(resolved)
    if (stat.isDirectory()) return { source: 'directory', path: resolved }
    if (stat.isFile()) return { source: 'file', path: resolved }
    throw new Error(`Marketplace source must be a directory or file: ${raw}`)
  }

  const parsed = parseRefAndPath(raw)
  if (/^[^/\s]+\/[^/\s]+$/.test(parsed.base)) {
    return {
      source: 'github',
      repo: parsed.base,
      ...(parsed.ref ? { ref: parsed.ref } : {}),
      ...(parsed.path ? { path: parsed.path } : {}),
    }
  }

  const repo = githubRepoFromUrl(parsed.base)
  if (repo) {
    return {
      source: 'github',
      repo,
      ...(parsed.ref ? { ref: parsed.ref } : {}),
      ...(parsed.path ? { path: parsed.path } : {}),
    }
  }

  if (/^https?:\/\//.test(raw)) {
    return { source: 'url', url: raw }
  }

  throw new Error(
    `Unsupported marketplace source: ${sourceInput}. Use a local path, "owner/repo", or prefixes like github:, git:, url:, file:, dir:.`,
  )
}

async function fetchBinary(url: string): Promise<Uint8Array> {
  const resp = await fetch(url, { method: 'GET' })
  if (!resp.ok) {
    throw new Error(
      `Failed to download ${url}: ${resp.status} ${resp.statusText}`,
    )
  }
  const buf = await resp.arrayBuffer()
  return new Uint8Array(buf)
}

async function tryDownloadGithubZip(
  repo: string,
  ref: string,
): Promise<Uint8Array> {
  const [owner, name] = repo.split('/', 2)
  if (!owner || !name) throw new Error(`Invalid GitHub repo: ${repo}`)

  const candidates = ref.startsWith('refs/')
    ? [ref]
    : [`refs/heads/${ref}`, `refs/tags/${ref}`]

	  let lastError: Error | null = null
	  for (const candidate of candidates) {
	    const url = `https://codeload.github.com/${owner}/${name}/zip/${candidate}`
	    try {
	      return await fetchBinary(url)
	    } catch (err) {
	      lastError = err instanceof Error ? err : Error(String(err))
	    }
  }
  throw lastError ?? new Error(`Failed to download GitHub repo ${repo}@${ref}`)
}

async function cacheMarketplaceToTempDir(
  source: MarketplaceSource,
  tempDir: string,
): Promise<void> {
  ensureEmptyDir(tempDir)

  if (source.source === 'directory') {
    const root = resolve(source.path)
    if (!existsSync(root) || !lstatSync(root).isDirectory()) {
      throw new Error(`Directory not found: ${source.path}`)
    }
    safeCopyDirectory(root, tempDir)
    return
  }

  if (source.source === 'file') {
    const file = resolve(source.path)
    if (!existsSync(file) || !lstatSync(file).isFile()) {
      throw new Error(`File not found: ${source.path}`)
    }
    const out = join(tempDir, '.kode-plugin')
    ensureDir(out)
    copyFileSync(file, join(out, 'marketplace.json'))
    return
  }

  if (source.source === 'github') {
    const pathWithin = normalizeMarketplaceSubPath(source.path)

    const preferredRef = source.ref?.trim() || ''
    const refsToTry = preferredRef ? [preferredRef] : ['main', 'master']

    let zip: Uint8Array | null = null
    let usedRef = preferredRef || 'main'
    let lastError: Error | null = null
    for (const ref of refsToTry) {
      try {
        zip = await tryDownloadGithubZip(source.repo, ref)
        usedRef = ref
        break
      } catch (err) {
        lastError = err instanceof Error ? err : Error(String(err))
      }
    }
    if (!zip)
      throw (
        lastError ?? new Error(`Failed to download GitHub repo ${source.repo}`)
      )

    const files = unzipSync(zip)
    const names = Object.keys(files).filter(Boolean)
    const topDir = names.length > 0 ? names[0]!.split('/')[0]! : ''
    const includePrefix = pathWithin
      ? `${topDir}/${pathWithin.replace(/\/+$/, '')}/`
      : `${topDir}/`

    let extractedCount = 0
    for (const [name, data] of Object.entries(files)) {
      if (!name.startsWith(includePrefix)) continue
      const rel = name.slice(includePrefix.length)
      if (!rel) continue
      if (rel.endsWith('/')) {
        ensureDir(safeJoinWithin(tempDir, rel))
        continue
      }
      const dest = safeJoinWithin(tempDir, rel)
      ensureDir(dirname(dest))
      writeFileSync(dest, data)
      extractedCount++
    }

    if (extractedCount === 0) {
      throw new Error(
        `No files extracted from ${source.repo}@${usedRef}${pathWithin ? `#${pathWithin}` : ''}`,
      )
    }
    return
  }

  if (source.source === 'url') {
    const url = source.url
    if (url.toLowerCase().endsWith('.json')) {
      const data = await fetchBinary(url)
      const out = join(tempDir, '.kode-plugin')
      ensureDir(out)
      writeFileSync(join(out, 'marketplace.json'), Buffer.from(data))
      return
    }
    if (url.toLowerCase().endsWith('.zip')) {
      const zip = await fetchBinary(url)
      const files = unzipSync(zip)
      for (const [name, data] of Object.entries(files)) {
        if (!name || name.endsWith('/')) continue
        const dest = safeJoinWithin(tempDir, name)
        ensureDir(dirname(dest))
        writeFileSync(dest, data)
      }
      return
    }
    throw new Error(
      `Unsupported url marketplace source. Provide a .json or .zip URL: ${url}`,
    )
  }

  if (source.source === 'git') {
    const repo = githubRepoFromUrl(source.url)
    if (repo) {
      await cacheMarketplaceToTempDir(
        {
          source: 'github',
          repo,
          ...(source.ref ? { ref: source.ref } : {}),
          ...(source.path ? { path: source.path } : {}),
        },
        tempDir,
      )
      return
    }
    throw new Error(
      `git sources are not supported without GitHub conversion (url=${source.url})`,
    )
  }

  if (source.source === 'npm') {
    throw new Error(
      `npm marketplace sources are not supported yet (package=${source.package}). Install the package and add it as a local dir instead.`,
    )
  }
}

function loadKnownMarketplaces(): KnownMarketplacesConfig {
  const raw = readJsonFile<unknown>(knownMarketplacesConfigPath(), {})
  const parsed = KnownMarketplacesSchema.safeParse(raw)
  if (!parsed.success) {
    throw new Error(
      `Marketplace configuration is corrupted: ${parsed.error.issues.map(i => i.message).join('; ')}`,
    )
  }
  return parsed.data
}

function saveKnownMarketplaces(config: KnownMarketplacesConfig): void {
  const parsed = KnownMarketplacesSchema.safeParse(config)
  if (!parsed.success) {
    throw new Error(`Invalid marketplace config: ${parsed.error.message}`)
  }
  writeJsonFile(knownMarketplacesConfigPath(), parsed.data)
}

export function listMarketplaces(): KnownMarketplacesConfig {
  return loadKnownMarketplaces()
}

export async function addMarketplace(
  sourceInput: string,
): Promise<{ name: string }> {
  const source = parseMarketplaceSourceInput(sourceInput)
  const validatedSource = MarketplaceSourceSchema.safeParse(source)
  if (!validatedSource.success) {
    throw new Error(
      `Invalid marketplace source: ${validatedSource.error.issues.map(i => i.message).join('; ')}`,
    )
  }

  const config = loadKnownMarketplaces()
  const cacheBase = marketplaceCacheBaseDir()
  ensureDir(cacheBase)

  const tempDir = join(cacheBase, `tmp-${randomUUID()}`)
  try {
    await cacheMarketplaceToTempDir(validatedSource.data, tempDir)
    const manifest = readMarketplaceFromDirectory(tempDir)
    const marketplaceName = manifest.name

    if (config[marketplaceName]) {
      throw new Error(
        `Marketplace '${marketplaceName}' is already installed. Remove it first to re-add.`,
      )
    }

    const installLocation = join(cacheBase, marketplaceName)
    if (existsSync(installLocation)) {
      throw new Error(
        `Marketplace cache directory already exists: ${installLocation}`,
      )
    }

    renameSync(tempDir, installLocation)
    config[marketplaceName] = {
      source: validatedSource.data,
      installLocation,
      lastUpdated: new Date().toISOString(),
    }
    saveKnownMarketplaces(config)
    return { name: marketplaceName }
  } catch (error) {
    if (existsSync(tempDir)) rmSync(tempDir, { recursive: true, force: true })
    throw error
  }
}

export function removeMarketplace(name: string): void {
  const trimmed = name.trim()
  if (!trimmed) throw new Error('Marketplace name is required')

  const config = loadKnownMarketplaces()
  const entry = config[trimmed]
  if (!entry) throw new Error(`Marketplace '${trimmed}' not found`)

  delete config[trimmed]
  saveKnownMarketplaces(config)

  try {
    if (existsSync(entry.installLocation)) {
      rmSync(entry.installLocation, { recursive: true, force: true })
    }
  } catch {
  }
}

export async function refreshMarketplaceAsync(name: string): Promise<void> {
  const trimmed = name.trim()
  if (!trimmed) throw new Error('Marketplace name is required')

  const config = loadKnownMarketplaces()
  const entry = config[trimmed]
  if (!entry) throw new Error(`Marketplace '${trimmed}' not found`)

  const cacheBase = marketplaceCacheBaseDir()
  ensureDir(cacheBase)

  const tempDir = join(cacheBase, `tmp-${randomUUID()}`)
  try {
    await cacheMarketplaceToTempDir(entry.source, tempDir)
    const manifest = readMarketplaceFromDirectory(tempDir)
    if (manifest.name !== trimmed) {
      throw new Error(
        `Marketplace name mismatch on refresh: expected ${trimmed}, got ${manifest.name}`,
      )
    }

    if (existsSync(entry.installLocation)) {
      rmSync(entry.installLocation, { recursive: true, force: true })
    }
    renameSync(tempDir, entry.installLocation)
    config[trimmed] = {
      ...entry,
      lastUpdated: new Date().toISOString(),
    }
    saveKnownMarketplaces(config)
  } catch (error) {
    if (existsSync(tempDir)) rmSync(tempDir, { recursive: true, force: true })
    throw error
  }
}

export async function refreshAllMarketplacesAsync(
  onProgress?: (message: string) => void,
): Promise<{ refreshed: string[]; failed: { name: string; error: string }[] }> {
  const config = loadKnownMarketplaces()
  const names = Object.keys(config).sort()

  const refreshed: string[] = []
  const failed: { name: string; error: string }[] = []

  for (const name of names) {
    try {
      onProgress?.(`Updating marketplace: ${name}...`)
      await refreshMarketplaceAsync(name)
      refreshed.push(name)
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error)
      failed.push({ name, error: message })
      onProgress?.(`Failed to refresh marketplace ${name}: ${message}`)
    }
  }

  return { refreshed, failed }
}

export function getMarketplaceManifest(marketplaceName: string): {
  manifest: MarketplaceManifest
  rootDir: string
  source: MarketplaceSource
} {
  const config = loadKnownMarketplaces()
  const entry = config[marketplaceName]
  if (!entry) {
    const available = Object.keys(config).sort().join(', ')
    throw new Error(
      `Marketplace '${marketplaceName}' not found. Available marketplaces: ${available || '(none)'}`,
    )
  }
  const manifest = readMarketplaceFromDirectory(entry.installLocation)
  return { manifest, rootDir: entry.installLocation, source: entry.source }
}

function ensurePluginInstallState(): InstalledSkillPluginsFile {
  ensureDir(userKodeDir())
  const state = readJsonFile<Record<string, any>>(
    installedSkillPluginsPath(),
    {},
  )
  for (const record of Object.values(state)) {
    if (!record || typeof record !== 'object') continue
    if (
      record.scope !== 'user' &&
      record.scope !== 'project' &&
      record.scope !== 'local'
    ) {
      record.scope = 'user'
    }
    if (record.kind !== 'skill-pack' && record.kind !== 'plugin-pack') {
      record.kind =
        typeof record.pluginRoot === 'string' ? 'plugin-pack' : 'skill-pack'
    }
    if (record.isEnabled === undefined) record.isEnabled = true
  }
  return state as InstalledSkillPluginsFile
}

function savePluginInstallState(state: InstalledSkillPluginsFile): void {
  writeJsonFile(installedSkillPluginsPath(), state)
}

export function installSkillPlugin(
  pluginInput: string,
  options?: { scope?: PluginScope; project?: boolean; force?: boolean },
): {
  pluginSpec: string
  installedSkills: string[]
  installedCommands: string[]
} {
  const scope = normalizePluginScope(options)
  const { plugin, marketplace, pluginSpec } =
    resolvePluginForInstall(pluginInput)
  const { manifest, rootDir, source } = getMarketplaceManifest(marketplace)

  const entry = manifest.plugins.find(p => p.name === plugin)
  if (!entry) {
    const available = manifest.plugins
      .map(p => p.name)
      .sort()
      .join(', ')
    throw new Error(
      `Plugin '${plugin}' not found in marketplace '${marketplace}'. Available plugins: ${available || '(none)'}`,
    )
  }

  const installState = ensurePluginInstallState()
  const existing = installState[pluginSpec]
  if (existing && existing.scope !== scope && options?.force !== true) {
    throw new Error(
      `Plugin '${pluginSpec}' is already installed with scope=${existing.scope}. Uninstall it first to install with scope=${scope}.`,
    )
  }
  if (existing && options?.force !== true) {
    throw new Error(
      `Plugin '${pluginSpec}' is already installed. Re-run with --force to reinstall.`,
    )
  }

  const entrySourceBase = resolve(rootDir, entry.source ?? './')
  const primaryManifestPath = join(
    entrySourceBase,
    '.kode-plugin',
    'plugin.json',
  )
  const legacyManifestPath = join(
    entrySourceBase,
    '.claude-plugin',
    'plugin.json',
  )
  const pluginManifestPath = existsSync(primaryManifestPath)
    ? primaryManifestPath
    : legacyManifestPath

  if (
    existsSync(pluginManifestPath) &&
    lstatSync(pluginManifestPath).isFile()
  ) {
    const pluginRoot = scopeInstalledPluginRoot(scope, plugin, marketplace)
    if (existsSync(pluginRoot) && options?.force !== true) {
      throw new Error(`Destination already exists: ${pluginRoot}`)
    }
    ensureEmptyDir(pluginRoot)
    safeCopyDirectory(entrySourceBase, pluginRoot)

    installState[pluginSpec] = {
      plugin,
      marketplace,
      scope,
      kind: 'plugin-pack',
      pluginRoot,
      isEnabled: true,
      projectPath: scope === 'user' ? undefined : getCwd(),
      installedAt: new Date().toISOString(),
      skills: [],
      commands: [],
      sourceMarketplacePath:
        source.source === 'file' || source.source === 'directory'
          ? source.path
          : source.source === 'github'
            ? `github:${source.repo}`
            : source.source === 'url'
              ? source.url
              : source.source === 'git'
                ? source.url
                : `npm:${source.package}`,
    }
    savePluginInstallState(installState)

    return { pluginSpec, installedSkills: [], installedCommands: [] }
  }

  const skillsDestBase = scopeSkillsDir(scope)
  const commandsDestBase = join(scopeCommandsDir(scope), plugin, marketplace)

  ensureDir(skillsDestBase)
  ensureDir(commandsDestBase)

  const installedSkills: string[] = []
  const installedCommands: string[] = []

  const skillPaths = entry.skills ?? []
  for (const rel of skillPaths) {
    const src = safeJoinWithin(entrySourceBase, rel)
    if (!existsSync(src) || !lstatSync(src).isDirectory()) {
      throw new Error(`Skill path not found or not a directory: ${src}`)
    }
    const skillName = basename(src)
    const dest = join(skillsDestBase, skillName)

    if (existsSync(dest) && options?.force !== true) {
      throw new Error(`Destination already exists: ${dest}`)
    }
    ensureEmptyDir(dest)
    safeCopyDirectory(src, dest)
    installedSkills.push(skillName)
  }

  const commandPaths = entry.commands ?? []
  for (const rel of commandPaths) {
    const src = safeJoinWithin(entrySourceBase, rel)
    if (!existsSync(src)) {
      throw new Error(`Command path not found: ${src}`)
    }
    const stat = lstatSync(src)
    if (stat.isDirectory()) {
      const dest = join(commandsDestBase, basename(src))
      if (existsSync(dest) && options?.force !== true) {
        throw new Error(`Destination already exists: ${dest}`)
      }
      ensureEmptyDir(dest)
      safeCopyDirectory(src, dest)
      installedCommands.push(dest)
      continue
    }
    if (stat.isFile()) {
      const dest = join(commandsDestBase, basename(src))
      ensureDir(dirname(dest))
      if (existsSync(dest) && options?.force !== true) {
        throw new Error(`Destination already exists: ${dest}`)
      }
      copyFileSync(src, dest)
      installedCommands.push(dest)
      continue
    }
  }

  installState[pluginSpec] = {
    plugin,
    marketplace,
    scope,
    kind: 'skill-pack',
    isEnabled: true,
    projectPath: scope === 'user' ? undefined : getCwd(),
    installedAt: new Date().toISOString(),
    skills: installedSkills,
    commands: installedCommands,
    sourceMarketplacePath:
      source.source === 'file' || source.source === 'directory'
        ? source.path
        : source.source === 'github'
          ? `github:${source.repo}`
          : source.source === 'url'
            ? source.url
            : source.source === 'git'
              ? source.url
              : `npm:${source.package}`,
  }
  savePluginInstallState(installState)

  return { pluginSpec, installedSkills, installedCommands }
}

export function uninstallSkillPlugin(
  pluginInput: string,
  options?: { scope?: PluginScope; project?: boolean },
): { pluginSpec: string; removedSkills: string[]; removedCommands: string[] } {
  const requestedScope = normalizePluginScope(options)
  const state = ensurePluginInstallState()
  const pluginSpec = resolveInstalledPluginSpec(pluginInput, state)
  const record = state[pluginSpec]
  if (!record) {
    throw new Error(`Plugin '${pluginSpec}' is not installed`)
  }

  if (record.scope !== requestedScope) {
    throw new Error(
      `Plugin '${pluginSpec}' is installed with scope=${record.scope}. Re-run with --scope ${record.scope}.`,
    )
  }
  if (record.scope !== 'user') {
    const projectPath = record.projectPath?.trim() || ''
    const cwd = getCwd()
    if (!projectPath || projectPath !== cwd) {
      throw new Error(
        `Plugin '${pluginSpec}' is installed for a different directory. Expected cwd=${projectPath || '(missing)'}, got cwd=${cwd}`,
      )
    }
  }

  if (record.kind === 'plugin-pack') {
    const baseDir = baseDirForInstallRecord(record)
    const pluginRoot =
      typeof record.pluginRoot === 'string' && record.pluginRoot.trim()
        ? record.pluginRoot
        : join(
            baseDir,
            'plugins',
            'installed',
            record.plugin,
            record.marketplace,
          )

    const removedCommands: string[] = []
    if (existsSync(pluginRoot)) {
      rmSync(pluginRoot, { recursive: true, force: true })
      removedCommands.push(pluginRoot)
    }

    delete state[pluginSpec]
    savePluginInstallState(state)

    return { pluginSpec, removedSkills: [], removedCommands }
  }

  const baseDir = baseDirForInstallRecord(record)
  const skillsDestBase = join(baseDir, 'skills')
  const commandsDestBase = join(
    baseDir,
    'commands',
    record.plugin,
    record.marketplace,
  )
  const disabledSkillsBase = join(
    baseDir,
    'skills.disabled',
    record.plugin,
    record.marketplace,
  )
  const disabledCommandsBase = join(
    baseDir,
    'commands.disabled',
    record.plugin,
    record.marketplace,
  )

  const removedSkills: string[] = []
  for (const skillName of record.skills) {
    const dest = join(skillsDestBase, skillName)
    if (existsSync(dest)) rmSync(dest, { recursive: true, force: true })
    const disabledDest = join(disabledSkillsBase, skillName)
    if (existsSync(disabledDest))
      rmSync(disabledDest, { recursive: true, force: true })
    removedSkills.push(skillName)
  }

  const removedCommands: string[] = []
  if (existsSync(commandsDestBase)) {
    rmSync(commandsDestBase, { recursive: true, force: true })
    removedCommands.push(commandsDestBase)
  }
  if (existsSync(disabledCommandsBase)) {
    rmSync(disabledCommandsBase, { recursive: true, force: true })
    removedCommands.push(disabledCommandsBase)
  }

  delete state[pluginSpec]
  savePluginInstallState(state)

  return { pluginSpec, removedSkills, removedCommands }
}

export function disableSkillPlugin(
  pluginInput: string,
  options?: { scope?: PluginScope; project?: boolean },
): {
  pluginSpec: string
  disabledSkills: string[]
  disabledCommands: string[]
} {
  const requestedScope = normalizePluginScope(options)
  const state = ensurePluginInstallState()
  const pluginSpec = resolveInstalledPluginSpec(pluginInput, state)
  const record = state[pluginSpec]
  if (!record) throw new Error(`Plugin '${pluginSpec}' is not installed`)

  if (record.scope !== requestedScope) {
    throw new Error(
      `Plugin '${pluginSpec}' is installed with scope=${record.scope}. Re-run with --scope ${record.scope}.`,
    )
  }
  if (record.scope !== 'user') {
    const projectPath = record.projectPath?.trim() || ''
    const cwd = getCwd()
    if (!projectPath || projectPath !== cwd) {
      throw new Error(
        `Plugin '${pluginSpec}' is installed for a different directory. Expected cwd=${projectPath || '(missing)'}, got cwd=${cwd}`,
      )
    }
  }

  if (record.isEnabled === false) {
    return { pluginSpec, disabledSkills: [], disabledCommands: [] }
  }

  if (record.kind === 'plugin-pack') {
    record.isEnabled = false
    state[pluginSpec] = record
    savePluginInstallState(state)
    return { pluginSpec, disabledSkills: [], disabledCommands: [] }
  }

  const baseDir = baseDirForInstallRecord(record)
  const skillsDir = join(baseDir, 'skills')
  const commandsDir = join(
    baseDir,
    'commands',
    record.plugin,
    record.marketplace,
  )
  const disabledSkillsBase = join(
    baseDir,
    'skills.disabled',
    record.plugin,
    record.marketplace,
  )
  const disabledCommandsDir = join(
    baseDir,
    'commands.disabled',
    record.plugin,
    record.marketplace,
  )

  const disabledSkills: string[] = []
  for (const skillName of record.skills) {
    const src = join(skillsDir, skillName)
    if (!existsSync(src)) continue
    const dest = join(disabledSkillsBase, skillName)
    ensureDir(dirname(dest))
    if (existsSync(dest)) rmSync(dest, { recursive: true, force: true })
    renameSync(src, dest)
    disabledSkills.push(skillName)
  }

  const disabledCommands: string[] = []
  if (existsSync(commandsDir)) {
    ensureDir(dirname(disabledCommandsDir))
    if (existsSync(disabledCommandsDir)) {
      rmSync(disabledCommandsDir, { recursive: true, force: true })
    }
    renameSync(commandsDir, disabledCommandsDir)
    disabledCommands.push(disabledCommandsDir)
  }

  record.isEnabled = false
  state[pluginSpec] = record
  savePluginInstallState(state)

  return { pluginSpec, disabledSkills, disabledCommands }
}

export function enableSkillPlugin(
  pluginInput: string,
  options?: { scope?: PluginScope; project?: boolean },
): { pluginSpec: string; enabledSkills: string[]; enabledCommands: string[] } {
  const requestedScope = normalizePluginScope(options)
  const state = ensurePluginInstallState()
  const pluginSpec = resolveInstalledPluginSpec(pluginInput, state)
  const record = state[pluginSpec]
  if (!record) throw new Error(`Plugin '${pluginSpec}' is not installed`)

  if (record.scope !== requestedScope) {
    throw new Error(
      `Plugin '${pluginSpec}' is installed with scope=${record.scope}. Re-run with --scope ${record.scope}.`,
    )
  }
  if (record.scope !== 'user') {
    const projectPath = record.projectPath?.trim() || ''
    const cwd = getCwd()
    if (!projectPath || projectPath !== cwd) {
      throw new Error(
        `Plugin '${pluginSpec}' is installed for a different directory. Expected cwd=${projectPath || '(missing)'}, got cwd=${cwd}`,
      )
    }
  }

  if (record.isEnabled !== false) {
    return { pluginSpec, enabledSkills: [], enabledCommands: [] }
  }

  if (record.kind === 'plugin-pack') {
    record.isEnabled = true
    state[pluginSpec] = record
    savePluginInstallState(state)
    return { pluginSpec, enabledSkills: [], enabledCommands: [] }
  }

  const baseDir = baseDirForInstallRecord(record)
  const skillsDir = join(baseDir, 'skills')
  const commandsDir = join(
    baseDir,
    'commands',
    record.plugin,
    record.marketplace,
  )
  const disabledSkillsBase = join(
    baseDir,
    'skills.disabled',
    record.plugin,
    record.marketplace,
  )
  const disabledCommandsDir = join(
    baseDir,
    'commands.disabled',
    record.plugin,
    record.marketplace,
  )

  const enabledSkills: string[] = []
  for (const skillName of record.skills) {
    const src = join(disabledSkillsBase, skillName)
    if (!existsSync(src)) continue
    const dest = join(skillsDir, skillName)
    ensureDir(dirname(dest))
    if (existsSync(dest)) {
      throw new Error(`Destination already exists: ${dest}`)
    }
    renameSync(src, dest)
    enabledSkills.push(skillName)
  }

  const enabledCommands: string[] = []
  if (existsSync(disabledCommandsDir)) {
    ensureDir(dirname(commandsDir))
    if (existsSync(commandsDir)) {
      throw new Error(`Destination already exists: ${commandsDir}`)
    }
    renameSync(disabledCommandsDir, commandsDir)
    enabledCommands.push(commandsDir)
  }

  record.isEnabled = true
  state[pluginSpec] = record
  savePluginInstallState(state)

  return { pluginSpec, enabledSkills, enabledCommands }
}

export function listInstalledSkillPlugins(): InstalledSkillPluginsFile {
  return ensurePluginInstallState()
}

export function listEnabledInstalledPluginPackRoots(): string[] {
  const state = ensurePluginInstallState()
  const cwd = getCwd()
  const roots: string[] = []

  for (const spec of Object.keys(state).sort()) {
    const record = state[spec]
    if (!record || record.kind !== 'plugin-pack') continue
    if (record.isEnabled === false) continue

    if (record.scope !== 'user') {
      const projectPath = record.projectPath?.trim() || ''
      if (!projectPath || projectPath !== cwd) continue
    }

    const baseDir = baseDirForInstallRecord(record)
    const pluginRoot =
      typeof record.pluginRoot === 'string' && record.pluginRoot.trim()
        ? record.pluginRoot
        : join(
            baseDir,
            'plugins',
            'installed',
            record.plugin,
            record.marketplace,
          )

    try {
      if (!existsSync(pluginRoot) || !lstatSync(pluginRoot).isDirectory())
        continue
      roots.push(pluginRoot)
    } catch {
      continue
    }
  }

  return roots
}
