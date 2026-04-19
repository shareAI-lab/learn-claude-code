import { Box, Text, useInput } from 'ink'
import React, { useEffect, useMemo, useState } from 'react'
import { Select } from '@components/custom-select/select'
import TextInput from '@components/TextInput'
import { PermissionRequestTitle } from '@components/permissions/PermissionRequestTitle'
import type { ToolUseConfirm } from '@components/permissions/PermissionRequest'
import { getTheme } from '@utils/theme'
import { usePermissionContext } from '@context/PermissionContext'
import {
  getPlanConversationKey,
  getPlanFilePath,
  readPlanFile,
} from '@utils/plan/planMode'
import {
  launchExternalEditor,
  launchExternalEditorForFilePath,
} from '@utils/system/externalEditor'
import { writeFileSync } from 'fs'

type Props = {
  toolUseConfirm: ToolUseConfirm
  onDone(): void
  verbose: boolean
}

type ExitPlanModeOptionValue =
  | 'yes-bypass'
  | 'yes-accept'
  | 'yes-launch-swarm'
  | 'yes-default'
  | 'no'

type ExitPlanModeOption = { label: string; value: ExitPlanModeOptionValue }

function getExitPlanModeOptions(args: {
  bypassAvailable: boolean
  launchSwarmAvailable: boolean
  teammateCount: number
}): ExitPlanModeOption[] {
  const options: ExitPlanModeOption[] = []

  options.push(
    args.bypassAvailable
      ? { label: 'Yes, and bypass permissions', value: 'yes-bypass' }
      : { label: 'Yes, and auto-accept edits', value: 'yes-accept' },
  )

  if (args.launchSwarmAvailable) {
    options.push({
      label: `Yes, and launch swarm (${args.teammateCount} teammates)`,
      value: 'yes-launch-swarm',
    })
  }

  options.push({
    label: 'Yes, and manually approve edits',
    value: 'yes-default',
  })
  options.push({ label: 'No, keep planning', value: 'no' })

  return options
}

export function __getExitPlanModeOptionsForTests(args: {
  bypassAvailable: boolean
  launchSwarmAvailable: boolean
  teammateCount: number
}): ExitPlanModeOption[] {
  return getExitPlanModeOptions(args)
}

function planPlaceholder(): string {
  return 'No plan found. Please write your plan to the plan file first.'
}

