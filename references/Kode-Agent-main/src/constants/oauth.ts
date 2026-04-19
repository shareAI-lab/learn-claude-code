const BASE_CONFIG = {
  REDIRECT_PORT: 54545,
  MANUAL_REDIRECT_URL: '/oauth/code/callback',
  SCOPES: ['org:create_api_key', 'user:profile'] as const,
}

const PROD_OAUTH_CONFIG = {
  ...BASE_CONFIG,
  AUTHORIZE_URL: '',
  TOKEN_URL: '',
  API_KEY_URL: '',
  SUCCESS_URL: '',
  CLIENT_ID: '',
} as const

export const OAUTH_CONFIG = PROD_OAUTH_CONFIG
