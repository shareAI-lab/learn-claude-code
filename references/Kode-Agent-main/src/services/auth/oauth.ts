import * as crypto from 'crypto'
import * as http from 'http'
import { IncomingMessage, ServerResponse } from 'http'
import * as url from 'url'

import { OAUTH_CONFIG } from '@constants/oauth'
import { openBrowser } from '@utils/system/browser'
import { logError } from '@utils/log'
import {
  AccountInfo,
  getGlobalConfig,
  saveGlobalConfig,
  normalizeApiKeyForConfig,
} from '@utils/config'

function base64URLEncode(buffer: Buffer): string {
  return buffer
    .toString('base64')
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=/g, '')
}

function generateCodeVerifier(): string {
  return base64URLEncode(crypto.randomBytes(32))
}

async function generateCodeChallenge(verifier: string): Promise<string> {
  const encoder = new TextEncoder()
  const data = encoder.encode(verifier)
  const digest = await crypto.subtle.digest('SHA-256', data)
  return base64URLEncode(Buffer.from(digest))
}

type OAuthTokenExchangeResponse = {
  access_token: string
  account?: {
    uuid: string
    email_address: string
  }
  organization?: {
    uuid: string
    name: string
  }
}

export type OAuthResult = {
  accessToken: string
}

export class OAuthService {
  private server: http.Server | null = null
  private codeVerifier: string
  private expectedState: string | null = null
  private pendingCodePromise: {
    resolve: (result: {
      authorizationCode: string
      useManualRedirect: boolean
    }) => void
    reject: (err: Error) => void
  } | null = null

  constructor() {
    this.codeVerifier = generateCodeVerifier()
  }

  private generateAuthUrls(
    codeChallenge: string,
    state: string,
  ): { autoUrl: string; manualUrl: string } {
    function makeUrl(isManual: boolean): string {
      const authUrl = new URL(OAUTH_CONFIG.AUTHORIZE_URL)
      authUrl.searchParams.append('client_id', OAUTH_CONFIG.CLIENT_ID)
      authUrl.searchParams.append('response_type', 'code')
      authUrl.searchParams.append(
        'redirect_uri',
        isManual
          ? OAUTH_CONFIG.MANUAL_REDIRECT_URL
          : `http://localhost:${OAUTH_CONFIG.REDIRECT_PORT}/callback`,
      )
      authUrl.searchParams.append('scope', OAUTH_CONFIG.SCOPES.join(' '))
      authUrl.searchParams.append('code_challenge', codeChallenge)
      authUrl.searchParams.append('code_challenge_method', 'S256')
      authUrl.searchParams.append('state', state)
      return authUrl.toString()
    }

    return {
      autoUrl: makeUrl(false),
      manualUrl: makeUrl(true),
    }
  }

  async startOAuthFlow(
    authURLHandler: (url: string) => Promise<void>,
  ): Promise<OAuthResult> {
    const codeChallenge = await generateCodeChallenge(this.codeVerifier)
    const state = base64URLEncode(crypto.randomBytes(32))
    this.expectedState = state
    const { autoUrl, manualUrl } = this.generateAuthUrls(codeChallenge, state)

    const onReady = async () => {
      await authURLHandler(manualUrl)
      await openBrowser(autoUrl)
    }

    const { authorizationCode, useManualRedirect } = await new Promise<{
      authorizationCode: string
      useManualRedirect: boolean
    }>((resolve, reject) => {
      this.pendingCodePromise = { resolve, reject }
      this.startLocalServer(state, onReady)
    })

    const {
      access_token: accessToken,
      account,
      organization,
    } = await this.exchangeCodeForTokens(
      authorizationCode,
      state,
      useManualRedirect,
    )

    if (account) {
      const accountInfo: AccountInfo = {
        accountUuid: account.uuid,
        emailAddress: account.email_address,
        organizationUuid: organization?.uuid,
      }
      const config = getGlobalConfig()
      config.oauthAccount = accountInfo
      saveGlobalConfig(config)
    }

    return { accessToken }
  }

