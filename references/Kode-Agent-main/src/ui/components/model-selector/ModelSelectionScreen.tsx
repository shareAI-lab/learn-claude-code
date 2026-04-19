import React from 'react'
import { Box, Text } from 'ink'
import { Select } from '../custom-select/select'
import TextInput from '../TextInput'
import type { ModelInfo } from './types'
import { buildModelOptions } from './filterModels'

type Props = {
  theme: any
  exitState: { pending: boolean; keyName?: string }
  providerLabel: string
  modelTypeText: string

  availableModels: ModelInfo[]
  modelSearchQuery: string
  onModelSearchChange: (value: string) => void
  modelSearchCursorOffset: number
  onModelSearchCursorOffsetChange: (offset: number) => void
  onModelSelect: (model: string) => void
}

export function ModelSelectionScreen({
  theme,
  exitState,
  providerLabel,
  modelTypeText,
  availableModels,
  modelSearchQuery,
  onModelSearchChange,
  modelSearchCursorOffset,
  onModelSearchCursorOffsetChange,
  onModelSelect,
}: Props): React.ReactNode {
  const modelOptions = buildModelOptions(availableModels, modelSearchQuery)

  return (
    <Box flexDirection="column" gap={1}>
      <Box
        flexDirection="column"
        gap={1}
        borderStyle="round"
        borderColor={theme.secondaryBorder}
        paddingX={2}
        paddingY={1}
      >
        <Text bold>
          Model Selection{' '}
          {exitState.pending ? `(press ${exitState.keyName} again to exit)` : ''}
        </Text>
        <Box flexDirection="column" gap={1}>
          <Text bold>
            Select a model from {providerLabel} for {modelTypeText}:
          </Text>
          <Box flexDirection="column" width={70}>
            <Text color={theme.secondaryText}>
              This model profile can be assigned to different pointers (main,
              task, compact, quick) for various use cases.
            </Text>
          </Box>

          <Box marginY={1}>
            <Text bold>Search models:</Text>
            <TextInput
              placeholder="Type to filter models..."
              value={modelSearchQuery}
              onChange={onModelSearchChange}
              columns={100}
              cursorOffset={modelSearchCursorOffset}
              onChangeCursorOffset={onModelSearchCursorOffsetChange}
              showCursor={true}
              focus={true}
            />
          </Box>

          {modelOptions.length > 0 ? (
            <>
              <Select
                options={modelOptions}
                onChange={onModelSelect}
                visibleOptionCount={15}
              />
              <Text dimColor>
                Showing {modelOptions.length} of {availableModels.length} models
              </Text>
            </>
          ) : (
            <Box>
              {availableModels.length > 0 ? (
                <Text color="yellow">
                  No models match your search. Try a different query.
                </Text>
              ) : (
                <Text color="yellow">No models available for this provider.</Text>
              )}
            </Box>
          )}

          <Box marginTop={1}>
            <Text dimColor>
              Press <Text color={theme.suggestion}>Esc</Text> to go back to API
              key input
            </Text>
          </Box>
        </Box>
      </Box>
    </Box>
  )
}
