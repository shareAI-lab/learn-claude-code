import { useState, useCallback, useEffect, useRef } from 'react'
import { useInput, type Key } from 'ink'
import { getCwd } from '@utils/state'
import { getActiveAgents } from '@utils/agent/loader'
import { getModelManager } from '@utils/model'
import { debug as debugLogger } from '@utils/log/debugLogger'
import { logError } from '@utils/log'
import { getCompletionContext } from '@utils/completion/context'
import { generateSuggestionsForContext } from '@utils/completion/generateSuggestions'
import {
  getEssentialCommands,
  getMinimalFallbackCommands,
} from '@utils/completion/commonUnixCommands'
import type {
  CompletionContext,
  UnifiedSuggestion,
} from '@utils/completion/types'
import type { Command } from '@commands'

export type { UnifiedSuggestion } from '@utils/completion/types'

interface Props {
  input: string
  cursorOffset: number
  onInputChange: (value: string) => void
  setCursorOffset: (offset: number) => void
  commands: Command[]
  disableSlashCommands?: boolean
  onSubmit?: (value: string, isSubmittingSlashCommand?: boolean) => void
}

interface CompletionState {
  suggestions: UnifiedSuggestion[]
  selectedIndex: number
  isActive: boolean
  context: CompletionContext | null
  preview: {
    isActive: boolean
    originalInput: string
    wordRange: [number, number]
  } | null
  emptyDirMessage: string
  suppressUntil: number
}

const INITIAL_STATE: CompletionState = {
  suggestions: [],
  selectedIndex: 0,
  isActive: false,
  context: null,
  preview: null,
  emptyDirMessage: '',
  suppressUntil: 0,
}

export function __getCompletionContextForTests(args: {
  input: string
  cursorOffset: number
  disableSlashCommands?: boolean
}): CompletionContext | null {
  return getCompletionContext(args)
}

