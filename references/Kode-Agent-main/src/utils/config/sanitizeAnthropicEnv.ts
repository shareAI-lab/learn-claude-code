const deprecatedAnthropicEnvVars = [
  'ANTHROPIC_BASE_URL',
  'ANTHROPIC_API_KEY',
  'ANTHROPIC_API_TOKEN',
  'ANTHROPIC_API_Token',
]

for (const key of deprecatedAnthropicEnvVars) {
  if (process.env[key]) {
    delete process.env[key]
  }
}
