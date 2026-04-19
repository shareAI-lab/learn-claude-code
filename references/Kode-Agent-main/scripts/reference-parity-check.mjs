#!/usr/bin/env bun
import { spawnSync } from 'node:child_process'
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join, resolve } from 'node:path'

function usage() {
  console.log(
    [
      'Usage:',
      '  bun run scripts/reference-parity-check.mjs --reference <path>',
      '',
      'Env:',
      '  KODE_REFERENCE_REPO=<path>    Reference repo root (alternative to --reference)',
      '',
      'Notes:',
      '- Runs offline parity checks (stdout/stderr/exit codes) against a reference repo.',
      '- Forces wrappers to skip any cached native binaries by setting KODE_BIN_DIR to a temp dir.',
    ].join('\n'),
  )
}

function normalizeNewlines(text) {
  return String(text ?? '').replace(/\r\n/g, '\n')
}

function normalizeOutput(text, { newRoot, referenceRoot }) {
  let out = normalizeNewlines(text)
  if (newRoot) out = out.split(newRoot).join('<REPO>')
  if (referenceRoot) out = out.split(referenceRoot).join('<REPO>')
  // Ignore repo-internal absolute paths and their line-wrapping differences.
  out = out.replace(/<REPO>[\\/][^\s)]+/g, '<REPO>/<path>')
  return out
}

function firstDiffSnippet(a, b, context = 80) {
  if (a === b) return null
  const max = Math.max(a.length, b.length)
  let i = 0
  while (i < max && a[i] === b[i]) i++
  const start = Math.max(0, i - context)
  const end = i + context
  return {
    index: i,
    a: a.slice(start, end),
    b: b.slice(start, end),
  }
}

