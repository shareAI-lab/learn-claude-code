import net from 'node:net'
import type { AddressInfo } from 'node:net'
import { URL } from 'node:url'
import { logError } from '@utils/log'
import type { SandboxRuntimeConfig } from './sandboxConfig'

export type SandboxNetworkPermissionQuery = { host: string; port: number }
export type SandboxNetworkPermissionCallback = (
  query: SandboxNetworkPermissionQuery,
) => Promise<boolean>

export type SandboxNetworkInfrastructurePorts = {
  httpProxyPort: number
  socksProxyPort: number
}

type ActiveState = {
  config: SandboxRuntimeConfig | null
  permissionCallback: SandboxNetworkPermissionCallback | null
  httpProxyServer: net.Server | null
  socksProxyServer: net.Server | null
  httpProxyPort: number | null
  socksProxyPort: number | null
  initializationPromise: Promise<SandboxNetworkInfrastructurePorts> | null
  cleanupRegistered: boolean
  sessionAllowedHosts: Set<string>
  sessionDeniedHosts: Set<string>
  inflightPermissionRequests: Map<string, Promise<boolean>>
  permissionPromptChain: Promise<void>
}

const active: ActiveState = {
  config: null,
  permissionCallback: null,
  httpProxyServer: null,
  socksProxyServer: null,
  httpProxyPort: null,
  socksProxyPort: null,
  initializationPromise: null,
  cleanupRegistered: false,
  sessionAllowedHosts: new Set(),
  sessionDeniedHosts: new Set(),
  inflightPermissionRequests: new Map(),
  permissionPromptChain: Promise.resolve(),
}

export function matchesSandboxDomainPattern(
  host: string,
  pattern: string,
): boolean {
  if (pattern.startsWith('*.')) {
    const suffix = pattern.substring(2)
    return host.toLowerCase().endsWith('.' + suffix.toLowerCase())
  }
  return host.toLowerCase() === pattern.toLowerCase()
}

async function shouldAllowNetworkRequest(
  query: SandboxNetworkPermissionQuery,
): Promise<boolean> {
  const config = active.config
  if (!config) return false

  const hostKey = query.host.toLowerCase()
  if (active.sessionAllowedHosts.has(hostKey)) return true
  if (active.sessionDeniedHosts.has(hostKey)) return false

  for (const denied of config.network.deniedDomains) {
    if (matchesSandboxDomainPattern(query.host, denied)) return false
  }
  for (const allowed of config.network.allowedDomains) {
    if (matchesSandboxDomainPattern(query.host, allowed)) return true
  }

  const permissionCallback = active.permissionCallback
  if (!permissionCallback) return false

  const existing = active.inflightPermissionRequests.get(hostKey)
  if (existing) return existing

  const requestPromise = (async () => {
    const decision = await serializePermissionPrompt(async () => {
      try {
        return await permissionCallback(query)
      } catch (error) {
        logError(error)
        return false
      }
    })

    if (decision) active.sessionAllowedHosts.add(hostKey)
    else active.sessionDeniedHosts.add(hostKey)

    return decision
  })().finally(() => {
    active.inflightPermissionRequests.delete(hostKey)
  })

  active.inflightPermissionRequests.set(hostKey, requestPromise)
  return requestPromise
}

async function serializePermissionPrompt<T>(
  task: () => Promise<T>,
): Promise<T> {
  let release: (() => void) | null = null
  const next = new Promise<void>(resolve => {
    release = resolve
  })
  const prev = active.permissionPromptChain
  active.permissionPromptChain = prev.then(() => next)

  try {
    await prev
    return await task()
  } finally {
    release?.()
  }
}

function registerCleanupOnce(): void {
  if (active.cleanupRegistered) return
  active.cleanupRegistered = true

  const cleanup = () => {
    void cleanupSandboxNetworkInfrastructure()
  }

  process.once('exit', cleanup)
  process.once('SIGINT', cleanup)
  process.once('SIGTERM', cleanup)
}

