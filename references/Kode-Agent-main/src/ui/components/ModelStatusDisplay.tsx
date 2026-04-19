import React from 'react'
import { Text, Box } from 'ink'
import { getModelManager } from '@utils/model'
import { getGlobalConfig } from '@utils/config'
import { useExitOnCtrlCD } from '@hooks/useExitOnCtrlCD'
import { getTheme } from '@utils/theme'

type Props = {
  onClose: () => void
}

export function ModelStatusDisplay({ onClose }: Props): React.ReactNode {
  const theme = getTheme()
  const exitState = useExitOnCtrlCD(onClose)

  try {
    const modelManager = getModelManager()
    const config = getGlobalConfig()

    const pointers = ['main', 'task', 'compact', 'quick'] as const

    return (
      <Box
        flexDirection="column"
        borderStyle="round"
        borderColor={theme.secondaryBorder}
        paddingX={2}
        paddingY={1}
      >
        <Text bold>
          📊 Current Model Status{' '}
          {exitState.pending
            ? `(press ${exitState.keyName} again to exit)`
            : ''}
        </Text>
        <Text> </Text>

        {pointers.map(pointer => {
          try {
            const model = modelManager.getModel(pointer)
            if (model && model.name && model.provider) {
              return (
                <Box key={pointer} flexDirection="column" marginBottom={1}>
                  <Text>
                    🎯{' '}
                    <Text bold color={theme.kode}>
                      {pointer.toUpperCase()}
                    </Text>{' '}
                    → {model.name}
                  </Text>
                  <Text color={theme.secondaryText}>
                    {' '}
                    Provider: {model.provider}
                  </Text>
                  <Text color={theme.secondaryText}>
                    {' '}
                    Model: {model.modelName || 'unknown'}
                  </Text>
                  <Text color={theme.secondaryText}>
                    {' '}
                    Context:{' '}
                    {model.contextLength
                      ? Math.round(model.contextLength / 1000)
                      : 'unknown'}
                    k tokens
                  </Text>
                  <Text color={theme.secondaryText}>
                    {' '}
                    Active: {model.isActive ? '✅' : '❌'}
                  </Text>
                </Box>
              )
            } else {
              return (
                <Box key={pointer} flexDirection="column" marginBottom={1}>
                  <Text>
                    🎯{' '}
                    <Text bold color={theme.kode}>
                      {pointer.toUpperCase()}
                    </Text>{' '}
                    → <Text color={theme.error}>❌ Not configured</Text>
                  </Text>
                </Box>
              )
            }
          } catch (pointerError) {
            return (
              <Box key={pointer} flexDirection="column" marginBottom={1}>
                <Text>
                  🎯{' '}
                  <Text bold color={theme.kode}>
                    {pointer.toUpperCase()}
                  </Text>{' '}
                  →{' '}
                  <Text color={theme.error}>
                    ❌ Error: {String(pointerError)}
                  </Text>
                </Text>
              </Box>
            )
          }
        })}

        <Text> </Text>
        <Text bold>📚 Available Models:</Text>

        {(() => {
          try {
            const availableModels = modelManager.getAvailableModels() || []

            if (availableModels.length === 0) {
              return (
                <Text color={theme.secondaryText}> No models configured</Text>
              )
            }

            return availableModels.map((model, index) => {
              try {
                const isInUse = pointers.some(p => {
                  try {
                    return (
                      modelManager.getModel(p)?.modelName === model.modelName
                    )
                  } catch {
                    return false
                  }
                })

                return (
                  <Box key={index} flexDirection="column" marginBottom={1}>
                    <Text>
                      {' '}
                      {isInUse ? '🔄' : '💤'} {model.name || 'Unnamed'}{' '}
                      <Text color={theme.secondaryText}>
                        ({model.provider || 'unknown'})
                      </Text>
                    </Text>
                    <Text color={theme.secondaryText}>
                      {' '}
                      Model: {model.modelName || 'unknown'}
                    </Text>
                    <Text color={theme.secondaryText}>
                      {' '}
                      Context:{' '}
                      {model.contextLength
                        ? Math.round(model.contextLength / 1000)
                        : 'unknown'}
                      k tokens
                    </Text>
                    {model.lastUsed && (
                      <Text color={theme.secondaryText}>
                        {' '}
                        Last used: {new Date(model.lastUsed).toLocaleString()}
                      </Text>
                    )}
                  </Box>
                )
              } catch (modelError) {
                return (
                  <Box key={index} flexDirection="column" marginBottom={1}>
                    <Text color={theme.error}>
                      {' '}
                      ❌ Model error: {String(modelError)}
                    </Text>
                  </Box>
                )
              }
            })
          } catch (availableModelsError) {
            return (
              <Text color={theme.error}>
                ❌ Error loading available models:{' '}
                {String(availableModelsError)}
              </Text>
            )
          }
        })()}

        <Text> </Text>
        <Text bold>🔧 Debug Info:</Text>
        <Text color={theme.secondaryText}>
          {' '}
          ModelProfiles: {config.modelProfiles?.length || 0} configured
        </Text>
        <Text color={theme.secondaryText}>
          {' '}
          DefaultModelId: {(config as any).defaultModelId || 'not set'}
        </Text>
        {config.modelPointers && (
          <>
            <Text color={theme.secondaryText}>
              {' '}
              ModelPointers configured:{' '}
              {Object.keys(config.modelPointers).length > 0 ? 'Yes' : 'No'}
            </Text>
            {Object.entries(config.modelPointers).map(([pointer, modelId]) => (
              <React.Fragment key={pointer}>
                <Text color={theme.secondaryText}>
                  {' '}
                  {pointer}: {modelId || 'not set'}
                </Text>
              </React.Fragment>
            ))}
          </>
        )}
      </Box>
    )
  } catch (error) {
    return (
      <Box
        flexDirection="column"
        borderStyle="round"
        borderColor={theme.error}
        paddingX={2}
        paddingY={1}
      >
        <Text bold>
          📊 Model Status Error{' '}
          {exitState.pending
            ? `(press ${exitState.keyName} again to exit)`
            : ''}
        </Text>
        <Text color={theme.error}>
          ❌ Error reading model status: {String(error)}
        </Text>
      </Box>
    )
  }
}
