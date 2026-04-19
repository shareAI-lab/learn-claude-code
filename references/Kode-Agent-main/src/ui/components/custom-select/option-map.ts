import { type Option } from '@inkjs/ui'
import { optionHeaderKey, type OptionHeader } from './select'

type OptionMapItem = (Option | OptionHeader) & {
  previous: OptionMapItem | undefined
  next: OptionMapItem | undefined
  index: number
}

export default class OptionMap extends Map<string, OptionMapItem> {
  readonly first: OptionMapItem | undefined

  constructor(options: (Option | OptionHeader)[]) {
    const items: Array<[string, OptionMapItem]> = []
    let firstItem: OptionMapItem | undefined
    let previous: OptionMapItem | undefined
    let index = 0

    for (const option of options) {
      const item = {
        ...option,
        previous,
        next: undefined,
        index,
      }

      if (previous) {
        previous.next = item
      }

      firstItem ||= item

      const key = 'value' in option ? option.value : optionHeaderKey(option)
      items.push([key, item])
      index++
      previous = item
    }

    super(items)
    this.first = firstItem
  }
}