async function cleanupSandboxNetworkInfrastructure(): Promise<void> {
  const httpServer = active.httpProxyServer
  const socksServer = active.socksProxyServer
  active.httpProxyServer = null
  active.socksProxyServer = null
  active.httpProxyPort = null
  active.socksProxyPort = null
  active.initializationPromise = null

  active.sessionAllowedHosts.clear()
  active.sessionDeniedHosts.clear()
  active.inflightPermissionRequests.clear()

  await Promise.allSettled([
    httpServer
      ? new Promise<void>(resolve => {
          try {
            httpServer.close(() => resolve())
          } catch {
            resolve()
          }
        })
      : Promise.resolve(),
    socksServer
      ? new Promise<void>(resolve => {
          try {
            socksServer.close(() => resolve())
          } catch {
            resolve()
          }
        })
      : Promise.resolve(),
  ])
}

function parseConnectTarget(
  value: string,
): { host: string; port: number } | null {
  const trimmed = value.trim()
  const firstToken = trimmed.split(/\s+/)[0]
  const withoutLeadingSlash = firstToken.startsWith('/')
    ? firstToken.slice(1)
    : firstToken
  const authority = withoutLeadingSlash.startsWith('//')
    ? withoutLeadingSlash.slice(2)
    : withoutLeadingSlash

  try {
    const url = new URL(`http://${authority}`)
    if (!url.hostname) return null
    const port = Number(url.port) || 443
    return { host: url.hostname, port }
  } catch {
    return null
  }
}

function writeHttpErrorResponse(socket: net.Socket, statusLine: string): void {
  try {
    socket.write(
      `HTTP/1.1 ${statusLine}\r\nConnection: close\r\nContent-Length: 0\r\n\r\n`,
    )
  } catch {}
  try {
    socket.destroy()
  } catch {}
}

