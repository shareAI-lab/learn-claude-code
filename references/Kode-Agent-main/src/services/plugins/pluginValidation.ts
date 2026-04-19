import { existsSync, lstatSync, readFileSync } from 'node:fs'
import { dirname, join, resolve, sep } from 'node:path'
import figures from 'figures'
import { z } from 'zod'
import { getCwd } from '@utils/state'
import { parseFrontmatter } from '@services/customCommands'
import { MarketplaceManifestSchema } from '@services/skillMarketplace'

export type ValidationIssue = {
  path: string
  message: string
}

export type ValidationResult = {
  success: boolean
  fileType: 'plugin' | 'marketplace'
  filePath: string
  errors: ValidationIssue[]
  warnings: ValidationIssue[]
}

const PluginManifestSchema = z
  .strictObject({
    name: z.string().min(1),
    version: z.string().optional(),
    description: z.string().optional(),
    author: z.unknown().optional(),
    homepage: z.string().optional(),
    repository: z.unknown().optional(),
    license: z.string().optional(),
    keywords: z.array(z.string()).optional(),
    commands: z.union([z.string(), z.array(z.string())]).optional(),
    agents: z.union([z.string(), z.array(z.string())]).optional(),
    skills: z.union([z.string(), z.array(z.string())]).optional(),
    hooks: z.union([z.string(), z.record(z.string(), z.unknown())]).optional(),
    mcpServers: z
      .union([z.string(), z.record(z.string(), z.unknown())])
      .optional(),
  })
  .passthrough()

function resolveFromAgentCwd(input: string): string {
  const trimmed = input.trim()
  if (!trimmed) return trimmed
  if (trimmed.startsWith('~')) {
    return trimmed
  }
  if (trimmed.startsWith(sep)) return trimmed
  return resolve(getCwd(), trimmed)
}

function validateRelativePath(path: string): string | null {
  if (!path.startsWith('./')) return 'must start with "./"'
  if (path.split('/').includes('..')) return 'must not contain ".."'
  if (path.includes('\\')) return 'must use forward slashes'
  return null
}

function safeResolveWithin(baseDir: string, rel: string): string | null {
  const normalized = rel.replace(/\\/g, '/')
  if (!normalized.startsWith('./') || normalized.split('/').includes('..'))
    return null
  const abs = resolve(baseDir, normalized.split('/').join(sep))
  const base = resolve(baseDir)
  if (!abs.startsWith(base + sep) && abs !== base) return null
  return abs
}

function validateSkillDir(skillDir: string): ValidationIssue[] {
  const issues: ValidationIssue[] = []
  const name = skillDir.split(sep).pop() || ''
  if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(name) || name.length > 64) {
    issues.push({
      path: `skills/${name}`,
      message:
        'Invalid skill directory name (must be lowercase kebab-case, 1–64 chars)',
    })
    return issues
  }

  const skillFileCandidates = [
    join(skillDir, 'SKILL.md'),
    join(skillDir, 'skill.md'),
  ]
  const skillFile = skillFileCandidates.find(p => existsSync(p))
  if (!skillFile) {
    issues.push({
      path: `skills/${name}`,
      message: 'Missing SKILL.md (or skill.md)',
    })
    return issues
  }

  try {
    const raw = readFileSync(skillFile, 'utf8')
    const { frontmatter } = parseFrontmatter(raw)
    const declared =
      typeof (frontmatter as any).name === 'string'
        ? String((frontmatter as any).name).trim()
        : ''
    if (!declared) {
      issues.push({
        path: `${name}/SKILL.md`,
        message: 'Missing required frontmatter field: name',
      })
    } else if (declared !== name) {
      issues.push({
        path: `${name}/SKILL.md`,
        message: `Frontmatter name must match directory name (dir=${name}, name=${declared})`,
      })
    }

    const description =
      typeof (frontmatter as any).description === 'string'
        ? String((frontmatter as any).description).trim()
        : ''
    if (!description) {
      issues.push({
        path: `${name}/SKILL.md`,
        message: 'Missing required frontmatter field: description',
      })
    } else if (description.length > 1024) {
      issues.push({
        path: `${name}/SKILL.md`,
        message: 'description must be <= 1024 characters',
      })
    }
  } catch (err) {
    issues.push({
      path: `${name}/SKILL.md`,
      message: `Failed to parse SKILL.md: ${err instanceof Error ? err.message : String(err)}`,
    })
  }

  return issues
}

