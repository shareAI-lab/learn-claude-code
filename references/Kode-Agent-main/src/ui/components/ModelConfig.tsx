import { Box, Text, useInput } from 'ink'
import * as React from 'react'
import { useState, useCallback, useEffect, useRef } from 'react'
import figures from 'figures'
import { getTheme } from '@utils/theme'
import {
  getGlobalConfig,
  saveGlobalConfig,
  ModelPointerType,
  setModelPointer,
} from '@utils/config'
import { getModelManager } from '@utils/model'
import { useExitOnCtrlCD } from '@hooks/useExitOnCtrlCD'
import { ModelSelector } from './ModelSelector'
import { ModelListManager } from './ModelListManager'

type Props = {
  onClose: () => void
}

type ModelPointerSetting = {
  id: ModelPointerType | 'add-new'
  label: string
  description: string
  value: string
  options: Array<{ id: string; name: string }>
  type: 'modelPointer' | 'action'
  onChange(value?: string): void
}

export function ModelConfig({ onClose }: Props): React.ReactNode {
  const config = getGlobalConfig()
  const theme = getTheme()
  const [selectedIndex, setSelectedIndex] = useState(0)
  const [showModelSelector, setShowModelSelector] = useState(false)
  const [showModelListManager, setShowModelListManager] = useState(false)
  const [currentPointer, setCurrentPointer] = useState<ModelPointerType | null>(
    null,
  )
  const [refreshKey, setRefreshKey] = useState(0)
  const [isDeleteMode, setIsDeleteMode] = useState(false)
  const selectedIndexRef = useRef(selectedIndex)
  const exitState = useExitOnCtrlCD(() => process.exit(0))

  const modelManager = getModelManager()

  useEffect(() => {
    selectedIndexRef.current = selectedIndex
  }, [selectedIndex])

  const availableModels = React.useMemo((): Array<{
    id: string
    name: string
  }> => {
    const profiles = modelManager.getAvailableModels()
    return profiles.map(p => ({ id: p.modelName, name: p.name }))
  }, [modelManager, refreshKey])

  const menuItems = React.useMemo(() => {
    const modelSettings: ModelPointerSetting[] = [
      {
        id: 'main',
        label: 'Main Model',
        description: 'Primary model for general tasks and conversations',
        value: config.modelPointers?.main || '',
        options: availableModels,
        type: 'modelPointer' as const,
        onChange: (value: string) => handleModelPointerChange('main', value),
      },
      {
        id: 'task',
        label: 'Task Model',
        description: 'Model for TaskTool sub-agents and automation',
        value: config.modelPointers?.task || '',
        options: availableModels,
        type: 'modelPointer' as const,
        onChange: (value: string) => handleModelPointerChange('task', value),
      },
      {
        id: 'compact',
        label: 'Compact Model',
        description:
          'Model used for context compression when nearing the context window',
        value: config.modelPointers?.compact || '',
        options: availableModels,
        type: 'modelPointer' as const,
        onChange: (value: string) => handleModelPointerChange('compact', value),
      },
      {
        id: 'quick',
        label: 'Quick Model',
        description: 'Fast model for simple operations and utilities',
        value: config.modelPointers?.quick || '',
        options: availableModels,
        type: 'modelPointer' as const,
        onChange: (value: string) => handleModelPointerChange('quick', value),
      },
    ]

    return [
      ...modelSettings,
      {
        id: 'manage-models',
        label: 'Manage Model List',
        description: 'View, add, and delete model configurations',
        value: '',
        options: [],
        type: 'action' as const,
        onChange: () => handleManageModels(),
      },
    ]
  }, [config.modelPointers, availableModels, refreshKey])

  const handleModelPointerChange = (
    pointer: ModelPointerType,
    modelId: string,
  ) => {
    setModelPointer(pointer, modelId)
    setRefreshKey(prev => prev + 1)
  }

  const handleManageModels = () => {
    setShowModelListManager(true)
  }

  const handleModelConfigurationComplete = () => {
    setShowModelSelector(false)
    setShowModelListManager(false)
    setCurrentPointer(null)
    setRefreshKey(prev => prev + 1)
    const manageIndex = menuItems.findIndex(item => item.id === 'manage-models')
    if (manageIndex !== -1) {
      setSelectedIndex(manageIndex)
    }
  }

  const handleInput = useCallback(
    (input: string, key: any) => {
      if (key.escape) {
        if (isDeleteMode) {
          setIsDeleteMode(false)
        } else {
          onClose()
        }
      } else if (input === 'd' && !isDeleteMode) {
        setIsDeleteMode(true)
      } else if (key.upArrow) {
        setSelectedIndex(prev => Math.max(0, prev - 1))
      } else if (key.downArrow) {
        setSelectedIndex(prev => Math.min(menuItems.length - 1, prev + 1))
      } else if (key.return || input === ' ') {
        const setting = menuItems[selectedIndex]

        if (isDeleteMode && setting.type === 'modelPointer' && setting.value) {
          setModelPointer(setting.id as ModelPointerType, '')
          setRefreshKey(prev => prev + 1)
          setIsDeleteMode(false)
        } else if (setting.type === 'modelPointer') {
          if (setting.options.length === 0) {
            handleManageModels()
            return
          }
          const currentIndex = setting.options.findIndex(
            opt => opt.id === setting.value,
          )
          const nextIndex = (currentIndex + 1) % setting.options.length
          const nextOption = setting.options[nextIndex]
          if (nextOption) {
            setting.onChange(nextOption.id)
          }
        } else if (setting.type === 'action') {
          setting.onChange()
        }
      }
    },
    [selectedIndex, menuItems, onClose, isDeleteMode, modelManager],
  )

  useInput(handleInput, {
    isActive: !showModelSelector && !showModelListManager,
  })

  if (showModelListManager) {
    return <ModelListManager onClose={handleModelConfigurationComplete} />
  }

  if (showModelSelector) {
    return (
      <ModelSelector
        onDone={handleModelConfigurationComplete}
        onCancel={handleModelConfigurationComplete}
        skipModelType={true}
        targetPointer={currentPointer || undefined}
        isOnboarding={false}
        abortController={new AbortController()}
      />
    )
  }

  return (
    <Box
      flexDirection="column"
      borderStyle="round"
      borderColor={theme.secondaryBorder}
      paddingX={1}
      marginTop={1}
    >
      <Box flexDirection="column" minHeight={2} marginBottom={1}>
        <Text bold>
          Model Configuration{isDeleteMode ? ' - CLEAR MODE' : ''}
        </Text>
        <Text dimColor>
          {isDeleteMode
            ? 'Press Enter/Space to clear selected pointer assignment, Esc to cancel'
            : availableModels.length === 0
              ? 'No models configured. Use "Configure New Model" to add your first model.'
              : 'Configure which models to use for different tasks. Space to cycle, Enter to configure.'}
        </Text>
      </Box>

      {menuItems.map((setting, i) => {
        const isSelected = i === selectedIndex
        let displayValue = ''
        let actionText = ''

        if (setting.type === 'modelPointer') {
          const currentModel = setting.options.find(
            opt => opt.id === setting.value,
          )
          displayValue = currentModel?.name || '(not configured)'
          actionText = isSelected ? ' [Space to cycle]' : ''
        } else if (setting.type === 'action') {
          displayValue = ''
          actionText = isSelected ? ' [Enter to configure]' : ''
        }

        return (
          <Box key={setting.id} flexDirection="column">
            <Box>
              <Box width={44}>
                <Text color={isSelected ? 'blue' : undefined}>
                  {isSelected ? figures.pointer : ' '} {setting.label}
                </Text>
              </Box>
              <Box>
                {setting.type === 'modelPointer' && (
                  <Text
                    color={
                      displayValue !== '(not configured)'
                        ? theme.success
                        : theme.warning
                    }
                  >
                    {displayValue}
                  </Text>
                )}
                {actionText && <Text color="blue">{actionText}</Text>}
              </Box>
            </Box>
            {isSelected && (
              <Box paddingLeft={2} marginBottom={1}>
                <Text dimColor>{setting.description}</Text>
              </Box>
            )}
          </Box>
        )
      })}

      <Box
        marginTop={1}
        paddingTop={1}
        borderTopColor={theme.secondaryBorder}
        borderTopStyle="single"
      >
        <Text dimColor>
          {isDeleteMode
            ? 'CLEAR MODE: Press Enter/Space to clear assignment, Esc to cancel'
            : availableModels.length === 0
              ? 'Use ↑/↓ to navigate, Enter to configure new model, Esc to exit'
              : 'Use ↑/↓ to navigate, Space to cycle models, Enter to configure, d to clear, Esc to exit'}
        </Text>
      </Box>
    </Box>
  )
}
