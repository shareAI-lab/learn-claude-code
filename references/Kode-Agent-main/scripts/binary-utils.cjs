const os = require('node:os')
const path = require('node:path')

function getPlatformArch(platform = process.platform, arch = process.arch) {
  return `${platform}-${arch}`
}

function getBinaryFilename(platform = process.platform) {
  return platform === 'win32' ? 'kode.exe' : 'kode'
}

function getDefaultBinBaseDir() {
  return (
    process.env.KODE_BIN_DIR ||
    process.env.ANYKODE_BIN_DIR ||
    path.join(os.homedir(), '.kode', 'bin')
  )
}

function getCachedBinaryPath(options) {
  const version = options?.version
  const platform = options?.platform ?? process.platform
  const arch = options?.arch ?? process.arch
  const baseDir = options?.baseDir ?? getDefaultBinBaseDir()
  if (!version) throw new Error('getCachedBinaryPath: version is required')

  return path.join(baseDir, version, getPlatformArch(platform, arch), getBinaryFilename(platform))
}

function getGithubReleaseBinaryAssetName(platform = process.platform, arch = process.arch) {
  const ext = platform === 'win32' ? '.exe' : ''
  return `kode-${platform}-${arch}${ext}`
}

function getGithubReleaseBinaryUrl(options) {
  const version = options?.version
  const platform = options?.platform ?? process.platform
  const arch = options?.arch ?? process.arch
  const owner = options?.owner ?? 'shareAI-lab'
  const repo = options?.repo ?? 'kode'
  const tag = options?.tag ?? `v${version}`
  const baseUrl = options?.baseUrl ?? process.env.KODE_BINARY_BASE_URL

  if (!version) throw new Error('getGithubReleaseBinaryUrl: version is required')

  if (baseUrl) {
    const trimmed = String(baseUrl).replace(/\/+$/, '')
    return `${trimmed}/${getGithubReleaseBinaryAssetName(platform, arch)}`
  }

  return `https://github.com/${owner}/${repo}/releases/download/${tag}/${getGithubReleaseBinaryAssetName(platform, arch)}`
}

module.exports = {
  getPlatformArch,
  getBinaryFilename,
  getDefaultBinBaseDir,
  getCachedBinaryPath,
  getGithubReleaseBinaryAssetName,
  getGithubReleaseBinaryUrl,
}

