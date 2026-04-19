import { Box, Text, useInput } from 'ink'
import * as React from 'react'
import { useState } from 'react'
import figures from 'figures'
import { getTheme } from '@utils/theme'
import { GlobalConfig, saveGlobalConfig, getGlobalConfig } from '@utils/config'
import chalk from 'chalk'
import { useExitOnCtrlCD } from '@hooks/useExitOnCtrlCD'
import { getModelManager } from '@utils/model'

type Props = {
  onClose: () => void
}

type Setting =
  | {
      id: string
      label: string
      value: boolean
      onChange(value: boolean): void
      type: 'boolean'
      disabled?: boolean
    }
  | {
      id: string
      label: string
      value: string
      options: string[]
      onChange(value: string): void
      type: 'enum'
      disabled?: boolean
    }
  | {
      id: string
      label: string
      value: string
      onChange(value: string): void
      type: 'string'
      disabled?: boolean
    }
  | {
      id: string
      label: string
      value: number
      onChange(value: number): void
      type: 'number'
      disabled?: boolean
    }

export function Config({ onClose }: Props): React.ReactNode {
  const [globalConfig, setGlobalConfig] = useState(getGlobalConfig())
  const initialConfig = React.useRef(getGlobalConfig())
  const [selectedIndex, setSelectedIndex] = useState(0)
  const exitState = useExitOnCtrlCD(() => process.exit(0))
  const [editingString, setEditingString] = useState(false)
  const [currentInput, setCurrentInput] = useState('')
  const [inputError, setInputError] = useState<string | null>(null)

  const modelManager = getModelManager()
  const activeProfiles = modelManager.getAvailableModels()

  const settings: Setting[] = [
    {
      id: 'theme',
      label: 'Theme',
      value: globalConfig.theme ?? 'dark',
      options: ['dark', 'light'],
      onChange(theme: string) {
        const config = { ...getGlobalConfig(), theme: theme as any }
        saveGlobalConfig(config)
        setGlobalConfig(config)
      },
      type: 'enum',
    },
    {
      id: 'verbose',
      label: 'Verbose mode',
      value: globalConfig.verbose ?? false,
      onChange(verbose: boolean) {
        const config = { ...getGlobalConfig(), verbose }
        saveGlobalConfig(config)
        setGlobalConfig(config)
      },
      type: 'boolean',
    },
    {
      id: 'stream',
      label: 'Stream responses',
      value: globalConfig.stream ?? true,
      onChange(stream: boolean) {
        const config = { ...getGlobalConfig(), stream }
        saveGlobalConfig(config)
        setGlobalConfig(config)
      },
      type: 'boolean',
    },
  ]

  const theme = getTheme()

  useInput((input, key) => {
    if (editingString) {
      if (key.return) {
        const currentSetting = settings[selectedIndex]
        if (currentSetting?.type === 'string') {
          try {
            currentSetting.onChange(currentInput)
            setEditingString(false)
            setCurrentInput('')
            setInputError(null)
          } catch (error) {
            setInputError(
              error instanceof Error ? error.message : 'Invalid input',
            )
          }
        } else if (currentSetting?.type === 'number') {
          const numValue = parseFloat(currentInput)
          if (isNaN(numValue)) {
            setInputError('Please enter a valid number')
          } else {
            try {
              ;(currentSetting as any).onChange(numValue)
              setEditingString(false)
              setCurrentInput('')
              setInputError(null)
            } catch (error) {
              setInputError(
                error instanceof Error ? error.message : 'Invalid input',
              )
            }
          }
        }
      } else if (key.escape) {
        setEditingString(false)
        setCurrentInput('')
        setInputError(null)
      } else if (key.delete || key.backspace) {
        setCurrentInput(prev => prev.slice(0, -1))
      } else if (input) {
        setCurrentInput(prev => prev + input)
      }
      return
    }

    if (key.upArrow && !exitState.pending) {
      setSelectedIndex(prev => Math.max(0, prev - 1))
    } else if (key.downArrow && !exitState.pending) {
      setSelectedIndex(prev => Math.min(settings.length - 1, prev + 1))
    } else if (key.return && !exitState.pending) {
      const currentSetting = settings[selectedIndex]
      if (currentSetting?.disabled) return

      if (currentSetting?.type === 'boolean') {
        currentSetting.onChange(!currentSetting.value)
      } else if (currentSetting?.type === 'enum') {
        const currentIndex = currentSetting.options.indexOf(
          currentSetting.value,
        )
        const nextIndex = (currentIndex + 1) % currentSetting.options.length
        currentSetting.onChange(currentSetting.options[nextIndex])
      } else if (
        currentSetting?.type === 'string' ||
        currentSetting?.type === 'number'
      ) {
        setCurrentInput(String(currentSetting.value))
        setEditingString(true)
        setInputError(null)
      }
    } else if (key.escape && !exitState.pending) {
      const currentConfigString = JSON.stringify(getGlobalConfig())
      const initialConfigString = JSON.stringify(initialConfig.current)

      if (currentConfigString !== initialConfigString) {
        saveGlobalConfig(getGlobalConfig())
      }

      onClose()
    }
  })

  return (
    <Box flexDirection="column" gap={1}>
      <Box
        flexDirection="column"
        borderStyle="round"
        borderColor={theme.secondaryBorder}
        paddingX={2}
        paddingY={1}
        gap={1}
      >
        <Text bold>
          Configuration{' '}
          {exitState.pending
            ? `(press ${exitState.keyName} again to exit)`
            : ''}
        </Text>

        <Box flexDirection="column" marginY={1}>
          <Text bold color={theme.success}>
            Model Configuration:
          </Text>
          {activeProfiles.length === 0 ? (
            <Text color={theme.secondaryText}>
              No models configured. Use /model to add models.
            </Text>
          ) : (
            <Box flexDirection="column" marginLeft={2}>
              {activeProfiles.map(profile => (
                <React.Fragment key={profile.modelName}>
                  <Text color={theme.secondaryText}>
                    • {profile.name} ({profile.provider})
                  </Text>
                </React.Fragment>
              ))}
              <Box marginTop={1}>
                <Text color={theme.suggestion}>
                  Use /model to manage model configurations
                </Text>
              </Box>
            </Box>
          )}
        </Box>

        <Box flexDirection="column">
          {settings.map((setting, index) => (
            <Box key={setting.id} flexDirection="column">
              <Box flexDirection="row" gap={1}>
                <Text
                  color={
                    index === selectedIndex
                      ? theme.success
                      : setting.disabled
                        ? theme.secondaryText
                        : theme.text
                  }
                >
                  {index === selectedIndex ? figures.pointer : ' '}{' '}
                  {setting.label}
                </Text>
                <Text
                  color={
                    setting.disabled ? theme.secondaryText : theme.suggestion
                  }
                >
                  {setting.type === 'boolean'
                    ? setting.value
                      ? 'enabled'
                      : 'disabled'
                    : setting.type === 'enum'
                      ? setting.value
                      : String(setting.value)}
                </Text>
              </Box>
              {index === selectedIndex && editingString && (
                <Box flexDirection="column" marginLeft={2}>
                  <Text color={theme.suggestion}>
                    Enter new value: {currentInput}
                  </Text>
                  {inputError && <Text color="red">{inputError}</Text>}
                </Box>
              )}
            </Box>
          ))}
        </Box>

        <Box marginTop={1}>
          <Text dimColor>
            {editingString ? (
              'Enter to save · Esc to cancel'
            ) : (
              <>
                ↑/↓ to navigate · Enter to change · Esc to close
                <Text color={theme.suggestion}>
                  {' '}
                  · Use /model for model config
                </Text>
              </>
            )}
          </Text>
        </Box>
      </Box>
    </Box>
  )
}
