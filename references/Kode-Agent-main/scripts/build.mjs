#!/usr/bin/env bun
import {
  chmodSync,
  cpSync,
  mkdirSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from 'node:fs'
import { join } from 'node:path'
import { build as esbuildBuild } from 'esbuild'

const OUT_DIR = 'dist'

function loadEsbuildTsconfigRaw() {
  try {
    const raw = JSON.parse(readFileSync('tsconfig.json', 'utf8'))
    const compilerOptions = raw?.compilerOptions ?? {}
    const paths = { ...(compilerOptions.paths ?? {}) }
    // Prevent esbuild from rewriting all package imports via "*" -> node_modules/*.
    delete paths['*']

    return {
      compilerOptions: {
        ...compilerOptions,
        paths,
      },
    }
  } catch {
    return undefined
  }
}

const ESBUILD_TSCONFIG_RAW = loadEsbuildTsconfigRaw()

async function buildWithEsbuild(options) {
  try {
    await esbuildBuild({
      entryPoints: options.entrypoints,
      outdir: options.outdir,
      bundle: true,
      platform: 'node',
      target: ['node20'],
      format: 'esm',
      splitting: true,
      // Keep node_modules as runtime dependencies (avoid bundling optional deps like ink devtools).
      packages: 'external',
      sourcemap: 'external',
      banner: {
        // Allow CJS-style `require(...)` from ESM output (esbuild may emit dynamic requires
        // for optional dependencies).
        js: 'import { createRequire as __kodeCreateRequire } from "node:module";\nconst require = __kodeCreateRequire(import.meta.url);',
      },
      ...(ESBUILD_TSCONFIG_RAW ? { tsconfigRaw: ESBUILD_TSCONFIG_RAW } : {}),
    })
  } catch (err) {
    throw new Error(
      `esbuild failed (${options.label}): ${err instanceof Error ? err.message : String(err)}`,
    )
  }
}

async function main() {
  console.log('🚀 Building Kode CLI (Bun dev + Node runtime)...')

  rmSync(OUT_DIR, { recursive: true, force: true })
  mkdirSync(OUT_DIR, { recursive: true })

  // Build the unified entry (src/entrypoints/index.ts -> dist/index.js)
  // and its dynamic imports (cli/acp/mcp) as split chunks.
  await buildWithEsbuild({
    label: 'npm',
    entrypoints: ['src/entrypoints/index.ts'],
    outdir: OUT_DIR,
  })

  // Mark dist as ESM for interoperability (some tooling still expects this)
  writeFileSync(
    join(OUT_DIR, 'package.json'),
    JSON.stringify({ type: 'module', main: './index.js' }, null, 2),
  )

  // Copy yoga.wasm alongside outputs (helps in environments where root assets are stripped)
  try {
    cpSync('yoga.wasm', join(OUT_DIR, 'yoga.wasm'))
  } catch (err) {
    console.warn(
      '⚠️  Could not copy yoga.wasm:',
      err instanceof Error ? err.message : String(err),
    )
  }

  // Copy vendor assets if present (ripgrep, future bundled tools)
  // Note: vendor assets are intentionally not shipped in the npm package.

  // Generate Node-based CLI shim (npm bin points here)
  // - Prefer cached native binary (Windows OOTB)
  // - Fallback to Node.js runtime (npm users don't need Bun)
  cpSync(join('scripts', 'cli-wrapper.cjs'), 'cli.js')
  try {
    chmodSync('cli.js', 0o755)
  } catch (err) {
    console.warn(
      '⚠️  Could not make cli.js executable:',
      err instanceof Error ? err.message : String(err),
    )
  }

  // Generate Node-based ACP shim (npm bin points here)
  cpSync(join('scripts', 'cli-acp-wrapper.cjs'), 'cli-acp.js')
  try {
    chmodSync('cli-acp.js', 0o755)
  } catch (err) {
    console.warn(
      '⚠️  Could not make cli-acp.js executable:',
      err instanceof Error ? err.message : String(err),
    )
  }

  // Create .npmrc file (kept intentionally tiny)
  writeFileSync(
    '.npmrc',
    `# Kode npm configuration
package-lock=false
save-exact=true
`,
  )

  console.log('✅ Build completed')
  console.log('📋 Outputs:')
  console.log('  - dist/index.js')
  console.log('  - cli.js')
  console.log('  - cli-acp.js')
}

main().catch(err => {
  console.error('❌ Build failed:', err)
  process.exit(1)
})
