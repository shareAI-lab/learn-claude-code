# OpenAI Adapter Layer

OpenAI-compatible provider abstraction that routes requests through Chat Completions or Responses API while maintaining provider neutrality.

## Architecture

The adapter layer translates between Anthropic's internal format and various OpenAI-compatible APIs:

1. **Normalization** - Convert Anthropic messages to `UnifiedRequestParams`
2. **Adapter Selection** - Choose ChatCompletionsAdapter or ResponsesAPIAdapter based on model capabilities
3. **Request Construction** - Build provider-specific requests using capability-driven logic
4. **Response Normalization** - Convert provider responses back to `UnifiedResponse`

## Canonical Token Structure

### Eliminating Field Name Ambiguity

Different APIs use different token field names (`prompt_tokens` vs `input_tokens` vs `promptTokens`). The system normalizes all API responses to a canonical `TokenUsage` interface:

```typescript
interface TokenUsage {
  input: number      // Always called "input"
  output: number     // Always called "output"
  total?: number     // Optional total
  reasoning?: number // Optional reasoning tokens
}
```

### Boundary Normalization

All adapters call `normalizeTokens()` once at the API boundary, eliminating ambiguity throughout the rest of the system.

## Capability-Driven Adapter Logic

### Smart Field Selection

Adapters use model capabilities to determine request parameters:

```typescript
// Smart max tokens field selection
const maxTokensField = this.getMaxTokensParam() // From model capabilities
request[maxTokensField] = maxTokens

// Capability-driven feature enablement
if (this.capabilities.parameters.supportsReasoningEffort && params.reasoningEffort) {
  request.reasoning_effort = params.reasoningEffort
}

if (this.capabilities.streaming.supported) {
  request.stream = true
  if (this.capabilities.streaming.includesUsage) {
    request.stream_options = { include_usage: true }
  }
}
```

### Model-Specific Constraints

Adapters use capabilities to handle model-specific requirements:

```typescript
// Capability-driven model constraints
if (this.capabilities.parameters.temperatureMode === 'fixed_one') {
  delete request.temperature
}

if (!this.capabilities.streaming.supported) {
  delete request.stream
  delete request.stream_options
}
```

## Chat Completions Fallback Strategy

### Safety-First Architecture

The system only uses new adapters for Responses API models. Chat Completions models use the proven legacy path to ensure stability.

```typescript
const shouldUseResponses = ModelAdapterFactory.shouldUseResponsesAPI(modelProfile)

// Only use new adapters for Responses API models
// Chat Completions models use legacy path for stability
if (shouldUseResponses) {
  const adapter = ModelAdapterFactory.createAdapter(modelProfile)
  // ... adapter logic
}
// Chat Completions models skip adapter creation and use proven legacy path
```

**Benefits:**
- **Stability**: Chat Completions models continue using battle-tested legacy path
- **Innovation**: Responses API models get new adapter improvements
- **Clean separation**: No dual execution paths for the same model type
- **Zero breakage**: All existing functionality preserved

## Extension Guide

### Adding New Models
1. Define capabilities in `src/constants/modelCapabilities.ts`
2. Add to `MODEL_CAPABILITIES_REGISTRY`
3. Test with integration tests

### Custom Provider Handling
For providers requiring custom protocol handling:
1. Extend `ModelAPIAdapter`
2. Implement required abstract methods
3. Register in `ModelAdapterFactory`

## Non-Obvious Design Patterns

### 1. Adapter Pattern for API Compatibility
- **What it looks like**: Code duplication across adapters
- **Why it's intentional**: Separate protocols require separate adapters for clarity and type safety

### 2. Canonical Data Normalization
- **What it looks like**: Multiple field names for the same concept
- **Why it's solved**: Normalize once at the API boundary to eliminate ambiguity

### 3. Capability-Driven Design
- **What it looks like**: Model-specific logic scattered throughout code
- **Why it's solved**: Centralize model behavior in capability definitions

### Safety-First Architecture

To ensure stability, the system only uses new adapters for Responses API models:

```typescript
const shouldUseResponses = ModelAdapterFactory.shouldUseResponsesAPI(modelProfile)

// Only use new adapters for Responses API models
// Chat Completions models use legacy path for stability
if (shouldUseResponses) {
  const adapter = ModelAdapterFactory.createAdapter(modelProfile)
  // ... adapter logic
}
// Chat Completions models skip adapter creation and use proven legacy path
```

**Benefits:**
- **Stability**: Chat Completions models continue using battle-tested legacy path
- **Innovation**: Responses API models get new adapter improvements
- **Clean separation**: No dual execution paths for the same model type
- **Zero breakage**: All existing functionality preserved

## Non-Obvious Design Patterns

### 1. Adapter Pattern for API Compatibility
- **What it looks like**: Code duplication across adapters (e.g., `chatCompletions.ts` vs `responsesAPI.ts`).
- **Why it's intentional**: Responses API and Chat Completions are fundamentally different protocols. Separate adapters provide clarity, type safety, and independent evolution at the cost of some duplication.
- **When to use**: When supporting multiple versions/formats of an API where a single abstraction would be leaky or overly complex.

### 2. Multi-Model Architecture
- **What it looks like**: Complex model management with profiles and pointers (`ModelManager`).
- **Why it's intentional**: Different models excel at different tasks (reasoning vs coding vs speed). This allows optimal model selection for each job.
- **When to use**: When you need to leverage the specific strengths of multiple AI models within a single workflow.

### 3. Canonical Data Normalization
- **What it looks like**: Multiple field names for the same concept (prompt_tokens vs input_tokens).
- **Why it's solved**: Normalize once at the API boundary to eliminate ambiguity throughout the system.
- **When to use**: When integrating multiple APIs with different naming conventions for the same concepts.

## Maintenance Tips

### Adding a New Model
1.  Add capability definition in `src/constants/modelCapabilities.ts`.
2.  Add to `MODEL_CAPABILITIES_REGISTRY`.
3.  Add default profile in `src/constants/models.ts`.
4.  Test with integration test (`src/test/integration/integration-cli-flow.test.ts`).

### Modifying Responses API Request
-   Edit `src/services/adapters/responsesAPI.ts`.
-   Run unit tests: `bun test src/test/unit/responses-api-e2e.test.ts`.
-   Run integration test: `bun test src/test/integration/integration-cli-flow.test.ts`.
-   Run production test: `PRODUCTION_TEST_MODE=true bun test src/test/unit/responses-api-e2e.test.ts`.

