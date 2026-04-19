import { env } from '@utils/config/env'

export const BLACK_CIRCLE = env.platform === 'macos' ? '⏺' : '●'
