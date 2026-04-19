import { readFileSync } from 'fs'
import { memoize } from 'lodash-es'
import { getCwd } from '@utils/state'
import { getProjectInstructionFiles } from './projectInstructions'

const STYLE_PROMPT =
  'The codebase follows strict style guidelines shown below. All code changes must strictly adhere to these guidelines to maintain consistency and quality.'

export const getCodeStyle = memoize((): string => {
  const styles: string[] = []

  const instructionFiles = getProjectInstructionFiles(getCwd())
  for (const file of instructionFiles) {
    try {
      styles.push(
        `Contents of ${file.absolutePath}:\n\n${readFileSync(file.absolutePath, 'utf-8')}`,
      )
    } catch {
    }
  }

  if (styles.length === 0) {
    return ''
  }

  return `${STYLE_PROMPT}\n\n${styles.join('\n\n')}`
})
