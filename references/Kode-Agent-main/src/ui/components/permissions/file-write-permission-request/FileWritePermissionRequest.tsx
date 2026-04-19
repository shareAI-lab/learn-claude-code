import { Box, Text, useInput } from 'ink'
import React, { useCallback, useMemo } from 'react'
import { Select } from '@components/custom-select/select'
import { basename, dirname, extname } from 'path'
import { getTheme } from '@utils/theme'
import {
  PermissionRequestTitle,
  textColorForRiskScore,
} from '@components/permissions/PermissionRequestTitle'
import { logUnaryEvent } from '@utils/log/unaryLogging'
import { env } from '@utils/config/env'
import { type ToolUseConfirm } from '@components/permissions/PermissionRequest'
import { existsSync } from 'fs'
import chalk from 'chalk'
import {
  UnaryEvent,
  usePermissionRequestLogging,
} from '@hooks/usePermissionRequestLogging'
import { FileWriteToolDiff } from './FileWriteToolDiff'
import { useTerminalSize } from '@hooks/useTerminalSize'
import { getPermissionModeCycleShortcut } from '@utils/terminal/permissionModeCycleShortcut'
import { usePermissionContext } from '@context/PermissionContext'
import { isPathInWorkingDirectories } from '@utils/permissions/fileToolPermissionEngine'

type Props = {
  toolUseConfirm: ToolUseConfirm
  onDone(): void
  verbose: boolean
}

export function FileWritePermissionRequest({
  toolUseConfirm,
  onDone,
  verbose,
}: Props): React.ReactNode {
  const { applyToolPermissionUpdate, toolPermissionContext } =
    usePermissionContext()
  const { file_path, content } = toolUseConfirm.input as {
    file_path: string
    content: string
  }
  const modeCycleShortcut = useMemo(() => getPermissionModeCycleShortcut(), [])
  const hasSessionSuggestion = (toolUseConfirm.suggestions?.length ?? 0) > 0
  const isInWorkingDir = isPathInWorkingDirectories(
    dirname(file_path),
    toolPermissionContext,
  )
  const sessionLabel = useMemo(() => {
    const dirPath = dirname(file_path)
    const dirName = basename(dirPath) || 'this directory'
    const shortcutHint = chalk.bold.hex(getTheme().warning)(
      `(${modeCycleShortcut.displayText})`,
    )
    return isInWorkingDir
      ? `Yes, allow all edits during this session ${shortcutHint}`
      : `Yes, allow all edits in ${chalk.bold(`${dirName}/`)} during this session ${shortcutHint}`
  }, [file_path, isInWorkingDir, modeCycleShortcut.displayText])
  const fileExists = useMemo(() => existsSync(file_path), [file_path])
  const unaryEvent = useMemo<UnaryEvent>(
    () => ({
      completion_type: 'write_file_single',
      language_name: extractLanguageName(file_path),
    }),
    [file_path],
  )
  const { columns } = useTerminalSize()
  usePermissionRequestLogging(toolUseConfirm, unaryEvent)

  const handleChoice = useCallback(
    (newValue: string) => {
      switch (newValue) {
        case 'yes':
          extractLanguageName(file_path).then(language => {
            logUnaryEvent({
              completion_type: 'write_file_single',
              event: 'accept',
              metadata: {
                language_name: language,
                message_id: toolUseConfirm.assistantMessage.message.id,
                platform: env.platform,
              },
            })
          })
          onDone()
          toolUseConfirm.onAllow('temporary')
          return
        case 'yes-session':
          extractLanguageName(file_path).then(language => {
            logUnaryEvent({
              completion_type: 'write_file_single',
              event: 'accept',
              metadata: {
                language_name: language,
                message_id: toolUseConfirm.assistantMessage.message.id,
                platform: env.platform,
              },
            })
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
          extractLanguageName(file_path).then(language => {
            logUnaryEvent({
              completion_type: 'write_file_single',
              event: 'reject',
              metadata: {
                language_name: language,
                message_id: toolUseConfirm.assistantMessage.message.id,
                platform: env.platform,
              },
            })
          })
          onDone()
          toolUseConfirm.onReject()
          return
      }
    },
    [
      applyToolPermissionUpdate,
      file_path,
      hasSessionSuggestion,
      onDone,
      toolUseConfirm,
    ],
  )

  useInput((inputChar, key) => {
    if (!modeCycleShortcut.check(inputChar, key)) return
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
        title={`${fileExists ? 'Edit' : 'Create'} file`}
        riskScore={toolUseConfirm.riskScore}
      />
      <Box flexDirection="column">
        <FileWriteToolDiff
          file_path={file_path}
          content={content}
          verbose={verbose}
          width={columns - 12}
        />
      </Box>
      <Box flexDirection="column">
        <Text>
          Do you want to {fileExists ? 'make this edit to' : 'create'}{' '}
          <Text bold>{basename(file_path)}</Text>?
        </Text>
        <Select
          options={[
            {
              label: 'Yes',
              value: 'yes',
            },
            ...(hasSessionSuggestion
              ? [
                  {
                    label: sessionLabel,
                    value: 'yes-session',
                  },
                ]
              : []),
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

async function extractLanguageName(file_path: string): Promise<string> {
  const ext = extname(file_path)
  if (!ext) {
    return 'unknown'
  }
  const Highlight = (await import('highlight.js')) as unknown as {
    default: { getLanguage(ext: string): { name: string | undefined } }
  }
  return Highlight.default.getLanguage(ext.slice(1))?.name ?? 'unknown'
}