async function startHttpProxy(): Promise<number> {
  const server = net.createServer(clientSocket => {
    let buffered: Buffer<ArrayBufferLike> = Buffer.alloc(
      0,
    ) as Buffer<ArrayBufferLike>

    const onData = (chunk: Buffer) => {
      buffered = buffered.length ? Buffer.concat([buffered, chunk]) : chunk

      const headerEnd = buffered.indexOf('\r\n\r\n')
      if (headerEnd === -1) return

      const headerText = buffered.slice(0, headerEnd).toString('latin1')
      const remainder = buffered.slice(headerEnd + 4)
      buffered = Buffer.alloc(0)
      clientSocket.off('data', onData)

      const lines = headerText.split('\r\n')
      const requestLine = lines.shift() ?? ''
      const [methodRaw, targetRaw, versionRaw] = requestLine.split(' ')
      const method = (methodRaw ?? '').trim().toUpperCase()
      const target = (targetRaw ?? '').trim()
      const version = (versionRaw ?? 'HTTP/1.1').trim() || 'HTTP/1.1'

      if (!method || !target) {
        writeHttpErrorResponse(clientSocket, '400 Bad Request')
        return
      }

      const headers: Record<string, string> = {}
      for (const line of lines) {
        const idx = line.indexOf(':')
        if (idx === -1) continue
        const key = line.slice(0, idx).trim().toLowerCase()
        const value = line.slice(idx + 1).trim()
        if (!key) continue
        headers[key] = value
      }

      if (method === 'CONNECT') {
        void (async () => {
          const targetValue = target || headers['host'] || ''
          const parsed = targetValue ? parseConnectTarget(targetValue) : null
          if (!parsed) {
            writeHttpErrorResponse(clientSocket, '400 Bad Request')
            return
          }

          const allowed = await shouldAllowNetworkRequest({
            host: parsed.host,
            port: parsed.port,
          })
          if (!allowed) {
            writeHttpErrorResponse(clientSocket, '403 Forbidden')
            return
          }

          const upstream = net.connect(parsed.port, parsed.host)
          upstream.once('error', () => {
            writeHttpErrorResponse(clientSocket, '502 Bad Gateway')
          })

          upstream.once('connect', () => {
            try {
              clientSocket.write('HTTP/1.1 200 Connection Established\r\n\r\n')
            } catch {
              try {
                upstream.destroy()
              } catch {}
              return
            }

            if (remainder.length > 0) {
              try {
                upstream.write(remainder)
              } catch {}
            }

            clientSocket.pipe(upstream)
            upstream.pipe(clientSocket)
          })
        })()
        return
      }

      void (async () => {
        const hostHeader = headers['host'] ?? ''
        let targetUrl: URL | null = null
        if (target.startsWith('http://') || target.startsWith('https://')) {
          try {
            targetUrl = new URL(target)
          } catch {
            targetUrl = null
          }
	        } else if (hostHeader) {
	          try {
	            targetUrl = new URL(
	              `http://${hostHeader}${target.startsWith('/') ? target : '/' + target}`,
	            )
	          } catch {
	            targetUrl = null
	          }
	        }

        if (!targetUrl) {
          writeHttpErrorResponse(clientSocket, '400 Bad Request')
          return
        }

        const port =
          targetUrl.port !== ''
            ? Number(targetUrl.port)
            : targetUrl.protocol === 'https:'
              ? 443
              : 80

        const allowed = await shouldAllowNetworkRequest({
          host: targetUrl.hostname,
          port,
        })
        if (!allowed) {
          writeHttpErrorResponse(clientSocket, '403 Forbidden')
          return
        }

        if (targetUrl.protocol === 'https:') {
          writeHttpErrorResponse(clientSocket, '400 Bad Request')
          return
        }

        delete headers['proxy-connection']
        delete headers['proxy-authorization']
        headers['connection'] = 'close'
        headers['host'] = targetUrl.host

        const upstream = net.connect(port, targetUrl.hostname)
        upstream.once('error', () => {
          writeHttpErrorResponse(clientSocket, '502 Bad Gateway')
        })

        upstream.once('connect', () => {
          const path = `${targetUrl.pathname}${targetUrl.search}`
          try {
            upstream.write(`${method} ${path} ${version}\r\n`)
            for (const [k, v] of Object.entries(headers)) {
              upstream.write(`${k}: ${v}\r\n`)
            }
            upstream.write('\r\n')
          } catch {
            writeHttpErrorResponse(clientSocket, '502 Bad Gateway')
            try {
              upstream.destroy()
            } catch {}
            return
          }

          if (remainder.length > 0) {
            try {
              upstream.write(remainder)
            } catch {}
          }

          clientSocket.pipe(upstream)
          upstream.pipe(clientSocket)
          upstream.once('end', () => {
            try {
              clientSocket.end()
            } catch {}
          })
        })
      })()
    }

    clientSocket.on('data', onData)
  })

  active.httpProxyServer = server

  return new Promise<number>((resolve, reject) => {
    server.once('error', reject)
    server.once('listening', () => {
      const addr = server.address()
      if (!addr || typeof addr === 'string') {
        reject(new Error('Failed to get HTTP proxy address'))
        return
      }
      server.unref()
      resolve((addr as AddressInfo).port)
    })
    server.listen(0, '127.0.0.1')
  })
}

function buildSocks5Reply(rep: number): Buffer {
  return Buffer.from([0x05, rep, 0x00, 0x01, 0, 0, 0, 0, 0, 0])
}

function parseSocks5Request(
  buffer: Buffer,
): { host: string; port: number; remaining: Buffer } | null {
  if (buffer.length < 4) return null
  if (buffer[0] !== 0x05) return null
  const cmd = buffer[1]
  const atyp = buffer[3]
  if (cmd !== 0x01) return null

  let offset = 4
  let host = ''

  if (atyp === 0x01) {
    if (buffer.length < offset + 4 + 2) return null
    host = `${buffer[offset]}.${buffer[offset + 1]}.${buffer[offset + 2]}.${buffer[offset + 3]}`
    offset += 4
  } else if (atyp === 0x03) {
    if (buffer.length < offset + 1) return null
    const len = buffer[offset]
    offset += 1
    if (buffer.length < offset + len + 2) return null
    host = buffer.slice(offset, offset + len).toString('utf8')
    offset += len
  } else if (atyp === 0x04) {
    if (buffer.length < offset + 16 + 2) return null
    const parts: string[] = []
    for (let i = 0; i < 16; i += 2) {
      parts.push(buffer.readUInt16BE(offset + i).toString(16))
    }
    host = parts.join(':')
    offset += 16
  } else {
    return null
  }

  const port = buffer.readUInt16BE(offset)
  offset += 2
  return { host, port, remaining: buffer.slice(offset) }
}

