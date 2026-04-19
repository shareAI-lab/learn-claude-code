import { Box, Text } from 'ink'
import React, { type ReactNode } from 'react'
import { SelectOption } from './select-option'
import { type Theme } from './theme'
import { useSelectState } from './use-select-state'
import { useSelect } from './use-select'
import { Option } from '@inkjs/ui'
import { getTheme } from '@utils/theme'

export type OptionSubtree = {
  readonly header?: string

  readonly options: (Option | OptionSubtree)[]
}

export type OptionHeader = {
  readonly header: string

  readonly optionValues: string[]
}

export const optionHeaderKey = (optionHeader: OptionHeader): string =>
  `HEADER-${optionHeader.optionValues.join(',')}`

export type SelectProps = {
  readonly isDisabled?: boolean

  readonly visibleOptionCount?: number

  readonly highlightText?: string

  readonly options: (Option | OptionSubtree)[]

  readonly defaultValue?: string

  readonly onChange?: (value: string) => void

  readonly onFocus?: (value: string) => void

  readonly focusValue?: string
}

export function Select({
  isDisabled = false,
  visibleOptionCount = 5,
  highlightText,
  options,
  defaultValue,
  onChange,
  onFocus,
  focusValue,
}: SelectProps) {
  const state = useSelectState({
    visibleOptionCount,
    options,
    defaultValue,
    onChange,
    onFocus,
    focusValue,
  })

  useSelect({ isDisabled, state })

  const appTheme = getTheme()
  const styles = {
    container: () => ({
      flexDirection: 'column' as const,
    }),
    highlightedText: () => ({
      color: appTheme.text,
      backgroundColor: appTheme.warning,
    }),
  }

  return (
    <Box {...styles.container()}>
      {state.visibleOptions.map(option => {
        const key = 'value' in option ? option.value : optionHeaderKey(option)
        const isFocused =
          !isDisabled &&
          state.focusedValue !== undefined &&
          ('value' in option
            ? state.focusedValue === option.value
            : option.optionValues.includes(state.focusedValue))
        const isSelected =
          !!state.value &&
          ('value' in option
            ? state.value === option.value
            : option.optionValues.includes(state.value))
        const smallPointer = 'header' in option
        const labelText = 'label' in option ? option.label : option.header
        let label: ReactNode = labelText

        if (highlightText && labelText.includes(highlightText)) {
          const index = labelText.indexOf(highlightText)

          label = (
            <>
              {labelText.slice(0, index)}
              <Text {...styles.highlightedText()}>{highlightText}</Text>
              {labelText.slice(index + highlightText.length)}
            </>
          )
        }

        return (
          <SelectOption
            key={key}
            isFocused={isFocused}
            isSelected={isSelected}
            smallPointer={smallPointer}
            children={label}
          />
        )
      })}
    </Box>
  )
}
