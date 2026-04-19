#!/usr/bin/env bun
import '@utils/config/sanitizeAnthropicEnv'
import { initSentry } from '@services/sentry'
import {
  ensurePackagedRuntimeEnv,
  ensureYogaWasmPath,
} from './cli/bootstrapEnv'
import { installProcessHandlers, runCli } from './cli/runCli'

initSentry()
ensurePackagedRuntimeEnv()
ensureYogaWasmPath(import.meta.url)

import * as dontcare from '@anthropic-ai/sdk/shims/node'
Object.keys(dontcare)

installProcessHandlers()
void runCli()

