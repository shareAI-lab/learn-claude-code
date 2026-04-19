import { execFileNoThrow } from '@utils/system/execFileNoThrow'
import { logError } from '@utils/log'

import { MACRO } from '@constants/macros'
import { PRODUCT_NAME } from '@constants/product'

async function getSemver() {
  const mod: any = await import('semver')
  return (mod?.default ?? mod) as {
    lt: (a: string, b: string) => boolean
    gt: (a: string, b: string) => boolean
  }
}

export type VersionConfig = {
  minVersion: string
}

export async function assertMinVersion(): Promise<void> {
  try {
    const versionConfig: VersionConfig = { minVersion: '0.0.0' }
    if (versionConfig.minVersion) {
      const { lt } = await getSemver()
      if (!lt(MACRO.VERSION, versionConfig.minVersion)) return

      const suggestions = await getUpdateCommandSuggestions()
      process.stderr.write(
        `Your ${PRODUCT_NAME} version ${MACRO.VERSION} is below the minimum supported ${versionConfig.minVersion}.\n` +
          'Update using one of:\n' +
          suggestions.map(c => `  ${c}`).join('\n') +
          '\n',
      )
      process.exit(1)
    }
  } catch (error) {
    logError(`Error checking minimum version: ${error}`)
  }
}

export async function getLatestVersion(): Promise<string | null> {
  try {
    const abortController = new AbortController()
    setTimeout(() => abortController.abort(), 5000)
    const result = await execFileNoThrow(
      'npm',
      ['view', MACRO.PACKAGE_URL, 'version'],
      abortController.signal,
    )
    if (result.code === 0) {
      const v = result.stdout.trim()
      if (v) return v
    }
  } catch {}

	  try {
	    const controller = new AbortController()
	    const timer = setTimeout(() => controller.abort(), 5000)
	    const res = await fetch(
	      `https://registry.npmjs.org/${encodeURIComponent(MACRO.PACKAGE_URL)}`,
	      {
	        method: 'GET',
	        headers: {
	          Accept: 'application/vnd.npm.install-v1+json',
	          'User-Agent': `${PRODUCT_NAME}/${MACRO.VERSION}`,
	        },
	        signal: controller.signal,
	      },
	    )
	    clearTimeout(timer)
	    if (!res.ok) return null
	    const json: any = await res.json().catch(() => null)
	    const latest = json && json['dist-tags'] && json['dist-tags'].latest
	    return typeof latest === 'string' ? latest : null
	  } catch {
	    return null
	  }
	}

export async function getUpdateCommandSuggestions(): Promise<string[]> {
  return [
    `bun add -g ${MACRO.PACKAGE_URL}@latest`,
    `npm install -g ${MACRO.PACKAGE_URL}@latest`,
  ]
}

export async function checkAndNotifyUpdate(): Promise<void> {
  try {
    if (process.env.NODE_ENV === 'test') return
    const [
      { isAutoUpdaterDisabled, getGlobalConfig, saveGlobalConfig },
      { env },
    ] = await Promise.all([import('@utils/config'), import('@utils/config/env')])
    if (await isAutoUpdaterDisabled()) return
    if (await env.getIsDocker()) return
    if (!(await env.hasInternetAccess())) return

    const config: any = getGlobalConfig()
    const now = Date.now()
    const DAY_MS = 24 * 60 * 60 * 1000
    const lastCheck = Number(config.lastUpdateCheckAt || 0)
    if (lastCheck && now - lastCheck < DAY_MS) return

    const latest = await getLatestVersion()
    if (!latest) {
      saveGlobalConfig({ ...config, lastUpdateCheckAt: now })
      return
    }

    const { gt } = await getSemver()
    if (gt(latest, MACRO.VERSION)) {
      saveGlobalConfig({
        ...config,
        lastUpdateCheckAt: now,
        lastSuggestedVersion: latest,
      })
      const suggestions = await getUpdateCommandSuggestions()
      process.stderr.write(
        [
          `New version available: ${latest} (current: ${MACRO.VERSION})`,
          'Run the following command to update:',
          ...suggestions.map(command => `  ${command}`),
          '',
        ].join('\n'),
      )
    } else {
      saveGlobalConfig({ ...config, lastUpdateCheckAt: now })
    }
  } catch (error) {
    logError(`update-notify: ${error}`)
  }
}