async function startSocks5Proxy(): Promise<number> {
  const server = net.createServer(socket => {
    let buffered: Buffer<ArrayBufferLike> = Buffer.alloc(
      0,
    ) as Buffer<ArrayBufferLike>
    let stage: 'greeting' | 'request' = 'greeting'

    const onData = (chunk: Buffer) => {
      buffered = buffered.length ? Buffer.concat([buffered, chunk]) : chunk

      if (stage === 'greeting') {
        if (buffered.length < 2) return
        if (buffered[0] !== 0x05) {
          socket.end()
          return
        }

        const nMethods = buffered[1]
        if (buffered.length < 2 + nMethods) return
        const methods = buffered.slice(2, 2 + nMethods)
        const supportsNoAuth = methods.includes(0x00)
        socket.write(Buffer.from([0x05, supportsNoAuth ? 0x00 : 0xff]))
        buffered = buffered.slice(2 + nMethods)
        if (!supportsNoAuth) {
          socket.end()
          return
        }
        stage = 'request'
      }

      if (stage === 'request') {
        const parsed = parseSocks5Request(buffered)
        if (!parsed) return
        buffered = parsed.remaining

        void (async () => {
          const allowed = await shouldAllowNetworkRequest({
            host: parsed.host,
            port: parsed.port,
          })
          if (!allowed) {
            socket.write(buildSocks5Reply(0x02))
            socket.end()
            return
          }

          const upstream = net.connect(parsed.port, parsed.host)
          upstream.once('error', () => {
            try {
              socket.write(buildSocks5Reply(0x05))
            } catch {}
            socket.end()
          })
          upstream.once('connect', () => {
            try {
              socket.write(buildSocks5Reply(0x00))
            } catch {
              try {
                upstream.destroy()
              } catch {}
              socket.end()
              return
            }
            socket.pipe(upstream)
            upstream.pipe(socket)
          })
        })()
      }
    }

    socket.on('data', onData)
  })

  active.socksProxyServer = server

  return new Promise<number>((resolve, reject) => {
    server.once('error', reject)
    server.once('listening', () => {
      const addr = server.address()
      if (!addr || typeof addr === 'string') {
        reject(new Error('Failed to get SOCKS proxy address'))
        return
      }
      server.unref()
      resolve((addr as AddressInfo).port)
    })
    server.listen(0, '127.0.0.1')
  })
}

export async function ensureSandboxNetworkInfrastructure(options: {
  runtimeConfig: SandboxRuntimeConfig
  permissionCallback?: SandboxNetworkPermissionCallback | null
}): Promise<SandboxNetworkInfrastructurePorts> {
  active.config = options.runtimeConfig
  active.permissionCallback = options.permissionCallback ?? null

  if (active.initializationPromise) return active.initializationPromise

  registerCleanupOnce()

  active.initializationPromise = (async () => {
    const httpProxyPort =
      options.runtimeConfig.network.httpProxyPort !== undefined
        ? options.runtimeConfig.network.httpProxyPort
        : await startHttpProxy()

    const socksProxyPort =
      options.runtimeConfig.network.socksProxyPort !== undefined
        ? options.runtimeConfig.network.socksProxyPort
        : await startSocks5Proxy()

    active.httpProxyPort = httpProxyPort
    active.socksProxyPort = socksProxyPort

    return { httpProxyPort, socksProxyPort }
  })().catch(async error => {
    active.initializationPromise = null
    await cleanupSandboxNetworkInfrastructure()
    throw error
  })

  return active.initializationPromise
}

export function getSandboxNetworkInfrastructurePorts(): SandboxNetworkInfrastructurePorts | null {
  if (active.httpProxyPort === null || active.socksProxyPort === null)
    return null
  return {
    httpProxyPort: active.httpProxyPort,
    socksProxyPort: active.socksProxyPort,
  }
}

export async function __resetSandboxNetworkInfrastructureForTests(): Promise<void> {
  await cleanupSandboxNetworkInfrastructure()
  active.permissionCallback = null
  active.config = null
  active.permissionPromptChain = Promise.resolve()
}
