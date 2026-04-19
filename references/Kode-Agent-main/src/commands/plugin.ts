import type { Command } from '@commands'
import { getCommands } from '@commands'
import { reloadCustomCommands } from '@services/customCommands'
import {
  addMarketplace,
  disableSkillPlugin,
  enableSkillPlugin,
  installSkillPlugin,
  listEnabledInstalledPluginPackRoots,
  listInstalledSkillPlugins,
  listMarketplaces,
  refreshAllMarketplacesAsync,
  refreshMarketplaceAsync,
  removeMarketplace,
  uninstallSkillPlugin,
} from '@services/skillMarketplace'
import {
  formatValidationResult,
  validatePluginOrMarketplacePath,
} from '@services/pluginValidation'
import { getCwd } from '@utils/state'
import { parse } from 'shell-quote'
import { getSessionPlugins } from '@utils/session/sessionPlugins'

type PluginScope = 'user' | 'project' | 'local'
const PLUGIN_SCOPES: readonly PluginScope[] = ['user', 'project', 'local']

function parseTokens(input: string): string[] {
  const parts = parse(input)
  const out: string[] = []
  for (const part of parts) {
    if (typeof part === 'string') out.push(part)
  }
  return out
}

function parseCommonFlags(tokens: string[]): {
  scope: PluginScope
  force: boolean
  json: boolean
  rest: string[]
} {
  let scope: PluginScope = 'user'
  let force = false
  let json = false
  const rest: string[] = []

  for (let i = 0; i < tokens.length; i++) {
    const token = tokens[i]!
    if ((token === '--scope' || token === '-s') && i + 1 < tokens.length) {
      const next = tokens[i + 1] as string
      if (PLUGIN_SCOPES.includes(next as PluginScope)) {
        scope = next as PluginScope
        i++
        continue
      }
    }
    if (token === '--force') {
      force = true
      continue
    }
    if (token === '--json') {
      json = true
      continue
    }
    rest.push(token)
  }

  return { scope, force, json, rest }
}

function refreshCommandsCache(): void {
  reloadCustomCommands()
  getCommands.cache.clear?.()
}

async function refreshPluginRuntimeFromInstalls(): Promise<string[]> {
  const installedRoots = listEnabledInstalledPluginPackRoots()
  const existingRoots = getSessionPlugins().map(p => p.rootDir)
  const dirs = Array.from(new Set([...existingRoots, ...installedRoots]))
  if (dirs.length === 0) return []

  const { configureSessionPlugins } = await import('@services/pluginRuntime')
  const { errors } = await configureSessionPlugins({ pluginDirs: dirs })
  return errors
}

