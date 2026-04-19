import 'bun'

declare module 'bun:test' {
  type TestFn = (done: (err?: unknown) => void) => void | Promise<unknown>
  interface TestOptions {
    timeout?: number
    todo?: boolean
    skip?: boolean
  }

  export function test(
    name: string,
    options: TestOptions,
    fn: TestFn | (() => void | Promise<unknown>),
  ): void
}
