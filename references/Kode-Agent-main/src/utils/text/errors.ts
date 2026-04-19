export class MalformedCommandError extends TypeError {}

export class DeprecatedCommandError extends Error {}

export class AbortError extends Error {}

export class ConfigParseError extends Error {
  filePath: string
  defaultConfig: unknown

  constructor(message: string, filePath: string, defaultConfig: unknown) {
    super(message)
    this.name = 'ConfigParseError'
    this.filePath = filePath
    this.defaultConfig = defaultConfig
  }
}