const plugin = {
  type: 'local',
  name: 'plugin',
  description: 'Manage plugins and marketplaces',
  isEnabled: true,
  isHidden: false,
  async call(args: string, _context: any) {
    const tokens = parseTokens(args)
    if (tokens.length === 0) {
      return [
        'Usage:',
        '  /plugin marketplace add <source>',
        '  /plugin marketplace list [--json]',
        '  /plugin marketplace remove <name>',
        '  /plugin marketplace update [name]',
        '  /plugin install <plugin> [--scope user|project|local] [--force]',
        '  /plugin uninstall <plugin> [--scope user|project|local]',
        '  /plugin enable <plugin> [--scope user|project|local]',
        '  /plugin disable <plugin> [--scope user|project|local]',
        '  /plugin list [--scope user|project|local] [--json]',
        '  /plugin validate <path>',
      ].join('\n')
    }

    const [subcommand, ...restTokens] = tokens

    if (subcommand === 'marketplace') {
      const [action, ...actionArgs] = restTokens
      const { json } = parseCommonFlags(actionArgs)

      if (action === 'add') {
        const source = actionArgs.filter(t => !t.startsWith('--')).join(' ')
        if (!source) return 'Usage: /plugin marketplace add <source>'
        const { name } = await addMarketplace(source)
        refreshCommandsCache()
        return `✓ Successfully added marketplace: ${name}`
      }

      if (action === 'list') {
        const marketplaces = listMarketplaces()
        if (json) return JSON.stringify(marketplaces, null, 2)
        const names = Object.keys(marketplaces).sort()
        if (names.length === 0) return 'No marketplaces configured'
        const lines: string[] = ['Configured marketplaces:']
        for (const name of names) {
          const entry: any = marketplaces[name]
          lines.push(`  - ${name}`)
          const src = entry?.source
          if (src?.source === 'github')
            lines.push(`    Source: GitHub (${src.repo})`)
          else if (src?.source === 'git')
            lines.push(`    Source: Git (${src.url})`)
          else if (src?.source === 'url')
            lines.push(`    Source: URL (${src.url})`)
          else if (src?.source === 'directory')
            lines.push(`    Source: Directory (${src.path})`)
          else if (src?.source === 'file')
            lines.push(`    Source: File (${src.path})`)
          else if (src?.source === 'npm')
            lines.push(`    Source: NPM (${src.package})`)
        }
        return lines.join('\n')
      }

      if (action === 'remove' || action === 'rm') {
        const name = actionArgs[0]?.trim()
        if (!name) return 'Usage: /plugin marketplace remove <name>'
        removeMarketplace(name)
        refreshCommandsCache()
        return `✓ Successfully removed marketplace: ${name}`
      }

      if (action === 'update') {
        const name = actionArgs[0]?.trim()
        if (name) {
          await refreshMarketplaceAsync(name)
          refreshCommandsCache()
          return `✓ Successfully updated marketplace: ${name}`
        }
        const marketplaces = listMarketplaces()
        const names = Object.keys(marketplaces)
        if (names.length === 0) return 'No marketplaces configured'
        await refreshAllMarketplacesAsync()
        refreshCommandsCache()
        return `✓ Successfully updated ${names.length} marketplace(s)`
      }

      return `Unknown marketplace subcommand: ${String(action || '')}`
    }

    if (subcommand === 'install') {
      const { scope, force, rest } = parseCommonFlags(restTokens)
      const pluginArg = rest[0]
      if (!pluginArg)
        return 'Usage: /plugin install <plugin> [--scope user|project|local] [--force]'
      const result = installSkillPlugin(pluginArg, { scope, force })
      const record = listInstalledSkillPlugins()[result.pluginSpec] as any
      const isPack = record?.kind === 'plugin-pack'
      const loadErrors = await refreshPluginRuntimeFromInstalls()
      refreshCommandsCache()
      const lines: string[] = []
      lines.push(
        `✓ Installed ${result.pluginSpec} (scope=${scope})${isPack ? ' [plugin pack]' : ''}`,
      )
      if (!isPack) {
        lines.push(`Skills: ${result.installedSkills.join(', ') || '(none)'}`)
      }
      if (loadErrors.length > 0) {
        lines.push('', 'Warnings:', ...loadErrors.map(e => `- ${e}`))
      }
      return lines.join('\n')
    }

    if (
      subcommand === 'uninstall' ||
      subcommand === 'remove' ||
      subcommand === 'rm'
    ) {
      const { scope, rest } = parseCommonFlags(restTokens)
      const pluginArg = rest[0]
      if (!pluginArg)
        return 'Usage: /plugin uninstall <plugin> [--scope user|project|local]'
      const result = uninstallSkillPlugin(pluginArg, { scope })
      const loadErrors = await refreshPluginRuntimeFromInstalls()
      refreshCommandsCache()
      const lines: string[] = []
      lines.push(`✓ Uninstalled ${result.pluginSpec} (scope=${scope})`)
      if (result.removedSkills.length > 0) {
        lines.push(`Skills: ${result.removedSkills.join(', ')}`)
      }
      if (loadErrors.length > 0) {
        lines.push('', 'Warnings:', ...loadErrors.map(e => `- ${e}`))
      }
      return lines.join('\n')
    }

    if (subcommand === 'enable') {
      const { scope, rest } = parseCommonFlags(restTokens)
      const pluginArg = rest[0]
      if (!pluginArg)
        return 'Usage: /plugin enable <plugin> [--scope user|project|local]'
      const result = enableSkillPlugin(pluginArg, { scope })
      const loadErrors = await refreshPluginRuntimeFromInstalls()
      refreshCommandsCache()
      const lines: string[] = []
      lines.push(`✓ Enabled ${result.pluginSpec} (scope=${scope})`)
      if (loadErrors.length > 0) {
        lines.push('', 'Warnings:', ...loadErrors.map(e => `- ${e}`))
      }
      return lines.join('\n')
    }

    if (subcommand === 'disable') {
      const { scope, rest } = parseCommonFlags(restTokens)
      const pluginArg = rest[0]
      if (!pluginArg)
        return 'Usage: /plugin disable <plugin> [--scope user|project|local]'
      const result = disableSkillPlugin(pluginArg, { scope })
      const loadErrors = await refreshPluginRuntimeFromInstalls()
      refreshCommandsCache()
      const lines: string[] = []
      lines.push(`✓ Disabled ${result.pluginSpec} (scope=${scope})`)
      if (loadErrors.length > 0) {
        lines.push('', 'Warnings:', ...loadErrors.map(e => `- ${e}`))
      }
      return lines.join('\n')
    }

    if (subcommand === 'list') {
      const { scope, json } = parseCommonFlags(restTokens)
      const cwd = getCwd()
      const all = listInstalledSkillPlugins()
      const filtered = Object.fromEntries(
        Object.entries(all).filter(([, record]) => {
          const r: any = record
          if (!r || r.scope !== scope) return false
          if (scope === 'user') return true
          return r.projectPath === cwd
        }),
      )
      if (json) return JSON.stringify(filtered, null, 2)
      const specs = Object.keys(filtered).sort()
      if (specs.length === 0) return 'No plugins installed'
      const lines: string[] = [`Installed plugins (scope=${scope}):`]
      for (const spec of specs) {
        const r: any = filtered[spec]
        const enabled = r?.isEnabled === false ? 'disabled' : 'enabled'
        lines.push(`  - ${spec} (${enabled})`)
      }
      return lines.join('\n')
    }

    if (subcommand === 'validate') {
      const target = restTokens.join(' ').trim()
      if (!target) {
        return [
          'Usage: /plugin validate <path>',
          '  kode plugin validate <path>',
        ].join('\n')
      }
      const result = validatePluginOrMarketplacePath(target)
      return `Validating ${result.fileType} manifest: ${result.filePath}\n${formatValidationResult(result)}`
    }

    return `Unknown /plugin subcommand: ${subcommand}`
  },
  userFacingName() {
    return 'plugin'
  },
} satisfies Command

export default plugin
