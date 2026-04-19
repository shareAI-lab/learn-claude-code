import { describe, expect, test } from 'bun:test'
import { runBashLlmSafetyGate } from '@tools/BashTool/llmSafetyGate'

const PRODUCTION_TEST_MODE = process.env.PRODUCTION_TEST_MODE === 'true'
const ENABLE_REAL_TEST = process.env.KODE_BASH_GATE_REAL_TEST === 'true'

describe('Bash LLM intent gate (real request)', () => {
  if (!PRODUCTION_TEST_MODE || !ENABLE_REAL_TEST) {
    test('⚠️  REAL TEST DISABLED', () => {
      expect(true).toBe(true)
    })
    return
  }

  test(
    'returns a parseable verdict for a benign command',
    async () => {
      const result = await runBashLlmSafetyGate({
        command: 'echo "hello"',
        userPrompt: 'Print a greeting to stdout',
        description: 'Print greeting',
        platform: process.platform,
        commandSource: 'agent_call',
        safeMode: false,
        runInBackground: false,
        willSandbox: true,
        sandboxRequired: false,
        cwd: process.cwd(),
        originalCwd: process.cwd(),
	      })

	      expect(['allow', 'block']).toContain(result.decision)
	      expect(result.decision).not.toBe('error')
	    },
    { timeout: 90_000 },
  )
})