function stripAnsi(input) {
  return String(input ?? '').replace(/\x1b\[[0-9;]*m/g, '')
}

function parseTopLevelCommandsFromHelp(helpText) {
  const lines = normalizeNewlines(helpText).split('\n').map(stripAnsi)
  const commandsHeaderIndex = lines.findIndex(
    l => stripAnsi(l).trim() === 'Commands:',
  )
  if (commandsHeaderIndex === -1) return []

  const commands = []
  for (let i = commandsHeaderIndex + 1; i < lines.length; i++) {
    const line = lines[i]
    if (!line || !line.trim()) continue
    if (!/^[\\s]/.test(line)) break
    const m = line.match(/^\\s+([a-z0-9][a-z0-9-]*)\\b/)
    if (m) commands.push(m[1])
  }
  return commands
}

const FALLBACK_TOP_LEVEL_COMMANDS = [
  'config',
  'models',
  'agents',
  'plugin',
  'skills',
  'approved-tools',
  'mcp',
  'doctor',
  'update',
  'log',
  'resume',
  'error',
  'context',
]

function run(cmd, options) {
  const [file, ...args] = cmd
  const proc = spawnSync(file, args, {
    cwd: options.cwd,
    env: options.env,
    encoding: 'utf8',
    input: '',
    timeout: options.timeoutMs ?? 60_000,
    maxBuffer: 32 * 1024 * 1024,
  })

  return {
    exitCode: typeof proc.status === 'number' ? proc.status : 1,
    stdout: proc.stdout ?? '',
    stderr: proc.stderr ?? '',
  }
}

function resolveCliArg(args, name) {
  const idx = args.indexOf(name)
  if (idx === -1) return null
  const value = args[idx + 1]
  if (!value || value.startsWith('-')) return null
  return value
}

function buildTempEnv(tempRoot) {
  return {
    KODE_CONFIG_DIR: join(tempRoot, 'config'),
    CLAUDE_CONFIG_DIR: join(tempRoot, 'config'),
    ANYKODE_CONFIG_DIR: join(tempRoot, 'config'),
    // Force Node wrappers to skip any cached native binary and always use local dist/
    KODE_BIN_DIR: join(tempRoot, 'bin'),
    ANYKODE_BIN_DIR: join(tempRoot, 'bin'),
  }
}

async function main() {
  const argv = process.argv.slice(2)
  if (argv.includes('--help') || argv.includes('-h')) {
    usage()
    process.exit(0)
  }

  const referenceArg = resolveCliArg(argv, '--reference')
  const referenceInput = referenceArg || process.env.KODE_REFERENCE_REPO
  if (!referenceInput) {
    usage()
    console.error('')
    console.error('Error: --reference (or KODE_REFERENCE_REPO) is required.')
    process.exit(1)
  }

  const referenceRoot = resolve(referenceInput)
  const newRoot = resolve(process.cwd())

  if (!referenceRoot || referenceRoot === newRoot) {
    console.error('Error: --reference (or KODE_REFERENCE_REPO) must point to a different repo root.')
    process.exit(1)
  }

  const node = Bun.which('node')
  if (!node) {
    console.error('Error: node not found in PATH (required to run the npm bin shims).')
    process.exit(1)
  }

  const tmp = mkdtempSync(join(tmpdir(), 'kode-reference-parity-'))
  const envBase = { ...process.env, ...buildTempEnv(tmp) }
  const projectCwd = join(tmp, 'project')
  try {
    // Ensure the working directory exists for cases that rely on process.cwd().
    mkdirSync(projectCwd, { recursive: true })
  } catch {}

  // Seed a minimal global config so parity checks don't trigger interactive onboarding
  // (which fails in non-TTY contexts and makes output dependent on stack trace paths).
  try {
    const configDir = join(tmp, 'config')
    mkdirSync(configDir, { recursive: true })
    writeFileSync(
      join(configDir, 'config.json'),
      JSON.stringify(
        {
          theme: 'dark',
          hasCompletedOnboarding: true,
          preferredNotifChannel: 'iterm2',
          verbose: false,
          numStartups: 0,
        },
        null,
        2,
      ),
    )
  } catch {}

  const cases = [
    { label: 'cli --help-lite', args: ['cli.js', '--help-lite'] },
    { label: 'cli --help', args: ['cli.js', '--help'] },
    { label: 'cli --version', args: ['cli.js', '--version'] },
    { label: 'cli --print (missing input)', args: ['cli.js', '--print'] },
    {
      label: 'cli --print stream-json verbose gate',
      args: [
        'cli.js',
        '--print',
        '--input-format',
        'stream-json',
        '--output-format',
        'stream-json',
      ],
    },
    { label: 'cli unknown flag', args: ['cli.js', '--this-flag-should-not-exist'] },
    {
      label: 'cli --cwd bad path (help-lite)',
      args: ['cli.js', '--cwd', join(tmp, 'definitely-does-not-exist'), '--help-lite'],
    },
    { label: 'acp --help', args: ['cli-acp.js', '--help'] },
    { label: 'acp --version', args: ['cli-acp.js', '--version'] },
  ]

  const mismatches = []
  console.log(`Reference repo: ${referenceRoot}`)
  console.log(`Current repo:   ${newRoot}`)
  console.log('')

  for (const testCase of cases) {
    const ref = run([node, join(referenceRoot, testCase.args[0]), ...testCase.args.slice(1)], {
      cwd: projectCwd,
      env: envBase,
    })
    const cur = run([node, join(newRoot, testCase.args[0]), ...testCase.args.slice(1)], {
      cwd: projectCwd,
      env: envBase,
    })

    const refStdout = normalizeOutput(ref.stdout, { newRoot, referenceRoot })
    const refStderr = normalizeOutput(ref.stderr, { newRoot, referenceRoot })
    const curStdout = normalizeOutput(cur.stdout, { newRoot, referenceRoot })
    const curStderr = normalizeOutput(cur.stderr, { newRoot, referenceRoot })

    const ok =
      ref.exitCode === cur.exitCode &&
      refStdout === curStdout &&
      refStderr === curStderr

    if (ok) {
      console.log(`✅ ${testCase.label}`)
      continue
    }

    console.log(`❌ ${testCase.label}`)
    mismatches.push({
      label: testCase.label,
      ref: { ...ref, stdout: refStdout, stderr: refStderr },
      cur: { ...cur, stdout: curStdout, stderr: curStderr },
    })
  }

  console.log('')
  console.log('Help matrix parity...')

  const refRootHelp = run([node, join(referenceRoot, 'cli.js'), '--help'], {
    cwd: projectCwd,
    env: envBase,
    timeoutMs: 60_000,
  })
  const curRootHelp = run([node, join(newRoot, 'cli.js'), '--help'], {
    cwd: projectCwd,
    env: envBase,
    timeoutMs: 60_000,
  })

  if (refRootHelp.exitCode !== 0 || curRootHelp.exitCode !== 0) {
    mismatches.push({
      label: 'help matrix: root --help (non-zero exit)',
      ref: refRootHelp,
      cur: curRootHelp,
    })
  } else {
    const refCommands = parseTopLevelCommandsFromHelp(refRootHelp.stdout)
    const curCommands = parseTopLevelCommandsFromHelp(curRootHelp.stdout)
    const sameList =
      refCommands.length === curCommands.length &&
      refCommands.every((c, i) => c === curCommands[i])

    const commandsToCheck =
      sameList && refCommands.length > 0 ? refCommands : FALLBACK_TOP_LEVEL_COMMANDS

    if (!sameList && refCommands.length > 0 && curCommands.length > 0) {
      mismatches.push({
        label: 'help matrix: command list mismatch',
        ref: { ...refRootHelp, stdout: normalizeNewlines(refRootHelp.stdout) },
        cur: { ...curRootHelp, stdout: normalizeNewlines(curRootHelp.stdout) },
      })
    }

    console.log(
      `✅ help matrix: ${commandsToCheck.length} top-level command(s)`,
    )
    for (const cmdName of commandsToCheck) {
        const label = `help matrix: ${cmdName} --help`
        const ref = run(
          [node, join(referenceRoot, 'cli.js'), cmdName, '--help'],
          { cwd: projectCwd, env: envBase, timeoutMs: 60_000 },
        )
        const cur = run([node, join(newRoot, 'cli.js'), cmdName, '--help'], {
          cwd: projectCwd,
          env: envBase,
          timeoutMs: 60_000,
        })

        const refStdout = normalizeOutput(ref.stdout, { newRoot, referenceRoot })
        const refStderr = normalizeOutput(ref.stderr, { newRoot, referenceRoot })
        const curStdout = normalizeOutput(cur.stdout, { newRoot, referenceRoot })
        const curStderr = normalizeOutput(cur.stderr, { newRoot, referenceRoot })

        const ok =
          ref.exitCode === cur.exitCode &&
          refStdout === curStdout &&
          refStderr === curStderr

        if (ok) {
          continue
        }

        console.log(`❌ ${label}`)
        mismatches.push({
          label,
          ref: { ...ref, stdout: refStdout, stderr: refStderr },
          cur: { ...cur, stdout: curStdout, stderr: curStderr },
        })
      }
  }

  console.log('')
  console.log('Tool manifest parity...')

  const toolSnippet = [
    "import { createHash } from 'node:crypto'",
    "import { zodToJsonSchema } from 'zod-to-json-schema'",
    "import { getAllTools } from './src/tools'",
    '',
    "let getToolDescription = null",
    "for (const candidate of ['./src/Tool', './src/core/tools/tool']) {",
    '  try {',
    '    const mod = await import(candidate)',
    "    if (typeof mod.getToolDescription === 'function') {",
    '      getToolDescription = mod.getToolDescription',
    '      break',
    '    }',
    '  } catch {}',
    '}',
    "if (!getToolDescription) throw new Error('getToolDescription not found')",
    '',
    'function sha256(text) {',
    "  return createHash('sha256').update(text).digest('hex')",
    '}',
    '',
    'function sortKeys(value) {',
    '  if (Array.isArray(value)) return value.map(sortKeys)',
    "  if (value && typeof value === 'object') {",
    '    const keys = Object.keys(value).sort()',
    '    const out = {}',
    '    for (const k of keys) out[k] = sortKeys(value[k])',
    '    return out',
    '  }',
    '  return value',
    '}',
    '',
    'const tools = getAllTools()',
    'const manifest = []',
    'for (const tool of tools) {',
    '  const schema = tool.inputJSONSchema ?? zodToJsonSchema(tool.inputSchema, { name: tool.name })',
    '  const stable = sortKeys(schema)',
    '  const stableJson = JSON.stringify(stable)',
    '  manifest.push({',
    '    name: tool.name,',
    '    description: getToolDescription(tool),',
    '    schemaSha256: sha256(stableJson),',
    '    schema: stable,',
    '  })',
    '}',
    '',
    'console.log(JSON.stringify(manifest, null, 2))',
    'process.exit(0)',
  ].join('\n')

  const refTools = run([process.execPath, '-e', toolSnippet, '--cwd', referenceRoot], {
    cwd: referenceRoot,
    env: envBase,
  })
  const curTools = run([process.execPath, '-e', toolSnippet, '--cwd', newRoot], {
    cwd: newRoot,
    env: envBase,
  })

  const refToolsOut = normalizeOutput(refTools.stdout, { newRoot, referenceRoot })
  const curToolsOut = normalizeOutput(curTools.stdout, { newRoot, referenceRoot })

  const toolOk =
    refTools.exitCode === 0 &&
    curTools.exitCode === 0 &&
    refToolsOut === curToolsOut

  if (toolOk) {
    console.log('✅ tools manifest matches')
  } else {
    console.log('❌ tools manifest mismatch')
    const snippet = firstDiffSnippet(refToolsOut, curToolsOut)
    mismatches.push({
      label: 'tools manifest',
      ref: { ...refTools, stdout: refToolsOut, stderr: normalizeOutput(refTools.stderr, { newRoot, referenceRoot }) },
      cur: { ...curTools, stdout: curToolsOut, stderr: normalizeOutput(curTools.stderr, { newRoot, referenceRoot }) },
      snippet,
    })
  }

  rmSync(tmp, { recursive: true, force: true })

  if (mismatches.length === 0) {
    console.log('')
    console.log('✅ Reference parity: OK')
    process.exit(0)
  }

  console.log('')
  console.log(`❌ Reference parity: ${mismatches.length} mismatch(es)`)
  for (const m of mismatches) {
    console.log('')
    console.log(`--- ${m.label} ---`)
    console.log(`ref exit: ${m.ref.exitCode}, cur exit: ${m.cur.exitCode}`)
    if (m.snippet) {
      console.log(`first diff @${m.snippet.index}`)
      console.log('ref:', JSON.stringify(m.snippet.a))
      console.log('cur:', JSON.stringify(m.snippet.b))
    } else {
      const outDiff = firstDiffSnippet(m.ref.stdout, m.cur.stdout)
      const errDiff = firstDiffSnippet(m.ref.stderr, m.cur.stderr)
      if (outDiff) {
        console.log(`stdout diff @${outDiff.index}`)
        console.log('ref:', JSON.stringify(outDiff.a))
        console.log('cur:', JSON.stringify(outDiff.b))
      }
      if (errDiff) {
        console.log(`stderr diff @${errDiff.index}`)
        console.log('ref:', JSON.stringify(errDiff.a))
        console.log('cur:', JSON.stringify(errDiff.b))
      }
    }
  }

  process.exit(1)
}

await main()
