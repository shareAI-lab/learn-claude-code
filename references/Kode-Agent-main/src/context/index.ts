import {
  getCurrentProjectConfig,
  saveCurrentProjectConfig,
} from '@utils/config'
import { logError } from '@utils/log'
import { getCodeStyle } from '@utils/config/style'
import { getCwd } from '@utils/state'
import { memoize, omit } from 'lodash-es'
import { getIsGit } from '@utils/system/git'
import { execFileNoThrow } from '@utils/system/execFileNoThrow'
import { join } from 'path'
import { readFile } from 'fs/promises'
import { existsSync, readdirSync } from 'fs'
import { getModelManager } from '@utils/model'
import { lastX } from '@utils/text/generators'
import { getGitEmail } from '@utils/identity/user'
import {
  getProjectInstructionFiles,
  readAndConcatProjectInstructionFiles,
} from '@utils/config/projectInstructions'
export async function getInstructionFilesNote(): Promise<string | null> {
  try {
    const cwd = getCwd()
    const instructionFiles = getProjectInstructionFiles(cwd)
    const legacyPath = join(cwd, 'CLAUDE.md')
    const hasLegacy = existsSync(legacyPath)

    if (instructionFiles.length === 0 && !hasLegacy) {
      return null
    }

    const fileTypes = new Set<string>()
    for (const f of instructionFiles) fileTypes.add(f.filename)
    if (hasLegacy) fileTypes.add('CLAUDE.md (legacy)')

    const allFiles = [
      ...instructionFiles.map(f => f.absolutePath),
      ...(hasLegacy ? [legacyPath] : []),
    ]

    return `NOTE: Additional project instruction files (${Array.from(fileTypes).join(', ')}) were found. When working in these directories, make sure to read and follow the instructions in the corresponding files:\n${allFiles
      .map(_ => `- ${_}`)
      .join('\n')}`
  } catch (error) {
    logError(error)
    return null
  }
}

export function setContext(key: string, value: string): void {
  const projectConfig = getCurrentProjectConfig()
  const context = omit(
    { ...projectConfig.context, [key]: value },
    'codeStyle',
    'directoryStructure',
  )
  saveCurrentProjectConfig({ ...projectConfig, context })
}

export function removeContext(key: string): void {
  const projectConfig = getCurrentProjectConfig()
  const context = omit(
    projectConfig.context,
    key,
    'codeStyle',
    'directoryStructure',
  )
  saveCurrentProjectConfig({ ...projectConfig, context })
}

export const getReadme = memoize(async (): Promise<string | null> => {
  try {
    const readmePath = join(getCwd(), 'README.md')
    if (!existsSync(readmePath)) {
      return null
    }
    const content = await readFile(readmePath, 'utf-8')
    return content
  } catch (e) {
    logError(e)
    return null
  }
})

export async function getProjectDocsForCwd(
  cwd: string,
): Promise<string | null> {
  try {
    const instructionFiles = getProjectInstructionFiles(cwd)
    const legacyPath = join(cwd, 'CLAUDE.md')

    const docs = []

    if (instructionFiles.length > 0) {
      const { content } = readAndConcatProjectInstructionFiles(
        instructionFiles,
        { includeHeadings: true },
      )
      if (content.trim().length > 0) docs.push(content)
    }

    if (existsSync(legacyPath)) {
      try {
        const content = await readFile(legacyPath, 'utf-8')
        docs.push(
          `# Legacy instructions (CLAUDE.md)\n\n${content}`,
        )
      } catch (e) {
        logError(e)
      }
    }

    return docs.length > 0 ? docs.join('\n\n---\n\n') : null
  } catch (e) {
    logError(e)
    return null
  }
}

export const getProjectDocs = memoize(async (): Promise<string | null> => {
  return getProjectDocsForCwd(getCwd())
})

export const getGitStatus = memoize(async (): Promise<string | null> => {
  if (process.env.NODE_ENV === 'test') {
    return null
  }
  if (!(await getIsGit())) {
    return null
  }

  try {
    const [branch, mainBranch, status, log, authorLog] = await Promise.all([
      execFileNoThrow(
        'git',
        ['branch', '--show-current'],
        undefined,
        undefined,
        false,
      ).then(({ stdout }) => stdout.trim()),
      execFileNoThrow(
        'git',
        ['rev-parse', '--abbrev-ref', 'origin/HEAD'],
        undefined,
        undefined,
        false,
      ).then(({ stdout }) => stdout.replace('origin/', '').trim()),
      execFileNoThrow(
        'git',
        ['status', '--short'],
        undefined,
        undefined,
        false,
      ).then(({ stdout }) => stdout.trim()),
      execFileNoThrow(
        'git',
        ['log', '--oneline', '-n', '5'],
        undefined,
        undefined,
        false,
      ).then(({ stdout }) => stdout.trim()),
      execFileNoThrow(
        'git',
        [
          'log',
          '--oneline',
          '-n',
          '5',
          '--author',
          (await getGitEmail()) || '',
        ],
        undefined,
        undefined,
        false,
      ).then(({ stdout }) => stdout.trim()),
    ])
    const statusLines = status.split('\n').length
    const truncatedStatus =
      statusLines > 200
        ? status.split('\n').slice(0, 200).join('\n') +
          '\n... (truncated because there are more than 200 lines. If you need more information, run "git status" using BashTool)'
        : status

    return `This is the git status at the start of the conversation. Note that this status is a snapshot in time, and will not update during the conversation.\nCurrent branch: ${branch}\n\nMain branch (you will usually use this for PRs): ${mainBranch}\n\nStatus:\n${truncatedStatus || '(clean)'}\n\nRecent commits:\n${log}\n\nYour recent commits:\n${authorLog || '(no recent commits)'}`
  } catch (error) {
    logError(error)
    return null
  }
})

export const getContext = memoize(
  async (): Promise<{
    [k: string]: string
  }> => {
    const codeStyle = getCodeStyle()
    const projectConfig = getCurrentProjectConfig()
    const dontCrawl = projectConfig.dontCrawlDirectory
    const [
      gitStatus,
      directoryStructure,
      instructionFilesNote,
      readme,
      projectDocs,
    ] = await Promise.all([
      getGitStatus(),
      dontCrawl ? Promise.resolve('') : getDirectoryStructure(),
      dontCrawl ? Promise.resolve('') : getInstructionFilesNote(),
      getReadme(),
      getProjectDocs(),
    ])
    return {
      ...projectConfig.context,
      ...(directoryStructure ? { directoryStructure } : {}),
      ...(gitStatus ? { gitStatus } : {}),
      ...(codeStyle ? { codeStyle } : {}),
      ...(instructionFilesNote ? { instructionFilesNote } : {}),
      ...(readme ? { readme } : {}),
      ...(projectDocs ? { projectDocs } : {}),
    }
  },
)

export const getDirectoryStructure = memoize(
  async function (): Promise<string> {
    let lines: string
    try {
      const entries = readdirSync(getCwd(), { withFileTypes: true })
      lines = entries
        .map(entry => `${entry.isDirectory() ? 'd' : 'f'} ${entry.name}`)
        .join('\n')
    } catch (error) {
      logError(error)
      return ''
    }

    return `Below is a snapshot of this project's file structure at the start of the conversation. This snapshot will NOT update during the conversation.

${lines}`
  },
)
