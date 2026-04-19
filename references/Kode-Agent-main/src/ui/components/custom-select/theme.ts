
import type { BoxProps, TextProps } from 'ink'

export interface Theme {
  styles: {
    container(): BoxProps

    option(props: { isFocused: boolean }): BoxProps

    focusIndicator(): TextProps

    label(props: { isFocused: boolean; isSelected: boolean }): TextProps

    selectedIndicator(): TextProps

    highlightedText(): TextProps
  }
}
