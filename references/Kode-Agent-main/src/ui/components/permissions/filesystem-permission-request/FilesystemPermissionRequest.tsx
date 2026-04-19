import { Box, Text, useInput } from 'ink'
import React, { useCallback, useMemo } from 'react'
import { Select } from '@components/custom-select/select'
import { getTheme } from '@utils/theme'
import {
  PermissionRequestTitle,
  textColorForRiskScore,
} from '@components/permissions/PermissionRequestTitle'
import { logUnaryEvent } from '@utils/log/unaryLogging'
import { env } from '@utils/config/env'
import {
  type PermissionRequestProps,
  type ToolUseConfirm,
} from '@components/permissions/PermissionRequest'
import chalk from 'chalk'
import {
  UnaryEvent,
  usePermissionRequestLogging,
} from '@hooks/usePermissionRequestLogging'
import { FileEditTool } from '@tools/FileEditTool/FileEditTool'
import { FileWriteTool } from '@tools/FileWriteTool/FileWriteTool'
import { GrepTool } from '@tools/search/GrepTool/GrepTool'
import { GlobTool } from '@tools/GlobTool/GlobTool'
import { FileReadTool } from '@tools/FileReadTool/FileReadTool'
import { NotebookEditTool } from '@tools/NotebookEditTool/NotebookEditTool'
import { FallbackPermissionRequest } from '@components/permissions/FallbackPermissionRequest'
import { toAbsolutePath } from '@utils/permissions/filesystem'
import { getCwd } from '@utils/state'
import { basename, dirname } from 'path'
import { statSync } from 'fs'
import { getPermissionModeCycleShortcut } from '@utils/terminal/permissionModeCycleShortcut'
import { usePermissionContext } from '@context/PermissionContext'
import { isPathInWorkingDirectories } from '@utils/permissions/fileToolPermissionEngine'

function pathArgNameForToolUse(toolUseConfirm: ToolUseConfirm): string | null {
  switch (toolUseConfirm.tool) {
    case FileWriteTool:
    case FileEditTool:
    case FileReadTool: {
      return 'file_path'
    }
    case GlobTool:
    case GrepTool: {
      return 'path'
    }
    case NotebookEditTool: {
      return 'notebook_path'
    }
  }
  return null
}

function isMultiFile(toolUseConfirm: ToolUseConfirm): boolean {
  switch (toolUseConfirm.tool) {
    case GlobTool:
    case GrepTool: {
      return true
    }
  }
  return false
}

function pathToPermissionDirectory(path: string): string {
  try {
    const stats = statSync(path)
    if (stats.isDirectory()) return path
  } catch {
  }
  return dirname(path)
}

function pathFromToolUse(toolUseConfirm: ToolUseConfirm): string | null {
  const pathArgName = pathArgNameForToolUse(toolUseConfirm)
  const input = toolUseConfirm.input
  if (pathArgName && pathArgName in input) {
    if (typeof input[pathArgName] === 'string') {
      return toAbsolutePath(input[pathArgName])
    } else {
      return toAbsolutePath(getCwd())
    }
  }
  return null
}

export function FilesystemPermissionRequest({
  toolUseConfirm,
  onDone,
  verbose,
}: PermissionRequestProps): React.ReactNode {
  const path = pathFromToolUse(toolUseConfirm)
  if (!path) {
    return (
      <FallbackPermissionRequest
        toolUseConfirm={toolUseConfirm}
        onDone={onDone}
        verbose={verbose}
      />
    )
  }
  return (
    <FilesystemPermissionRequestImpl
      toolUseConfirm={toolUseConfirm}
      path={path}
      onDone={onDone}
      verbose={verbose}
    />
  )
}

function getDontAskAgainOptions(
  toolUseConfirm: ToolUseConfirm,
  path: string,
  modeCycleShortcut: string,
  isInWorkingDir: boolean,
  hasSessionSuggestion: boolean,
) {
  if (!hasSessionSuggestion) return []
  const permissionDirPath = pathToPermissionDirectory(path)
  const permissionDirName = basename(permissionDirPath) || 'this directory'

  if (toolUseConfirm.tool.isReadOnly(toolUseConfirm.input as never)) {
    const label = isInWorkingDir
      ? 'Yes, during this session'
      : `Yes, allow reading from ${chalk.bold(`${permissionDirName}/`)} during this session`
    return [{ label, value: 'yes-session' }]
  }

  const shortcutHint = chalk.bold.hex(getTheme().warning)(
    `(${modeCycleShortcut})`,
  )
  const label = isInWorkingDir
    ? `Yes, allow all edits during this session ${shortcutHint}`
    : `Yes, allow all edits in ${chalk.bold(`${permissionDirName}/`)} during this session ${shortcutHint}`
  return [{ label, value: 'yes-session' }]
}