export function useUnifiedCompletion({
  input,
  cursorOffset,
  onInputChange,
  setCursorOffset,
  commands,
  disableSlashCommands = false,
  onSubmit,
}: Props) {
  const [state, setState] = useState<CompletionState>(INITIAL_STATE)

  const updateState = useCallback((updates: Partial<CompletionState>) => {
    setState(prev => ({ ...prev, ...updates }))
  }, [])

  const resetCompletion = useCallback(() => {
    setState(prev => ({
      ...prev,
      suggestions: [],
      selectedIndex: 0,
      isActive: false,
      context: null,
      preview: null,
      emptyDirMessage: '',
    }))
  }, [])

  const activateCompletion = useCallback(
    (suggestions: UnifiedSuggestion[], context: CompletionContext) => {
      setState(prev => ({
        ...prev,
        suggestions: suggestions,
        selectedIndex: 0,
        isActive: true,
        context,
        preview: null,
      }))
    },
    [],
  )

  const { suggestions, selectedIndex, isActive, emptyDirMessage } = state

  const getWordAtCursor = useCallback((): CompletionContext | null => {
    return __getCompletionContextForTests({
      input,
      cursorOffset,
      disableSlashCommands,
    })
  }, [input, cursorOffset, disableSlashCommands])

  const [systemCommands, setSystemCommands] = useState<string[]>([])
  const [isLoadingCommands, setIsLoadingCommands] = useState(false)

  const loadSystemCommands = useCallback(async () => {
    if (systemCommands.length > 0 || isLoadingCommands) return

    setIsLoadingCommands(true)
    try {
      const { readdirSync, statSync } = await import('fs')
      const pathDirs = (process.env.PATH || '').split(':').filter(Boolean)
      const commandSet = new Set<string>()

      const essentialCommands = getEssentialCommands()

      essentialCommands.forEach(cmd => commandSet.add(cmd))

      for (const dir of pathDirs) {
        try {
          if (readdirSync && statSync) {
            const entries = readdirSync(dir)
            for (const entry of entries) {
              try {
                const fullPath = `${dir}/${entry}`
                const stats = statSync(fullPath)
                if (stats.isFile() && (stats.mode & 0o111) !== 0) {
                  commandSet.add(entry)
                }
              } catch {
              }
            }
          }
        } catch {
        }
      }

      const commands = Array.from(commandSet).sort()
      setSystemCommands(commands)
	    } catch (error) {
	      logError(error)
	      debugLogger.warn('UNIFIED_COMPLETION_SYSTEM_COMMANDS_LOAD_FAILED', {
	        error: error instanceof Error ? error.message : String(error),
	      })
	      setSystemCommands(getMinimalFallbackCommands())
	    } finally {
	      setIsLoadingCommands(false)
	    }
  }, [systemCommands.length, isLoadingCommands])

  useEffect(() => {
    loadSystemCommands()
  }, [loadSystemCommands])

  const [agentSuggestions, setAgentSuggestions] = useState<UnifiedSuggestion[]>(
    [],
  )

  const [modelSuggestions, setModelSuggestions] = useState<UnifiedSuggestion[]>(
    [],
  )

  useEffect(() => {
    try {
      const modelManager = getModelManager()
      const allModels = modelManager.getAllAvailableModelNames()

      const suggestions = allModels.map(modelId => {
        return {
          value: `ask-${modelId}`,
          displayValue: `🦜 ask-${modelId} :: Consult ${modelId} for expert opinion and specialized analysis`,
          type: 'ask' as const,
          score: 90,
          metadata: { modelId },
        }
      })

      setModelSuggestions(suggestions)
	    } catch (error) {
	      logError(error)
	      debugLogger.warn('UNIFIED_COMPLETION_MODELS_LOAD_FAILED', {
	        error: error instanceof Error ? error.message : String(error),
	      })
	      setModelSuggestions([])
	    }
	  }, [])

  useEffect(() => {
    getActiveAgents()
      .then(agents => {
        const suggestions = agents.map(config => {
          let shortDesc = config.whenToUse

          const prefixPatterns = [
            /^Use this agent when you need (assistance with: )?/i,
            /^Use PROACTIVELY (when|to) /i,
            /^Specialized in /i,
            /^Implementation specialist for /i,
            /^Design validation specialist\.? Use PROACTIVELY to /i,
            /^Task validation specialist\.? Use PROACTIVELY to /i,
            /^Requirements validation specialist\.? Use PROACTIVELY to /i,
          ]

          for (const pattern of prefixPatterns) {
            shortDesc = shortDesc.replace(pattern, '')
          }

          const findSmartBreak = (text: string, maxLength: number) => {
            if (text.length <= maxLength) return text

            const sentenceEndings = /[.!。！]/
            const firstSentenceMatch = text.search(sentenceEndings)
            if (firstSentenceMatch !== -1) {
              const firstSentence = text.slice(0, firstSentenceMatch).trim()
              if (firstSentence.length >= 5) {
                return firstSentence
              }
            }

            if (text.length > maxLength) {
              const commaEndings = /[,，]/
              const commas = []
              let match
              const regex = new RegExp(commaEndings, 'g')
              while ((match = regex.exec(text)) !== null) {
                commas.push(match.index)
              }

              for (let i = commas.length - 1; i >= 0; i--) {
                const commaPos = commas[i]
                if (commaPos < maxLength) {
                  const clause = text.slice(0, commaPos).trim()
                  if (clause.length >= 5) {
                    return clause
                  }
                }
              }
            }

            return text.slice(0, maxLength) + '...'
          }

          shortDesc = findSmartBreak(shortDesc.trim(), 80)

          if (!shortDesc || shortDesc.length < 5) {
            shortDesc = findSmartBreak(config.whenToUse, 80)
          }

          return {
            value: `run-agent-${config.agentType}`,
            displayValue: `👤 run-agent-${config.agentType} :: ${shortDesc}`,
            type: 'agent' as const,
            score: 85,
            metadata: config,
          }
        })
        setAgentSuggestions(suggestions)
      })
	      .catch(error => {
	        logError(error)
	        debugLogger.warn('UNIFIED_COMPLETION_AGENTS_LOAD_FAILED', {
	          error: error instanceof Error ? error.message : String(error),
	        })
	        setAgentSuggestions([])
	      })
	  }, [])

  const generateSuggestions = useCallback(
    (context: CompletionContext): UnifiedSuggestion[] =>
      generateSuggestionsForContext({
        context,
        commands,
        agentSuggestions,
        modelSuggestions,
        systemCommands,
        isLoadingCommands,
        cwd: getCwd(),
      }),
    [
      commands,
      agentSuggestions,
      modelSuggestions,
      systemCommands,
      isLoadingCommands,
    ],
  )

  const completeWith = useCallback(
    (suggestion: UnifiedSuggestion, context: CompletionContext) => {
      let completion: string

      if (context.type === 'command') {
        completion = `/${suggestion.value} `
      } else if (context.type === 'agent') {
        if (suggestion.type === 'agent') {
          completion = `@${suggestion.value} `
        } else if (suggestion.type === 'ask') {
          completion = `@${suggestion.value} `
        } else {
          const isDirectory = suggestion.value.endsWith('/')
          completion = `@${suggestion.value}${isDirectory ? '' : ' '}`
        }
      } else {
        if (suggestion.isSmartMatch) {
          completion = `@${suggestion.value} `
        } else {
          const isDirectory = suggestion.value.endsWith('/')
          completion = suggestion.value + (isDirectory ? '' : ' ')
        }
      }

      let actualEndPos: number

      if (
        context.type === 'file' &&
        suggestion.value.startsWith('/') &&
        !suggestion.isSmartMatch
      ) {
        let end = context.startPos
        while (
          end < input.length &&
          input[end] !== ' ' &&
          input[end] !== '\n'
        ) {
          end++
        }
        actualEndPos = end
      } else {
        const currentWord = input.slice(context.startPos)
        const nextSpaceIndex = currentWord.indexOf(' ')
        actualEndPos =
          nextSpaceIndex === -1
            ? input.length
            : context.startPos + nextSpaceIndex
      }

      const newInput =
        input.slice(0, context.startPos) +
        completion +
        input.slice(actualEndPos)
      onInputChange(newInput)
      setCursorOffset(context.startPos + completion.length)


    },
    [input, onInputChange, setCursorOffset, onSubmit, commands],
  )

  const partialComplete = useCallback(
    (prefix: string, context: CompletionContext) => {
      const completion =
        context.type === 'command'
          ? `/${prefix}`
          : context.type === 'agent'
            ? `@${prefix}`
            : prefix

      const newInput =
        input.slice(0, context.startPos) +
        completion +
        input.slice(context.endPos)
      onInputChange(newInput)
      setCursorOffset(context.startPos + completion.length)
    },
    [input, onInputChange, setCursorOffset],
  )

  useInput((input_str, key) => {
    if (!__shouldHandleUnifiedCompletionTabKeyForTests(key)) return false

    const context = getWordAtCursor()
    if (!context) return false

    if (state.isActive && state.suggestions.length > 0) {
      const nextIndex = (state.selectedIndex + 1) % state.suggestions.length
      const nextSuggestion = state.suggestions[nextIndex]

      if (state.context) {
        const currentWord = input.slice(state.context.startPos)
        const wordEnd = currentWord.search(/\s/)
        const actualEndPos =
          wordEnd === -1 ? input.length : state.context.startPos + wordEnd

        let preview: string
        if (state.context.type === 'command') {
          preview = `/${nextSuggestion.value}`
        } else if (state.context.type === 'agent') {
          preview = `@${nextSuggestion.value}`
        } else if (nextSuggestion.isSmartMatch) {
          preview = `@${nextSuggestion.value}`
        } else {
          preview = nextSuggestion.value
        }

        const newInput =
          input.slice(0, state.context.startPos) +
          preview +
          input.slice(actualEndPos)

        onInputChange(newInput)
        setCursorOffset(state.context.startPos + preview.length)

        updateState({
          selectedIndex: nextIndex,
          preview: {
            isActive: true,
            originalInput: input,
            wordRange: [
              state.context.startPos,
              state.context.startPos + preview.length,
            ],
          },
        })
      }
      return true
    }

    const currentSuggestions = generateSuggestions(context)

    if (currentSuggestions.length === 0) {
      return false
    } else if (currentSuggestions.length === 1) {
      completeWith(currentSuggestions[0], context)
      return true
    } else {
      activateCompletion(currentSuggestions, context)

      const firstSuggestion = currentSuggestions[0]
      const currentWord = input.slice(context.startPos)
      const wordEnd = currentWord.search(/\s/)
      const actualEndPos =
        wordEnd === -1 ? input.length : context.startPos + wordEnd

      let preview: string
      if (context.type === 'command') {
        preview = `/${firstSuggestion.value}`
      } else if (context.type === 'agent') {
        preview = `@${firstSuggestion.value}`
      } else if (firstSuggestion.isSmartMatch) {
        preview = `@${firstSuggestion.value}`
      } else {
        preview = firstSuggestion.value
      }

      const newInput =
        input.slice(0, context.startPos) + preview + input.slice(actualEndPos)

      onInputChange(newInput)
      setCursorOffset(context.startPos + preview.length)

      updateState({
        preview: {
          isActive: true,
          originalInput: input,
          wordRange: [context.startPos, context.startPos + preview.length],
        },
      })

      return true
    }
  })

  useInput((inputChar, key) => {
    if (
      key.return &&
      !key.shift &&
      !key.meta &&
      state.isActive &&
      state.suggestions.length > 0
    ) {
      const selectedSuggestion = state.suggestions[state.selectedIndex]
      if (selectedSuggestion && state.context) {
        let completion: string

        if (state.context.type === 'command') {
          completion = `/${selectedSuggestion.value} `
        } else if (state.context.type === 'agent') {
          if (selectedSuggestion.type === 'agent') {
            completion = `@${selectedSuggestion.value} `
          } else if (selectedSuggestion.type === 'ask') {
            completion = `@${selectedSuggestion.value} `
          } else {
            completion = `@${selectedSuggestion.value} `
          }
        } else if (selectedSuggestion.isSmartMatch) {
          completion = `@${selectedSuggestion.value} `
        } else {
          completion = selectedSuggestion.value + ' '
        }

        const currentWord = input.slice(state.context.startPos)
        const nextSpaceIndex = currentWord.indexOf(' ')
        const actualEndPos =
          nextSpaceIndex === -1
            ? input.length
            : state.context.startPos + nextSpaceIndex

        const newInput =
          input.slice(0, state.context.startPos) +
          completion +
          input.slice(actualEndPos)
        onInputChange(newInput)
        setCursorOffset(state.context.startPos + completion.length)
      }
      resetCompletion()
      return true
    }

    if (!state.isActive || state.suggestions.length === 0) return false

    const handleNavigation = (newIndex: number) => {
      const preview = state.suggestions[newIndex].value

      if (state.preview?.isActive && state.context) {
        const newInput =
          input.slice(0, state.context.startPos) +
          preview +
          input.slice(state.preview.wordRange[1])

        onInputChange(newInput)
        setCursorOffset(state.context.startPos + preview.length)

        updateState({
          selectedIndex: newIndex,
          preview: {
            ...state.preview,
            wordRange: [
              state.context.startPos,
              state.context.startPos + preview.length,
            ],
          },
        })
      } else {
        updateState({ selectedIndex: newIndex })
      }
    }

    if (key.downArrow) {
      const nextIndex = (state.selectedIndex + 1) % state.suggestions.length
      handleNavigation(nextIndex)
      return true
    }

    if (key.upArrow) {
      const nextIndex =
        state.selectedIndex === 0
          ? state.suggestions.length - 1
          : state.selectedIndex - 1
      handleNavigation(nextIndex)
      return true
    }

    if (inputChar === ' ') {
      resetCompletion()
      return false
    }

    if (key.rightArrow) {
      const selectedSuggestion = state.suggestions[state.selectedIndex]
      const isDirectory = selectedSuggestion.value.endsWith('/')

      if (!state.context) return false

      const currentWordAtContext = input.slice(
        state.context.startPos,
        state.context.startPos + selectedSuggestion.value.length,
      )

      if (currentWordAtContext !== selectedSuggestion.value) {
        completeWith(selectedSuggestion, state.context)
      }

      resetCompletion()

      if (isDirectory) {
        setTimeout(() => {
          const newContext = {
            ...state.context,
            prefix: selectedSuggestion.value,
            endPos: state.context.startPos + selectedSuggestion.value.length,
          }

          const newSuggestions = generateSuggestions(newContext)

          if (newSuggestions.length > 0) {
            activateCompletion(newSuggestions, newContext)
          } else {
            updateState({
              emptyDirMessage: `Directory is empty: ${selectedSuggestion.value}`,
            })
            setTimeout(() => updateState({ emptyDirMessage: '' }), 3000)
          }
        }, 50)
      }

      return true
    }

    if (key.escape) {
      if (state.preview?.isActive && state.context) {
        onInputChange(state.preview.originalInput)
        setCursorOffset(state.context.startPos + state.context.prefix.length)
      }

      resetCompletion()
      return true
    }

    return false
  })

  useInput((input_str, key) => {
    if (key.backspace || key.delete) {
      if (state.isActive) {
        resetCompletion()
        const suppressionTime = input.length > 10 ? 200 : 100
        updateState({
          suppressUntil: Date.now() + suppressionTime,
        })
        return true
      }
    }
    return false
  })

  const lastInputRef = useRef('')

  useEffect(() => {
    if (lastInputRef.current === input) return

    const inputLengthChange = Math.abs(
      input.length - lastInputRef.current.length,
    )
    const isHistoryNavigation =
      (inputLengthChange > 10 ||
        (inputLengthChange > 5 &&
          !input.includes(lastInputRef.current.slice(-5)))) &&
      input !== lastInputRef.current

    lastInputRef.current = input

    if (state.preview?.isActive || Date.now() < state.suppressUntil) {
      return
    }

    if (isHistoryNavigation && state.isActive) {
      resetCompletion()
      return
    }

    const context = getWordAtCursor()

    if (context && shouldAutoTrigger(context)) {
      const newSuggestions = generateSuggestions(context)

      if (newSuggestions.length === 0) {
        resetCompletion()
      } else if (
        newSuggestions.length === 1 &&
        shouldAutoHideSingleMatch(newSuggestions[0], context)
      ) {
        resetCompletion()
      } else {
        activateCompletion(newSuggestions, context)
      }
    } else if (state.context) {
      const contextChanged =
        !context ||
        state.context.type !== context.type ||
        state.context.startPos !== context.startPos ||
        !context.prefix.startsWith(state.context.prefix)

      if (contextChanged) {
        resetCompletion()
      }
    }
  }, [input, cursorOffset])

  const shouldAutoTrigger = useCallback(
    (context: CompletionContext): boolean => {
      switch (context.type) {
        case 'command':
          return true
        case 'agent':
          return true
        case 'file':
          const prefix = context.prefix

          if (
            prefix.startsWith('./') ||
            prefix.startsWith('../') ||
            prefix.startsWith('/') ||
            prefix.startsWith('~') ||
            prefix.includes('/')
          ) {
            return true
          }

          if (prefix.startsWith('.') && prefix.length >= 2) {
            return true
          }

          return false
        default:
          return false
      }
    },
    [],
  )

  const shouldAutoHideSingleMatch = useCallback(
    (suggestion: UnifiedSuggestion, context: CompletionContext): boolean => {
      const currentInput = input.slice(context.startPos, context.endPos)

      if (context.type === 'file') {
        if (suggestion.value.endsWith('/')) {
          return false
        }

        if (currentInput === suggestion.value) {
          return true
        }

        if (
          currentInput.endsWith('/' + suggestion.value) ||
          currentInput.endsWith(suggestion.value)
        ) {
          return true
        }

        return false
      }

      if (context.type === 'command') {
        const fullCommand = `/${suggestion.value}`
        const matches = currentInput === fullCommand
        return matches
      }

      if (context.type === 'agent') {
        const fullAgent = `@${suggestion.value}`
        const matches = currentInput === fullAgent
        return matches
      }

      return false
    },
    [input],
  )

  return {
    suggestions,
    selectedIndex,
    isActive,
    emptyDirMessage,
  }
}

export function __shouldHandleUnifiedCompletionTabKeyForTests(
  key: Key,
): boolean {
  return Boolean(key.tab) && !Boolean(key.shift)
}
