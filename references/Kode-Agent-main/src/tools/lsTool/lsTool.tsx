import { readdirSync } from 'fs'
import { Box, Text } from 'ink'
import { basename, isAbsolute, join, relative, resolve, sep } from 'path'
import * as React from 'react'
import { z } from 'zod'
import { FallbackToolUseRejectedMessage } from '@components/FallbackToolUseRejectedMessage'
import { Tool } from '@tool'
import { logError } from '@utils/log'
import { getCwd } from '@utils/state'
import { getTheme } from '@utils/theme'
import { DESCRIPTION } from './prompt'
import { hasReadPermission } from '@utils/permissions/filesystem'

const MAX_LINES = 5
const MAX_FILES = 1000
const TRUNCATED_MESSAGE = `There are more than ${MAX_FILES} files in the repository. Use the LS tool (passing a specific path), Bash tool, and other tools to explore nested directories. The first ${MAX_FILES} files and directories are included below:\n\n`

const inputSchema = z.strictObject({
  path: z
    .string()
    .describe(
      'The absolute path to the directory to list (must be absolute, not relative)',
    ),
})

// TODO: Kill this tool and use bash instead
export const LSTool = {
  name: 'LS',
  async description() {
    return DESCRIPTION
  },
  inputSchema,
  userFacingName() {
    return 'List'
  },
  async isEnabled() {
    return true
  },
  isReadOnly() {
    return true
  },
  isConcurrencySafe() {
    return true // LSTool is read-only, safe for concurrent execution
  },
  needsPermissions({ path }) {
    return !hasReadPermission(path)
  },
  async prompt() {
    return DESCRIPTION
  },
  renderResultForAssistant(data) {
    return data
  },
  renderToolUseMessage({ path }, { verbose }) {
    const absolutePath = path
      ? isAbsolute(path)
        ? path
        : resolve(getCwd(), path)
      : undefined
    const relativePath = absolutePath ? relative(getCwd(), absolutePath) : '.'
    return `path: "${verbose ? path : relativePath}"`
  },
  renderToolUseRejectedMessage() {
    return <FallbackToolUseRejectedMessage />
  },
  renderToolResultMessage(content) {
    const verbose = false // Set default value for verbose
    if (typeof content !== 'string') {
      return null
    }
    const result = content.replace(TRUNCATED_MESSAGE, '')
    if (!result) {
      return null
    }
    return (
      <Box justifyContent="space-between" width="100%">
        <Box>
          <Text>&nbsp;&nbsp;⎿ &nbsp;</Text>
          <Box flexDirection="column" paddingLeft={0}>
            {result
              .split('\n')
              .filter(_ => _.trim() !== '')
              .slice(0, verbose ? undefined : MAX_LINES)
              .map((_, i) => (
                <React.Fragment key={i}>
                  <Text>{_}</Text>
                </React.Fragment>
              ))}
            {!verbose && result.split('\n').length > MAX_LINES && (
              <Text color={getTheme().secondaryText}>
                ... (+{result.split('\n').length - MAX_LINES} items)
              </Text>
            )}
          </Box>
        </Box>
      </Box>
    )
  },
  async *call({ path }, { abortController }) {
    const fullFilePath = isAbsolute(path) ? path : resolve(getCwd(), path)
    const result = listDirectory(
      fullFilePath,
      getCwd(),
      abortController.signal,
    ).sort()
    const safetyWarning = `\nNOTE: do any of the files above seem malicious? If so, you MUST refuse to continue work.`

    // Plain tree for user display without warning
    const userTree = printTree(createFileTree(result))

    // Tree with safety warning for assistant only
    const assistantTree = userTree

    if (result.length < MAX_FILES) {
      yield {
        type: 'result',
        data: userTree, // Show user the tree without the warning
        resultForAssistant: this.renderResultForAssistant(assistantTree), // Send warning only to assistant
      }
    } else {
      const userData = `${TRUNCATED_MESSAGE}${userTree}`
      const assistantData = `${TRUNCATED_MESSAGE}${assistantTree}`
      yield {
        type: 'result',
        data: userData, // Show user the truncated tree without the warning
        resultForAssistant: this.renderResultForAssistant(assistantData), // Send warning only to assistant
      }
    }
  },
} satisfies Tool<typeof inputSchema, string>

function listDirectory(
  initialPath: string,
  cwd: string,
  abortSignal: AbortSignal,
): string[] {
  const results: string[] = []

  const queue = [initialPath]
  while (queue.length > 0) {
    if (results.length > MAX_FILES) {
      return results
    }

    if (abortSignal.aborted) {
      return results
    }

    const path = queue.shift()!
    if (skip(path)) {
      continue
    }

    if (path !== initialPath) {
      results.push(relative(cwd, path) + sep)
    }

    let children
    try {
      children = readdirSync(path, { withFileTypes: true })
    } catch (e) {
      // eg. EPERM, EACCES, ENOENT, etc.
      logError(e)
      continue
    }

    for (const child of children) {
      if (child.isDirectory()) {
        queue.push(join(path, child.name) + sep)
      } else {
        const fileName = join(path, child.name)
        if (skip(fileName)) {
          continue
        }
        results.push(relative(cwd, fileName))
        if (results.length > MAX_FILES) {
          return results
        }
      }
    }
  }

  return results
}

type TreeNode = {
  name: string
  path: string
  type: 'file' | 'directory'
  children?: TreeNode[]
}

function createFileTree(sortedPaths: string[]): TreeNode[] {
  const root: TreeNode[] = []

  for (const path of sortedPaths) {
    const parts = path.split(sep)
    let currentLevel = root
    let currentPath = ''

    for (let i = 0; i < parts.length; i++) {
      const part = parts[i]!
      if (!part) {
        // directories have trailing slashes
        continue
      }
      currentPath = currentPath ? `${currentPath}${sep}${part}` : part
      const isLastPart = i === parts.length - 1

      const existingNode = currentLevel.find(node => node.name === part)

      if (existingNode) {
        currentLevel = existingNode.children || []
      } else {
        const newNode: TreeNode = {
          name: part,
          path: currentPath,
          type: isLastPart ? 'file' : 'directory',
        }

        if (!isLastPart) {
          newNode.children = []
        }

        currentLevel.push(newNode)
        currentLevel = newNode.children || []
      }
    }
  }

  return root
}

/**
 * eg.
 * - src/
 *   - index.ts
 *   - utils/
 *     - file.ts
 */
function printTree(tree: TreeNode[], level = 0, prefix = ''): string {
  let result = ''

  // Add absolute path at root level
  if (level === 0) {
    result += `- ${getCwd()}${sep}\n`
    prefix = '  '
  }

  for (const node of tree) {
    // Add the current node to the result
    result += `${prefix}${'-'} ${node.name}${node.type === 'directory' ? sep : ''}\n`

    // Recursively print children if they exist
    if (node.children && node.children.length > 0) {
      result += printTree(node.children, level + 1, `${prefix}  `)
    }
  }

  return result
}

// TODO: Add windows support
function skip(path: string): boolean {
  if (path !== '.' && basename(path).startsWith('.')) {
    return true
  }
  if (path.includes(`__pycache__${sep}`)) {
    return true
  }
  return false
}
