import chalk from 'chalk'
import type { Command } from '@commands'
import { getGlobalConfig, saveGlobalConfig } from '@utils/config'
import {
  AUTO_COMPACT_THRESHOLD_RATIO,
  getAutoCompactThresholdRatio,
  isValidAutoCompactThresholdRatio,
} from '@utils/session/autoCompactThreshold'

const HELP_ARGS = new Set(['help', '-h', '--help', '?'])
const RESET_ARGS = new Set(['reset', 'default'])

function parseThresholdInput(raw: string): number | null {
  const trimmed = raw.trim()
  if (!trimmed) return null

  let valueText = trimmed
  let isPercent = false

  if (valueText.endsWith('%')) {
    isPercent = true
    valueText = valueText.slice(0, -1).trim()
  }

  if (!valueText) return null

  const value = Number(valueText)
  if (!Number.isFinite(value)) return null

  let ratio = value
  // Treat bare values >1 as percentages (85 => 0.85) while still allowing ratios like 0.85.
  if (isPercent || (value > 1 && value <= 100)) {
    ratio = value / 100
  }

  return isValidAutoCompactThresholdRatio(ratio) ? ratio : null
}

function formatRatio(ratio: number): string {
  const percent = Math.round(ratio * 100)
  return `${ratio} (${percent}%)`
}

const compactThreshold = {
  type: 'local',
  name: 'compact-threshold',
  description: 'View or set the auto-compact threshold ratio',
  isEnabled: true,
  isHidden: false,
  argumentHint: '[ratio]',
  userFacingName() {
    return 'compact-threshold'
  },
  async call(args) {
    const raw = args.trim()

    if (!raw || HELP_ARGS.has(raw)) {
      const configured = getGlobalConfig().autoCompactThreshold
      const isCustom = isValidAutoCompactThresholdRatio(configured)
      const ratio = getAutoCompactThresholdRatio()
      const defaultNote = isCustom ? '' : ' (default)'

      return [
        `Auto-compact threshold: ${formatRatio(ratio)}${defaultNote}`,
        'Usage: /compact-threshold 0.85',
        'Tip: You can also use percentages, e.g. /compact-threshold 85%',
      ].join('\n')
    }

    if (RESET_ARGS.has(raw)) {
      const nextConfig = { ...getGlobalConfig() }
      delete nextConfig.autoCompactThreshold
      saveGlobalConfig(nextConfig)
      return `Auto-compact threshold reset to default (${AUTO_COMPACT_THRESHOLD_RATIO}).`
    }

    const parsed = parseThresholdInput(raw)
    if (!parsed) {
      return [
        `Invalid threshold: ${chalk.bold(raw)}`,
        'Provide a ratio greater than 0 and less than 1 (e.g. 0.85 or 85%).',
      ].join('\n')
    }

    const config = getGlobalConfig()
    saveGlobalConfig({ ...config, autoCompactThreshold: parsed })
    return `Auto-compact threshold set to ${formatRatio(parsed)}.`
  },
} satisfies Command

export default compactThreshold
