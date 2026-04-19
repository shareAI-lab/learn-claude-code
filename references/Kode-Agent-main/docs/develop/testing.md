# Kode CLI Test Suite

AI-friendly testing framework that validates multi-model adapter architecture with clear separation between unit, integration, and production testing.

## Testing Philosophy

### Three-Tier Architecture

**Unit Tests** - Fast, isolated adapter logic validation with mock data
**Integration Tests** - End-to-end CLI workflow testing through `claude.ts`
**Production Tests** - Real API validation (opt-in with `PRODUCTION_TEST_MODE=true`)

### Key Principles

1. **Clear Separation** - Each behavior tested exactly once
2. **Environment Resilience** - Graceful handling of missing credentials
3. **Fast Feedback** - Unit tests complete in < 100ms total
4. **Adapter Safety** - Validate Chat Completions fallback strategy

## Test Categories

### Unit Tests
Fast, isolated validation of adapter logic with mock data and predictable responses.

### Integration Tests
End-to-end CLI workflow testing through `claude.ts` with real API calls when credentials available.

### Production Tests
Real API validation (opt-in only with `PRODUCTION_TEST_MODE=true`) for comprehensive workflow testing.

### Diagnostic Tests
Regression prevention and performance benchmarking for known issues.

## Adapter Testing Strategy

### Model-Driven Testing

```bash
# Test specific adapter types
TEST_MODEL=gpt5          # First Responses API model
TEST_MODEL=glm           # First Chat Completions model
TEST_MODEL=specific-name # Exact model match

# Enable production testing
PRODUCTION_TEST_MODE=true bun test
```

### Test Design Principles

#### 1. Clear Separation of Concerns
- **Comprehensive Tests**: General adapter functionality for all models
- **API-Specific Tests**: Features unique to each API architecture
- **No Duplication**: Each behavior tested exactly once

#### 2. Environment Resilience
```typescript
// Tests handle missing credentials gracefully
const apiKey = process.env.TEST_GPT5_API_KEY
if (!apiKey) {
  test.skip('Missing TEST_GPT5_API_KEY')
}
```

#### 3. Fast Feedback Loop
- Unit tests run in < 100ms total
- Integration tests only when needed
- Production tests opt-in only

### Adapter-Specific Testing

#### Chat Completions Adapter Tests
- Request building with various model types
- Tool calling format compatibility
- Streaming response parsing
- Error handling for malformed responses

#### Responses API Adapter Tests
- Native Responses API request format
- Reasoning effort parameter handling
- SSE streaming with proper chunk parsing
- State management with response IDs

#### Cross-Adapter Validation
- Same model produces consistent results
- Token normalization works across adapters
- Error handling is adapter-agnostic

## Victory Conditions

A test suite passes when:

1. **✅ Clear Purpose**: Each test file has documented intent and scope
2. **✅ No Redundancy**: Each behavior is tested exactly once
3. **✅ Focused Tests**: Tests validate specific behaviors without overlap
4. **✅ Complete Coverage**: All adapter types and API-specific features are tested
5. **✅ Environment Ready**: Tests handle setup/teardown automatically
6. **✅ Multi-Model Support**: All configured models are tested
7. **✅ Maintainable Structure**: Tests are easy to understand and modify
8. **✅ Adapter Safety**: Chat Completions fallback strategy validated
9. **✅ Token Normalization**: Canonical token structure works across all adapters
10. **✅ Capability-Driven**: Model capabilities properly influence adapter behavior
