import { KodeAgentStructuredStdio } from '@utils/protocol/kodeAgentStructuredStdio'

export function createPrintModeStructuredStdio(args: {
  enabled: boolean
  stdin: any
  stdout: any
  onInterrupt: () => void
  onControlRequest: (msg: any) => Promise<any>
}): KodeAgentStructuredStdio | null {
  if (!args.enabled) return null

  return new KodeAgentStructuredStdio(args.stdin, args.stdout, {
    onInterrupt: args.onInterrupt,
    onControlRequest: args.onControlRequest,
  })
}

