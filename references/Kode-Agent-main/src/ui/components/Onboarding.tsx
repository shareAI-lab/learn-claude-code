import React, { useState } from 'react'
import { PRODUCT_NAME } from '@constants/product'
import { Box, Newline, Text, useInput } from 'ink'
import {
  getGlobalConfig,
  saveGlobalConfig,
  DEFAULT_GLOBAL_CONFIG,
  ProviderType,
} from '@utils/config'
import { OrderedList } from '@inkjs/ui'
import { useExitOnCtrlCD } from '@hooks/useExitOnCtrlCD'
import { MIN_LOGO_WIDTH } from './Logo'
import { Select } from './custom-select/select'
import { StructuredDiff } from './StructuredDiff'
import { getTheme, type ThemeNames } from '@utils/theme'
import { clearTerminal } from '@utils/terminal'
import { PressEnterToContinue } from './PressEnterToContinue'
import { ModelSelector } from './ModelSelector'
type StepId = 'theme' | 'usage' | 'providers' | 'model'

interface OnboardingStep {
  id: StepId
  component: React.ReactNode
}

type Props = {
  onDone(): void
}

export function Onboarding({ onDone }: Props): React.ReactNode {
  const [currentStepIndex, setCurrentStepIndex] = useState(0)
  const [showModelSelector, setShowModelSelector] = useState(false)
  const config = getGlobalConfig()

  const [selectedTheme, setSelectedTheme] = useState(
    DEFAULT_GLOBAL_CONFIG.theme,
  )
  const theme = getTheme()
  function goToNextStep() {
    if (currentStepIndex < steps.length - 1) {
      const nextIndex = currentStepIndex + 1
      setCurrentStepIndex(nextIndex)
    }
  }

  function handleThemeSelection(newTheme: string) {
    saveGlobalConfig({
      ...config,
      theme: newTheme as ThemeNames,
    })
    goToNextStep()
  }

  function handleThemePreview(newTheme: string) {
    setSelectedTheme(newTheme as ThemeNames)
  }

  function handleProviderSelectionDone() {
    goToNextStep()
  }

  function handleModelSelectionDone() {
    onDone()
  }

  const exitState = useExitOnCtrlCD(() => process.exit(0))

  useInput(
    async (_, key) => {
      const currentStep = steps[currentStepIndex]
      if (
        key.return &&
        currentStep &&
        ['usage', 'providers', 'model'].includes(currentStep.id)
      ) {
        if (currentStep.id === 'model') {
          setShowModelSelector(true)
        } else if (currentStepIndex === steps.length - 1) {
          onDone()
        } else {
          await clearTerminal()
          goToNextStep()
        }
      }
    },
    { isActive: !showModelSelector },
  )

  const themeStep = (
    <Box flexDirection="column" gap={1} paddingLeft={1}>
      <Text>Let&apos;s get started.</Text>
      <Box flexDirection="column">
        <Text bold>Choose the option that looks best when you select it:</Text>
        <Text dimColor>To change this later, run /config</Text>
      </Box>
      <Select
        options={[
          { label: 'Light text', value: 'dark' },
          { label: 'Dark text', value: 'light' },
          {
            label: 'Light text (colorblind-friendly)',
            value: 'dark-daltonized',
          },
          {
            label: 'Dark text (colorblind-friendly)',
            value: 'light-daltonized',
          },
        ]}
        onFocus={handleThemePreview}
        onChange={handleThemeSelection}
      />
      <Box flexDirection="column">
        <Box
          paddingLeft={1}
          marginRight={1}
          borderStyle="round"
          borderColor="gray"
          flexDirection="column"
        >
          <StructuredDiff
            patch={{
              oldStart: 1,
              newStart: 1,
              oldLines: 3,
              newLines: 3,
              lines: [
                'function greet() {',
                '-  console.log("Hello, World!");',
                '+  console.log("Hello, anon!");',
                '}',
              ],
            }}
            dim={false}
            width={40}
            overrideTheme={selectedTheme}
          />
        </Box>
      </Box>
    </Box>
  )

  const providersStep = (
    <Box flexDirection="column" gap={1} paddingLeft={1}>
      <Box flexDirection="column" width={70}>
        <Text color={theme.secondaryText}>
          Next, let's select your preferred AI provider and model.
        </Text>
      </Box>
      <ModelSelector
        onDone={handleProviderSelectionDone}
        skipModelType={true}
        isOnboarding={true}
      />
    </Box>
  )

  const usageStep = (
    <Box flexDirection="column" gap={1} paddingLeft={1}>
      <Text bold>Using {PRODUCT_NAME} effectively:</Text>
      <Box flexDirection="column" width={70}>
        <OrderedList children={[]}>
          <OrderedList.Item children={[]}>
            <Text>
              Start in your project directory
              <Newline />
              <Text color={theme.secondaryText}>
                Files are automatically added to context when needed.
              </Text>
              <Newline />
            </Text>
          </OrderedList.Item>
          <OrderedList.Item children={[]}>
            <Text>
              Use {PRODUCT_NAME} as a development partner
              <Newline />
              <Text color={theme.secondaryText}>
                Get help with file analysis, editing, bash commands,
                <Newline />
                and git history.
                <Newline />
              </Text>
            </Text>
          </OrderedList.Item>
          <OrderedList.Item children={[]}>
            <Text>
              Provide clear context
              <Newline />
              <Text color={theme.secondaryText}>
                Be as specific as you would with another engineer. <Newline />
                The better the context, the better the results. <Newline />
              </Text>
            </Text>
          </OrderedList.Item>
        </OrderedList>
      </Box>
      <PressEnterToContinue />
    </Box>
  )

  const modelStep = (
    <Box flexDirection="column" gap={1} paddingLeft={1}>
      <Text bold>Configure your models:</Text>
      <Box flexDirection="column" width={70}>
        <Text>
          You can customize which models {PRODUCT_NAME} uses for different
          tasks.
          <Newline />
          <Text color={theme.secondaryText}>
            Let's set up your preferred models for large and small tasks.
          </Text>
        </Text>
        <Box marginTop={1}>
          <Text>
            Press <Text color={theme.suggestion}>Enter</Text> to continue to the
            model selection screen.
          </Text>
        </Box>
      </Box>
      <PressEnterToContinue />
    </Box>
  )

  const steps: OnboardingStep[] = []
  steps.push({ id: 'theme', component: themeStep })
  steps.push({ id: 'usage', component: usageStep })

  steps.push({ id: 'model', component: modelStep })

  if (showModelSelector) {
    return (
      <ModelSelector
        onDone={handleModelSelectionDone}
        skipModelType={true}
        isOnboarding={true}
      />
    )
  }

  return (
    <Box flexDirection="column" gap={1}>
      <>
        <Box flexDirection="column" gap={1}>
          <Text bold>
            {PRODUCT_NAME}{' '}
            {exitState.pending
              ? `(press ${exitState.keyName} again to exit)`
              : ''}
          </Text>
          {steps[currentStepIndex]?.component}
        </Box>
      </>
    </Box>
  )
}

export function WelcomeBox(): React.ReactNode {
  const theme = getTheme()
  return (
    <Box
      borderColor={theme.kode}
      borderStyle="round"
      paddingX={1}
      width={MIN_LOGO_WIDTH}
    >
      <Text>
        <Text color={theme.kode}>✻</Text> Welcome to{' '}
        <Text bold>{PRODUCT_NAME}</Text> research preview!
      </Text>
    </Box>
  )
}