type Props = {
  toolUseConfirm: ToolUseConfirm
  path: string
  onDone(): void
  verbose: boolean
}

function FilesystemPermissionRequestImpl({
  toolUseConfirm,
  path,
  onDone,
  verbose,
}: Props): React.ReactNode {
  const { applyToolPermissionUpdate, toolPermissionContext } =
    usePermissionContext()
  const modeCycleShortcut = useMemo(() => getPermissionModeCycleShortcut(), [])
  const userFacingName = toolUseConfirm.tool.userFacingName()
  const hasSessionSuggestion = (toolUseConfirm.suggestions?.length ?? 0) > 0

  const userFacingReadOrWrite = toolUseConfirm.tool.isReadOnly(
    toolUseConfirm.input as never,
  )
    ? 'Read'
    : 'Edit'
  const title = `${userFacingReadOrWrite} ${isMultiFile(toolUseConfirm) ? 'files' : 'file'}`

  const unaryEvent = useMemo<UnaryEvent>(
    () => ({
      completion_type: 'tool_use_single',
      language_name: 'none',
    }),
    [],
  )

  usePermissionRequestLogging(toolUseConfirm, unaryEvent)

  const permissionDirPath = useMemo(
    () => pathToPermissionDirectory(path),
    [path],
  )
  const isInWorkingDir = useMemo(
    () => isPathInWorkingDirectories(permissionDirPath, toolPermissionContext),
    [permissionDirPath, toolPermissionContext],
  )

  const handleChoice = useCallback(
    (newValue: string) => {
      switch (newValue) {
        case 'yes':
          logUnaryEvent({
            completion_type: 'tool_use_single',
            event: 'accept',
            metadata: {
              language_name: 'none',
              message_id: toolUseConfirm.assistantMessage.message.id,
              platform: env.platform,
            },
          })
          onDone()
          toolUseConfirm.onAllow('temporary')
          return
        case 'yes-session':
          logUnaryEvent({
            completion_type: 'tool_use_single',
            event: 'accept',
            metadata: {
              language_name: 'none',
              message_id: toolUseConfirm.assistantMessage.message.id,
              platform: env.platform,
            },
          })
          if (hasSessionSuggestion) {
            for (const update of toolUseConfirm.suggestions ?? []) {
              applyToolPermissionUpdate(update)
            }
          }
          onDone()
          toolUseConfirm.onAllow(
            hasSessionSuggestion ? 'permanent' : 'temporary',
          )
          return
        case 'no':
          logUnaryEvent({
            completion_type: 'tool_use_single',
            event: 'reject',
            metadata: {
              language_name: 'none',
              message_id: toolUseConfirm.assistantMessage.message.id,
              platform: env.platform,
            },
          })
          onDone()
          toolUseConfirm.onReject()
          return
      }
    },
    [applyToolPermissionUpdate, hasSessionSuggestion, onDone, toolUseConfirm],
  )

  useInput((inputChar, key) => {
    if (!modeCycleShortcut.check(inputChar, key)) return
    if (toolUseConfirm.tool.isReadOnly(toolUseConfirm.input as never)) return
    if (!hasSessionSuggestion) return
    handleChoice('yes-session')
    return true
  })

  return (
    <Box
      flexDirection="column"
      borderStyle="round"
      borderColor={textColorForRiskScore(toolUseConfirm.riskScore)}
      marginTop={1}
      paddingLeft={1}
      paddingRight={1}
      paddingBottom={1}
    >
      <PermissionRequestTitle
        title={title}
        riskScore={toolUseConfirm.riskScore}
      />
      <Box flexDirection="column" paddingX={2} paddingY={1}>
        <Text>
          {userFacingName}(
          {toolUseConfirm.tool.renderToolUseMessage(
            toolUseConfirm.input as never,
            { verbose },
          )}
          )
        </Text>
      </Box>

      <Box flexDirection="column">
        <Text>Do you want to proceed?</Text>
        <Select
          options={[
            {
              label: 'Yes',
              value: 'yes',
            },
            ...getDontAskAgainOptions(
              toolUseConfirm,
              path,
              modeCycleShortcut.displayText,
              isInWorkingDir,
              hasSessionSuggestion,
            ),
            {
              label: `No, and provide instructions (${chalk.bold.hex(getTheme().warning)('esc')})`,
              value: 'no',
            },
          ]}
          onChange={handleChoice}
        />
      </Box>
    </Box>
  )
}
