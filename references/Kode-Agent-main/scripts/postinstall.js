#!/usr/bin/env node

// Postinstall responsibilities:
// - Best-effort download of the platform binary to a user-writable cache (Windows OOTB).
// - Never fail installation (script should be non-blocking and robust).

const fs = require('node:fs')
const path = require('node:path')
const https = require('node:https')
const { chmodSync } = require('node:fs')

const {
  getCachedBinaryPath,
  getGithubReleaseBinaryUrl,
  getPlatformArch,
} = require('./binary-utils.cjs')

function safeLog(line) {
  try {
    console.log(line)
  } catch {}
}

function safeWarn(line) {
  try {
    console.warn(line)
  } catch {}
}

function readPackageJson() {
  try {
    const pkgPath = path.join(process.cwd(), 'package.json')
    return JSON.parse(fs.readFileSync(pkgPath, 'utf8'))
  } catch {
    return null
  }
}

function ensureDir(dirPath) {
  fs.mkdirSync(dirPath, { recursive: true })
}

function downloadFile(url, destPath, redirectCount = 0) {
  return new Promise((resolve, reject) => {
    if (redirectCount > 8) {
      reject(new Error('Too many redirects'))
      return
    }

    const req = https.get(
      url,
      {
        headers: {
          'User-Agent': '@shareai-lab/kode postinstall',
          Accept: 'application/octet-stream',
        },
      },
      res => {
        const status = res.statusCode || 0
        const location = res.headers.location
        if (status >= 300 && status < 400 && location) {
          res.resume()
          resolve(downloadFile(location, destPath, redirectCount + 1))
          return
        }

        if (status !== 200) {
          res.resume()
          reject(new Error(`HTTP ${status}`))
          return
        }

        const tmpPath = `${destPath}.tmp-${process.pid}`
        const file = fs.createWriteStream(tmpPath)
        res.pipe(file)
        file.on('finish', () => {
          file.close(() => {
            fs.renameSync(tmpPath, destPath)
            resolve()
          })
        })
        file.on('error', err => {
          try { fs.unlinkSync(tmpPath) } catch {}
          reject(err)
        })
      },
    )

    req.on('error', reject)
  })
}

async function maybeInstallBinary() {
  if (process.env.KODE_SKIP_BINARY_DOWNLOAD) {
    return
  }

  const pkg = readPackageJson()
  const version = pkg?.version
  if (!version) return

  const platformArch = getPlatformArch()
  const dest = getCachedBinaryPath({ version })
  if (fs.existsSync(dest)) {
    return
  }

  try {
    ensureDir(path.dirname(dest))
  } catch {
    return
  }

  const url = getGithubReleaseBinaryUrl({ version })
  safeLog(`📦 Kode: installing native binary for ${platformArch} (v${version})`)

  try {
    await downloadFile(url, dest)
    if (process.platform !== 'win32') {
      try {
        chmodSync(dest, 0o755)
      } catch {}
    }
    safeLog(`✅ Kode: native binary ready at ${dest}`)
  } catch (err) {
    safeWarn(`⚠️  Kode: could not download native binary (${platformArch})`)
    safeWarn(`    URL: ${url}`)
    safeWarn(
      `    Reason: ${err instanceof Error ? err.message : String(err)}`,
    )
    safeWarn(`    This is non-fatal. Kode will fall back to Bun if available.`)
  }
}

async function postinstallNotice() {
  safeLog('✅ @shareai-lab/kode installed. Commands available: kode, kwa, kd')
  safeLog('   If shell cannot find them, reload your terminal or reinstall globally:')
  safeLog('   npm i -g @shareai-lab/kode  (or use: npx @shareai-lab/kode)')
  await maybeInstallBinary()
}

if (process.env.npm_lifecycle_event === 'postinstall') {
  postinstallNotice().catch(() => {})
}
