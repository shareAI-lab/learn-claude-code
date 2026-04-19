import { afterEach, describe, expect, test } from 'bun:test'
import React, { useState } from 'react'
import { PassThrough } from 'stream'
import stripAnsi from 'strip-ansi'
import { Box, Text, render } from 'ink'
import { buildModelOptions } from '@components/model-selector/filterModels'
import { ModelSelectionScreen } from '@components/model-selector/ModelSelectionScreen'
import { getTheme } from '@utils/theme'

type InkTestHarness = {
  stdin: PassThrough & {
    isTTY?: boolean
    setRawMode?: (enabled: boolean) => void
    isRaw?: boolean
  }
  unmount: () => void
  clearOutput: () => void
  getOutput: () => string
  wait: (ms: number) => Promise<void>
}

function createInkTestHarness(element: React.ReactElement): InkTestHarness {
  const stdin = new PassThrough()
  ;(stdin as any).isTTY = true
  ;(stdin as any).isRaw = true
  ;(stdin as any).setRawMode = () => {}
  ;(stdin as any).ref = () => {}
  ;(stdin as any).unref = () => {}
  stdin.setEncoding('utf8')
  stdin.resume()

  const stdout = new PassThrough()
  ;(stdout as any).isTTY = true
  ;(stdout as any).columns = 100
  ;(stdout as any).rows = 30

  let rawOutput = ''
  stdout.on('data', chunk => {
    rawOutput += chunk.toString('utf8')
  })

  const instance = render(element, {
    stdin: stdin as any,
    stdout: stdout as any,
    exitOnCtrlC: false,
  })

  return {
    stdin,
    unmount: () => instance.unmount(),
    clearOutput: () => {
      rawOutput = ''
    },
    getOutput: () => stripAnsi(rawOutput),
    wait: async ms => new Promise(resolve => setTimeout(resolve, ms)),
  }
}

const mounted: InkTestHarness[] = []

afterEach(() => {
  while (mounted.length > 0) {
    try {
      mounted.pop()!.unmount()
    } catch {}
  }
})

describe('ModelSelector modularization', () => {
  test('buildModelOptions filters models by search query', () => {
    const options = buildModelOptions(
      [
        { model: 'gpt-5', provider: 'openai' },
        { model: 'foo', provider: 'custom' },
      ] as any,
      'gpt',
    )
    expect(options.map(o => o.value)).toEqual(['gpt-5'])
  })

  test('ModelSelectionScreen filters and calls onModelSelect', async () => {
    const theme = getTheme()
    const models = [
      { model: 'gpt-5', provider: 'openai' },
      { model: 'foo', provider: 'custom' },
    ] as any

    function Harness(): React.ReactNode {
      const [selected, setSelected] = useState('')
      const [query, setQuery] = useState('')
      const [cursorOffset, setCursorOffset] = useState(0)

      return (
        <Box flexDirection="column">
          <Text>SELECTED:{selected}</Text>
          <ModelSelectionScreen
            theme={theme}
            exitState={{ pending: false, keyName: 'Ctrl-C' }}
            providerLabel="Test Provider"
            modelTypeText="this model profile"
            availableModels={models}
            modelSearchQuery={query}
            onModelSearchChange={setQuery}
            modelSearchCursorOffset={cursorOffset}
            onModelSearchCursorOffsetChange={setCursorOffset}
            onModelSelect={setSelected}
          />
        </Box>
      )
    }

    const h = createInkTestHarness(<Harness />)
    mounted.push(h)

    await h.wait(25)
    expect(h.getOutput()).toContain('Showing 2 of 2 models')

    h.clearOutput()
    h.stdin.write('foo')
    await h.wait(50)
    expect(h.getOutput()).toContain('Showing 1 of 2 models')

    h.clearOutput()
    h.stdin.write('\r')
    await h.wait(50)
    expect(h.getOutput()).toContain('SELECTED:foo')
  })
})