export function ExitPlanModePermissionRequest({
  toolUseConfirm,
  onDone,
}: Props): React.ReactNode {
  const theme = getTheme()
  const { setMode } = usePermissionContext()

  const conversationKey = getPlanConversationKey(toolUseConfirm.toolUseContext)
  const planFilePath = useMemo(
    () => getPlanFilePath(undefined, conversationKey),
    [conversationKey],
  )

  const planFromInput =
    typeof (toolUseConfirm.input as any)?.plan === 'string' &&
    String((toolUseConfirm.input as any).plan).trim().length > 0
      ? String((toolUseConfirm.input as any).plan)
      : null
  const planSource: 'file' | 'input' = planFromInput ? 'input' : 'file'

  const [planText, setPlanText] = useState(() => {
    if (planSource === 'input') {
      return planFromInput!
    }
    const { content, exists } = readPlanFile(undefined, conversationKey)
    return exists ? content : planPlaceholder()
  })
  const [planExists, setPlanExists] = useState(() => {
    if (planSource === 'input') return false
    const { exists } = readPlanFile(undefined, conversationKey)
    return exists
  })
  const [planSaved, setPlanSaved] = useState(false)
  const [showRejectInput, setShowRejectInput] = useState(false)
  const [rejectFeedback, setRejectFeedback] = useState('')
  const [rejectError, setRejectError] = useState<string | null>(null)
  const [rejectCursorOffset, setRejectCursorOffset] = useState(0)
  const [focusedOption, setFocusedOption] =
    useState<ExitPlanModeOptionValue | null>(null)
  const [teammateCount, setTeammateCount] = useState(3)

  useEffect(() => {
    if (!planSaved) return
    const timeout = setTimeout(() => setPlanSaved(false), 5000)
    return () => clearTimeout(timeout)
  }, [planSaved])

  useInput((input, key) => {
    if (key.escape && !showRejectInput) {
      toolUseConfirm.onReject()
      onDone()
      return
    }

    if (key.tab && focusedOption === 'yes-launch-swarm') {
      setTeammateCount(prev => {
        const allowed = [2, 3, 4, 6, 8]
        const idx = Math.max(0, allowed.indexOf(prev))
        return allowed[(idx + 1) % allowed.length]!
      })
      return
    }

    if (!(key.ctrl && input.toLowerCase() === 'g')) return

    void (async () => {
      if (planSource === 'input') {
        const edited = await launchExternalEditor(planText)
        if (edited.text !== null) {
          setPlanText(edited.text)
          setPlanSaved(true)
        }
        return
      }

      if (!planExists) {
        const initial = planText === planPlaceholder() ? '# Plan\n' : planText
        try {
          writeFileSync(planFilePath, initial, 'utf-8')
        } catch {
          const edited = await launchExternalEditor(initial)
          if (edited.text !== null) {
            setPlanText(edited.text)
            setPlanSaved(true)
          }
          return
        }
      }

      const opened = await launchExternalEditorForFilePath(planFilePath)
      if (opened.ok) {
        const next = readPlanFile(undefined, conversationKey)
        setPlanExists(next.exists)
        setPlanText(next.exists ? next.content : planPlaceholder())
        setPlanSaved(true)
      }
    })()
  })

  const bypassAvailable =
    toolUseConfirm.toolUseContext.options?.safeMode !== true
  const launchSwarmAvailable = false
  const options = useMemo(
    () =>
      getExitPlanModeOptions({
        bypassAvailable,
        launchSwarmAvailable,
        teammateCount,
      }),
    [bypassAvailable, launchSwarmAvailable, teammateCount],
  )

  if (showRejectInput) {
    return (
      <Box
        flexDirection="column"
        borderStyle="round"
        borderColor={theme.permission}
        marginTop={1}
        paddingLeft={1}
        paddingRight={1}
        paddingBottom={1}
      >
        <PermissionRequestTitle title="No, keep planning" riskScore={null} />
        <Box flexDirection="column" paddingX={2} paddingY={1}>
          <Text dimColor>
            Type here to tell Kode Agent what to change (Enter submits, Esc
            cancels)
          </Text>
          {rejectError ? <Text color={theme.error}>{rejectError}</Text> : null}
          <TextInput
            value={rejectFeedback}
            onChange={value => {
              setRejectFeedback(value)
              setRejectError(null)
            }}
            onSubmit={() => {
              const trimmed = rejectFeedback.trim()
              if (!trimmed) {
                setRejectError('Please enter what you want changed.')
                return
              }
              toolUseConfirm.onReject(trimmed)
              onDone()
            }}
            onExit={() => {
              setShowRejectInput(false)
              setRejectFeedback('')
              setRejectError(null)
            }}
            columns={80}
            cursorOffset={rejectCursorOffset}
            onChangeCursorOffset={setRejectCursorOffset}
          />
        </Box>
      </Box>
    )
  }

  return (
    <Box
      flexDirection="column"
      borderStyle="round"
      borderColor={theme.permission}
      marginTop={1}
      paddingLeft={1}
      paddingRight={1}
      paddingBottom={1}
    >
      <PermissionRequestTitle title="Ready to code?" riskScore={null} />

      <Box flexDirection="column" paddingX={2} paddingY={1}>
        <Text>Here is Kode Agent&apos;s plan:</Text>
        <Box
          borderStyle="dashed"
          borderColor={theme.secondaryBorder}
          borderDimColor
          borderLeft={false}
          borderRight={false}
          paddingX={1}
          paddingY={0}
          marginBottom={1}
          flexDirection="column"
        >
          <Text>{planText}</Text>
        </Box>
      </Box>

      <Box flexDirection="column" paddingX={2}>
        <Text dimColor>
          Tip: Press ctrl+g to edit{' '}
          {planSource === 'file' ? `plan file: ${planFilePath}` : 'plan text'}
          {planSaved ? ' · Plan saved!' : ''}
        </Text>
      </Box>

      <Box flexDirection="column" marginTop={1}>
        <Text dimColor>Would you like to proceed?</Text>
        <Select
          options={options}
          onFocus={value => setFocusedOption(value as ExitPlanModeOptionValue)}
          onChange={value => {
            if (value === 'no') {
              setShowRejectInput(true)
              return
            }

            const nextMode =
              value === 'yes-bypass'
                ? 'bypassPermissions'
                : value === 'yes-accept'
                  ? 'acceptEdits'
                  : value === 'yes-launch-swarm'
                    ? 'bypassPermissions'
                    : 'default'

            setMode(nextMode)

            if (value === 'yes-launch-swarm') {
              ;(toolUseConfirm.input as any).launchSwarm = true
              ;(toolUseConfirm.input as any).teammateCount = teammateCount
            }

            toolUseConfirm.onAllow('temporary')
            onDone()
          }}
        />
      </Box>
    </Box>
  )
}