function validateMarketplaceJson(filePath: string): ValidationResult {
  const errors: ValidationIssue[] = []
  const warnings: ValidationIssue[] = []

  let raw: string
  try {
    raw = readFileSync(filePath, 'utf8')
  } catch (err) {
    return {
      success: false,
      fileType: 'marketplace',
      filePath,
      errors: [
        { path: 'file', message: `Failed to read file: ${String(err)}` },
      ],
      warnings: [],
    }
  }

  let json: unknown
  try {
    json = JSON.parse(raw)
  } catch (err) {
    return {
      success: false,
      fileType: 'marketplace',
      filePath,
      errors: [
        { path: 'json', message: `Invalid JSON syntax: ${String(err)}` },
      ],
      warnings: [],
    }
  }

  const parsed = MarketplaceManifestSchema.safeParse(json)
  if (!parsed.success) {
    errors.push(
      ...parsed.error.issues.map(i => ({
        path: i.path.join('.'),
        message: i.message,
      })),
    )
    return {
      success: false,
      fileType: 'marketplace',
      filePath,
      errors,
      warnings,
    }
  }

  const data = parsed.data
  const topLevelDescription =
    typeof (data as any).description === 'string'
      ? String((data as any).description).trim()
      : ''
  const metadataDescription =
    typeof (data.metadata as any)?.description === 'string'
      ? String((data.metadata as any).description).trim()
      : ''
  if (!topLevelDescription && !metadataDescription) {
    warnings.push({
      path: 'description',
      message:
        'No marketplace description provided. Adding a description helps users understand what this marketplace offers',
    })
  }
  if (!data.plugins || data.plugins.length === 0) {
    warnings.push({
      path: 'plugins',
      message: 'Marketplace has no plugins defined',
    })
  }

  const pluginNames = new Set<string>()
  for (const [index, plugin] of data.plugins.entries()) {
    if (pluginNames.has(plugin.name)) {
      errors.push({
        path: `plugins[${index}].name`,
        message: `Duplicate plugin name "${plugin.name}"`,
      })
    }
    pluginNames.add(plugin.name)

    const source = plugin.source ?? './'
    const sourceErr = validateRelativePath(source)
    if (sourceErr)
      errors.push({ path: `plugins[${index}].source`, message: sourceErr })

    const marketplaceRoot = dirname(dirname(filePath))
    const pluginBase = safeResolveWithin(marketplaceRoot, source)
    if (!pluginBase) {
      errors.push({
        path: `plugins[${index}].source`,
        message: 'Invalid source path (must be ./..., no .., forward slashes)',
      })
      continue
    }
    if (!existsSync(pluginBase) || !lstatSync(pluginBase).isDirectory()) {
      errors.push({
        path: `plugins[${index}].source`,
        message: `Source path not found: ${source}`,
      })
      continue
    }

    const skillPaths = plugin.skills ?? []
    for (const [j, rel] of skillPaths.entries()) {
      const err = validateRelativePath(rel)
      if (err) {
        errors.push({ path: `plugins[${index}].skills[${j}]`, message: err })
        continue
      }
      const abs = safeResolveWithin(pluginBase, rel)
      if (!abs) {
        errors.push({
          path: `plugins[${index}].skills[${j}]`,
          message: 'Invalid path (must be ./..., no .., forward slashes)',
        })
        continue
      }
      if (!existsSync(abs) || !lstatSync(abs).isDirectory()) {
        errors.push({
          path: `plugins[${index}].skills[${j}]`,
          message: `Skill directory not found: ${rel}`,
        })
        continue
      }
      errors.push(
        ...validateSkillDir(abs).map(e => ({
          ...e,
          path: `plugins[${index}].skills[${j}]: ${e.path}`,
        })),
      )
    }

    const commandPaths = plugin.commands ?? []
    for (const [j, rel] of commandPaths.entries()) {
      const err = validateRelativePath(rel)
      if (err) {
        errors.push({ path: `plugins[${index}].commands[${j}]`, message: err })
        continue
      }
      const abs = safeResolveWithin(pluginBase, rel)
      if (!abs) {
        errors.push({
          path: `plugins[${index}].commands[${j}]`,
          message: 'Invalid path (must be ./..., no .., forward slashes)',
        })
        continue
      }
      if (!existsSync(abs) || !lstatSync(abs).isDirectory()) {
        errors.push({
          path: `plugins[${index}].commands[${j}]`,
          message: `Command directory not found: ${rel}`,
        })
      }
    }
  }

  return {
    success: errors.length === 0,
    fileType: 'marketplace',
    filePath,
    errors,
    warnings,
  }
}