  private startLocalServer(state: string, onReady?: () => void): void {
    if (this.server) {
      this.closeServer()
    }
    this.server = http.createServer(
      (req: IncomingMessage, res: ServerResponse) => {
        const parsedUrl = url.parse(req.url || '', true)

        if (parsedUrl.pathname === '/callback') {
          const authorizationCode = parsedUrl.query.code as string
          const returnedState = parsedUrl.query.state as string

          if (!authorizationCode) {
            res.writeHead(400)
            res.end('Authorization code not found')
            if (this.pendingCodePromise) {
              this.pendingCodePromise.reject(
                new Error('No authorization code received'),
              )
            }
            return
          }

          if (returnedState !== state) {
            res.writeHead(400)
            res.end('Invalid state parameter')
            if (this.pendingCodePromise) {
              this.pendingCodePromise.reject(
                new Error('Invalid state parameter'),
              )
            }
            return
          }

          res.writeHead(302, {
            Location: OAUTH_CONFIG.SUCCESS_URL,
          })
          res.end()

          this.processCallback({
            authorizationCode,
            state,
            useManualRedirect: false,
          })
        } else {
          res.writeHead(404)
          res.end()
        }
      },
    )

    this.server.listen(OAUTH_CONFIG.REDIRECT_PORT, async () => {
      onReady?.()
    })

    this.server.on('error', (err: Error) => {
      const portError = err as NodeJS.ErrnoException
      if (portError.code === 'EADDRINUSE') {
        const error = new Error(
          `Port ${OAUTH_CONFIG.REDIRECT_PORT} is already in use. Please ensure no other applications are using this port.`,
        )
        logError(error)
        this.closeServer()
        if (this.pendingCodePromise) {
          this.pendingCodePromise.reject(error)
        }
        return
      } else {
        logError(err)
        this.closeServer()
        if (this.pendingCodePromise) {
          this.pendingCodePromise.reject(err)
        }
        return
      }
    })
  }

  private async exchangeCodeForTokens(
    authorizationCode: string,
    state: string,
    useManualRedirect: boolean = false,
  ): Promise<OAuthTokenExchangeResponse> {
	    const requestBody = {
	      grant_type: 'authorization_code',
	      code: authorizationCode,
	      redirect_uri: useManualRedirect
	        ? OAUTH_CONFIG.MANUAL_REDIRECT_URL
	        : `http://localhost:${OAUTH_CONFIG.REDIRECT_PORT}/callback`,
	      client_id: OAUTH_CONFIG.CLIENT_ID,
	      code_verifier: this.codeVerifier,
	      state,
	    }

    const response = await fetch(OAUTH_CONFIG.TOKEN_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestBody),
    })

    if (!response.ok) {
      throw new Error(`Token exchange failed: ${response.statusText}`)
    }

    const data = await response.json()
    return data
  }

  processCallback({
    authorizationCode,
    state,
    useManualRedirect,
  }: {
    authorizationCode: string
    state: string
    useManualRedirect: boolean
  }): void {
    this.closeServer()

    if (state !== this.expectedState) {
      if (this.pendingCodePromise) {
        this.pendingCodePromise.reject(
          new Error('Invalid state parameter'),
        )
        this.pendingCodePromise = null
      }
      return
    }

    if (this.pendingCodePromise) {
      this.pendingCodePromise.resolve({ authorizationCode, useManualRedirect })
      this.pendingCodePromise = null
    }
  }

  private closeServer(): void {
    if (this.server) {
      this.server.close()
      this.server = null
    }
  }
}

export async function createAndStoreApiKey(
  accessToken: string,
): Promise<string | null> {
  try {
    const createApiKeyResp = await fetch(OAUTH_CONFIG.API_KEY_URL, {
      method: 'POST',
      headers: { Authorization: `Bearer ${accessToken}` },
    })

    let apiKeyData
    let errorText = ''

    try {
      apiKeyData = await createApiKeyResp.json()
    } catch (_e) {
      errorText = await createApiKeyResp.text()
    }

    if (createApiKeyResp.ok && apiKeyData && apiKeyData.raw_key) {
      const apiKey = apiKeyData.raw_key

      const config = getGlobalConfig()

      if (!config.customApiKeyResponses) {
        config.customApiKeyResponses = { approved: [], rejected: [] }
      }
      if (!config.customApiKeyResponses.approved) {
        config.customApiKeyResponses.approved = []
      }

      const normalizedKey = normalizeApiKeyForConfig(apiKey)
      if (!config.customApiKeyResponses.approved.includes(normalizedKey)) {
        config.customApiKeyResponses.approved.push(normalizedKey)
      }

      saveGlobalConfig(config)

      try {
        const { resetAnthropicClient } = await import('@services/llm')
        resetAnthropicClient()
      } catch {}

      return apiKey
    }

    return null
  } catch (error) {
    throw error
  }
}
