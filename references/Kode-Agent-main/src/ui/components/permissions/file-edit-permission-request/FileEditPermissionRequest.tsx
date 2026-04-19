import { Select } from '@components/custom-select/select'
import chalk from 'chalk'
import { Box, Text, useInput } from 'ink'
import { basename, dirname, extname } from 'path'
import React, { useCallback, useMemo } from 'react'
import {
  UnaryEvent,
  usePermissionRequestLogging,
} from '@hooks/usePermissionRequestLogging'
import { env } from '@utils/config/env'
import { getTheme } from '@utils/theme'
import { logUnaryEvent } from '@utils/log/unaryLogging'
import { type ToolUseConfirm } from '@components/permissions/PermissionRequest'
import {
  PermissionRequestTitle,
  textColorForRiskScore,
} from '@components/permissions/PermissionRequestTitle'
import { FileEditToolDiff } from './FileEditToolDiff'
import { useTerminalSize } from '@hooks/useTerminalSize'
import { getPermissionModeCycleShortcut } from '@utils/terminal/permissionModeCycleShortcut'
import { usePermissionContext } from '@context/PermissionContext'
import { isPathInWorkingDirectories } from '@utils/permissions/fileToolPermissionEngine'

function getOptions(args: {
  path: string
  modeCycleShortcut: string
  isInWorkingDir: boolean
  hasSessionSuggestion: boolean
}) {
  const dirPath = dirname(args.path)
  const dirName = basename(dirPath) || 'this directory'

  const options = [
    {
      label: 'Yes',
      value: 'yes',
    },
    {
      label: `No, and provide instructions (${chalk.bold.hex(getTheme().warning)('esc')})`,
      value: 'no',
    },
  ]

  if (args.hasSessionSuggestion) {
    const shortcutHint = chalk.bold.hex(getTheme().warning)(
      `(${args.modeCycleShortcut})`,
    )
    const sessionLabel = args.isInWorkingDir
      ? `Yes, allow all edits during this session ${shortcutHint}`
      : `Yes, allow all edits in ${chalk.bold(`${dirName}/`)} during this session ${shortcutHint}`
    options.splice(1, 0, { label: sessionLabel, value: 'yes-session' })
  }

  return options
}

type Props = {
  toolUseConfirm: ToolUseConfirm
  onDone(): void
  verbose: boolean
}

export function FileEditPermissionRequest({
  toolUseConfirm,
  onDone,
  verbose,
}: Props): React.ReactNode {
  const { columns } = useTerminalSize()
  const { applyToolPermissionUpdate, toolPermissionContext } =
    usePermissionContext()
  const { file_path, new_string, old_string } = toolUseConfirm.input as {
    file_path: string
    new_string: string
    old_string: string
  }
  const modeCycleShortcut = useMemo(() => getPermissionModeCycleShortcut(), [])
  const hasSessionSuggestion = (toolUseConfirm.suggestions?.length ?? 0) > 0
  const isInWorkingDir = isPathInWorkingDirectories(
    dirname(file_path),
    toolPermissionContext,
  )

  const unaryEvent = useMemo<UnaryEvent>(
    () => ({
      completion_type: 'str_replace_single',
      language_name: extractLanguageName(file_path),
    }),
    [file_path],
  )

  usePermissionRequestLogging(toolUseConfirm, unaryEvent)

  const handleChoice = useCallback(
    (newValue: string) => {
      switch (newValue) {
        case 'yes':
          extractLanguageName(file_path).then(language => {
            logUnaryEvent({
              completion_type: 'str_replace_single',
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
              completion_type: 'str_replace_single',
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
              completion_type: 'str_replace_single',
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
        title="Edit file"
        riskScore={toolUseConfirm.riskScore}
      />
      <FileEditToolDiff
        file_path={file_path}
        new_string={new_string}
        old_string={old_string}
        verbose={verbose}
        width={columns - 12}
      />
      <Box flexDirection="column">
        <Text>
          Do you want to make this edit to{' '}
          <Text bold>{basename(file_path)}</Text>?
        </Text>
        <Select
          options={getOptions({
            path: file_path,
            modeCycleShortcut: modeCycleShortcut.displayText,
            isInWorkingDir,
            hasSessionSuggestion,
          })}
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