function validatePluginJson(filePath: string): ValidationResult {
  const errors: ValidationIssue[] = []
  const warnings: ValidationIssue[] = []

  let raw: string
  try {
    raw = readFileSync(filePath, 'utf8')
  } catch (err) {
    return {
      success: false,
      fileType: 'plugin',
      filePath,
      errors: [
        { path: 'file', message: `Failed to read file: ${String(err)}` },
      ],
      warnings: [],
    }
  }

  let json: unknown
  try {
    json = JSON.parse(raw)
  } catch (err) {
    return {
      success: false,
      fileType: 'plugin',
      filePath,
      errors: [
        { path: 'json', message: `Invalid JSON syntax: ${String(err)}` },
      ],
      warnings: [],
    }
  }

  const parsed = PluginManifestSchema.safeParse(json)
  if (!parsed.success) {
    errors.push(
      ...parsed.error.issues.map(i => ({
        path: i.path.join('.'),
        message: i.message,
      })),
    )
    return { success: false, fileType: 'plugin', filePath, errors, warnings }
  }

  const data = parsed.data

  if (!/^[a-z][a-z0-9]*(-[a-z0-9]+)*$/.test(data.name)) {
    errors.push({
      path: 'name',
      message: 'Must be kebab-case and start with a letter',
    })
  }
  if (
    data.version &&
    !/^(\d+)\.(\d+)\.(\d+)(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$/.test(
      data.version,
    )
  ) {
    errors.push({
      path: 'version',
      message: 'Invalid semantic version (expected MAJOR.MINOR.PATCH)',
    })
  }
  if (data.homepage) {
    try {
      // eslint-disable-next-line no-new
      new URL(data.homepage)
    } catch {
      errors.push({ path: 'homepage', message: 'Invalid URL' })
    }
  }
  if (typeof data.repository === 'string') {
    try {
      // eslint-disable-next-line no-new
      new URL(data.repository)
    } catch {
      errors.push({ path: 'repository', message: 'Invalid URL' })
    }
  }
  if (!data.version) {
    warnings.push({
      path: 'version',
      message:
        'No version specified. Consider adding a version following semver (e.g., "1.0.0")',
    })
  }
  if (!data.description) {
    warnings.push({
      path: 'description',
      message:
        'No description provided. Adding a description helps users understand what your plugin does',
    })
  }
  if (!data.author) {
    warnings.push({
      path: 'author',
      message:
        'No author information provided. Consider adding author details for plugin attribution',
    })
  }

  const pluginRoot = dirname(dirname(filePath))

  const validatePathList = (field: string, value: unknown) => {
    if (!value) return
    const values = Array.isArray(value) ? value : [value]
    for (const [idx, p] of values.entries()) {
      if (typeof p !== 'string') continue
      const err = validateRelativePath(p)
      if (err) errors.push({ path: `${field}[${idx}]`, message: err })
      const abs = safeResolveWithin(pluginRoot, p)
      if (!abs) {
        errors.push({
          path: `${field}[${idx}]`,
          message: 'Invalid path (must be ./..., no .., forward slashes)',
        })
      } else if (!existsSync(abs)) {
        errors.push({
          path: `${field}[${idx}]`,
          message: `Path not found: ${p}`,
        })
      }
    }
  }

  validatePathList('commands', data.commands)
  validatePathList('agents', data.agents)
  validatePathList('skills', data.skills)

  if (typeof data.hooks === 'string') validatePathList('hooks', data.hooks)
  if (typeof data.mcpServers === 'string')
    validatePathList('mcpServers', data.mcpServers)

  return {
    success: errors.length === 0,
    fileType: 'plugin',
    filePath,
    errors,
    warnings,
  }
}

export function validatePluginOrMarketplacePath(
  path: string,
): ValidationResult {
  const abs = resolveFromAgentCwd(path)
  if (!abs) {
    return {
      success: false,
      fileType: 'plugin',
      filePath: '',
      errors: [{ path: 'path', message: 'Path is required' }],
      warnings: [],
    }
  }
  if (!existsSync(abs)) {
    return {
      success: false,
      fileType: 'plugin',
      filePath: abs,
      errors: [{ path: 'file', message: `Path not found: ${abs}` }],
      warnings: [],
    }
  }

  const stat = lstatSync(abs)
  let filePath = abs
  if (stat.isDirectory()) {
    const marketplace = join(abs, '.kode-plugin', 'marketplace.json')
    const plugin = join(abs, '.kode-plugin', 'plugin.json')
    const legacyMarketplace = join(abs, '.claude-plugin', 'marketplace.json')
    const legacyPlugin = join(abs, '.claude-plugin', 'plugin.json')
    if (existsSync(marketplace)) filePath = marketplace
    else if (existsSync(plugin)) filePath = plugin
    else if (existsSync(legacyMarketplace)) filePath = legacyMarketplace
    else if (existsSync(legacyPlugin)) filePath = legacyPlugin
    else {
      return {
        success: false,
        fileType: 'plugin',
        filePath: abs,
        errors: [
          {
            path: 'directory',
            message:
              'No manifest found in directory. Expected .kode-plugin/marketplace.json or .kode-plugin/plugin.json (legacy .claude-plugin/* is also supported)',
          },
        ],
        warnings: [],
      }
    }
  }

  if (filePath.endsWith('marketplace.json'))
    return validateMarketplaceJson(filePath)
  if (filePath.endsWith('plugin.json')) return validatePluginJson(filePath)

  try {
    const raw = readFileSync(filePath, 'utf8')
    const json = JSON.parse(raw)
    if (
      json &&
      typeof json === 'object' &&
      Array.isArray((json as any).plugins)
    ) {
      return validateMarketplaceJson(filePath)
    }
  } catch {}
  return validatePluginJson(filePath)
}

export function formatValidationResult(result: ValidationResult): string {
  const lines: string[] = []
  for (const err of result.errors) {
    lines.push(`  ${figures.pointer} ${err.path}: ${err.message}`)
  }
  for (const warn of result.warnings) {
    lines.push(`  ${figures.pointer} ${warn.path}: ${warn.message}`)
  }

  lines.push('')

  if (result.success) {
    if (result.warnings.length > 0) {
      lines.push(`${figures.tick} Validation passed with warnings`)
    } else {
      lines.push(`${figures.tick} Validation passed`)
    }
  } else {
    lines.push(`${figures.cross} Validation failed`)
  }

  return lines.join('\n')
}
