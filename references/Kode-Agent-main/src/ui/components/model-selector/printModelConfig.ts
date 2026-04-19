import chalk from 'chalk'
import { getGlobalConfig } from '@utils/config'

export function printModelConfig() {
  const config = getGlobalConfig()
  const modelProfiles = config.modelProfiles || []
  const activeProfiles = modelProfiles.filter(p => p.isActive)

  if (activeProfiles.length === 0) {
    process.stdout.write(`${chalk.gray('  ⎿  No active model profiles configured')}\n`)
    return
  }

  const profileSummary = activeProfiles
    .map(p => `${p.name} (${p.provider}: ${p.modelName})`)
    .join(' | ')
  process.stdout.write(`${chalk.gray(`  ⎿  ${profileSummary}`)}\n`)
}
