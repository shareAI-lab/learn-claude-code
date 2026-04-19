const RUNS_DEFAULT = 5
const TIMEOUT_MS_DEFAULT = 30_000

function getArgValue(name) {
  const idx = process.argv.indexOf(name)
  if (idx === -1) return null
  const next = process.argv[idx + 1]
  if (!next || next.startsWith('-')) return null
  return next
}

function getNumberArg(name, fallback) {
  const raw = getArgValue(name)
  if (!raw) return fallback
  const n = Number(raw)
  return Number.isFinite(n) && n > 0 ? n : fallback
}

function parseStartupLine(line) {
  const m = line.match(/^\[startup\]\s+(first_render|prompt_ready)=(\d+)ms\s*$/)
  if (!m) return null
  return { event: m[1], ms: Number(m[2]) }
}

async function runOnce({ timeoutMs }) {
  const cmd = [
    process.execPath,
    'run',
    './src/entrypoints/cli.tsx',
    '--verbose',
  ]

  const child = Bun.spawn(cmd, {
    env: {
      ...process.env,
      // Make benchmarks non-interactive/stable by skipping onboarding/trust dialogs.
      NODE_ENV: 'test',
      KODE_STARTUP_PROFILE: '1',
    },
    stdin: 'ignore',
    stdout: 'ignore',
    stderr: 'pipe',
  })

  const decoder = new TextDecoder()
  let buf = ''
  let firstRenderMs = null
  let promptReadyMs = null

  const timeout = setTimeout(() => {
    try {
      child.kill()
    } catch {}
  }, timeoutMs)

  try {
    for await (const chunk of child.stderr) {
      buf += decoder.decode(chunk)
      const lines = buf.split(/\r?\n/)
      buf = lines.pop() ?? ''
      for (const line of lines) {
        const parsed = parseStartupLine(line.trim())
        if (!parsed) continue
        if (parsed.event === 'first_render') firstRenderMs = parsed.ms
        if (parsed.event === 'prompt_ready') promptReadyMs = parsed.ms
        if (promptReadyMs != null) {
          try {
            child.kill()
          } catch {}
          break
        }
      }
      if (promptReadyMs != null) break
    }
  } finally {
    clearTimeout(timeout)
  }

  const exitCode = await child.exited
  return { firstRenderMs, promptReadyMs, exitCode }
}

function mean(values) {
  const xs = values.filter(v => Number.isFinite(v))
  if (xs.length === 0) return null
  return Math.round(xs.reduce((a, b) => a + b, 0) / xs.length)
}

const runs = getNumberArg('--runs', RUNS_DEFAULT)
const timeoutMs = getNumberArg('--timeout-ms', TIMEOUT_MS_DEFAULT)

const results = []
for (let i = 0; i < runs; i++) {
  const r = await runOnce({ timeoutMs })
  results.push(r)
  const fr = r.firstRenderMs ?? 'NA'
  const pr = r.promptReadyMs ?? 'NA'
  process.stdout.write(
    `run ${i + 1}/${runs}: first_render=${fr}ms prompt_ready=${pr}ms exit=${r.exitCode}\n`,
  )
}

process.stdout.write('\n')
process.stdout.write(`avg first_render: ${mean(results.map(r => r.firstRenderMs)) ?? 'NA'}ms\n`)
process.stdout.write(`avg prompt_ready: ${mean(results.map(r => r.promptReadyMs)) ?? 'NA'}ms\n`)

