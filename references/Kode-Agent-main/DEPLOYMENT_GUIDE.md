# Kode Responses API Support - Deployment Guide

## 🚀 Overview

The new capability-based model system has been successfully implemented to support GPT-5 and other Responses API models. The system replaces hardcoded model detection with a flexible, extensible architecture.

## ✅ What's New

### 1. **Capability-Based Architecture**
- Models are now defined by their capabilities rather than name-based detection
- Automatic API selection (Responses API vs Chat Completions)
- Seamless fallback mechanism for compatibility

### 2. **New Files Created**
```
src/
├── types/modelCapabilities.ts          # Type definitions
├── constants/modelCapabilities.ts      # Model capability registry
├── services/
│   ├── modelAdapterFactory.ts         # Adapter factory
│   └── adapters/                      # Pure adapters
│       ├── base.ts                    # Base adapter class
│       ├── responsesAPI.ts            # Responses API adapter
│       └── chatCompletions.ts         # Chat Completions adapter
└── test/testAdapters.ts               # Test suite
```

### 3. **Supported Models**
- **GPT-5 Series**: gpt-5, gpt-5-mini, gpt-5-nano
- **GPT-4 Series**: gpt-4o, gpt-4o-mini, gpt-4-turbo, gpt-4
- **Claude Series**: All Claude models
- **O1 Series**: o1, o1-mini, o1-preview
- **Future Models**: GPT-6, GLM-5, and more through configuration

## 🔧 How to Use

### Enable the New System

```bash
# Enable new adapter system (default)
export USE_NEW_ADAPTERS=true

# Use legacy system (fallback)
export USE_NEW_ADAPTERS=false
```

### Add Support for New Models

Edit `src/constants/modelCapabilities.ts`:

```typescript
// Add your model to the registry
export const MODEL_CAPABILITIES_REGISTRY: Record<string, ModelCapabilities> = {
  // ... existing models ...
  
  'your-model-name': {
    apiArchitecture: {
      primary: 'responses_api',  // or 'chat_completions'
      fallback: 'chat_completions'  // optional
    },
    parameters: {
      maxTokensField: 'max_completion_tokens',  // or 'max_tokens'
      supportsReasoningEffort: true,
      supportsVerbosity: true,
      temperatureMode: 'flexible'  // or 'fixed_one' or 'restricted'
    },
    toolCalling: {
      mode: 'custom_tools',  // or 'function_calling' or 'none'
      supportsFreeform: true,
      supportsAllowedTools: true,
      supportsParallelCalls: true
    },
    stateManagement: {
      supportsResponseId: true,
      supportsConversationChaining: true,
      supportsPreviousResponseId: true
    },
    streaming: {
      supported: false,
      includesUsage: true
    }
  }
}
```

## 🧪 Testing

### Run Adapter Tests
```bash
npx tsx src/test/testAdapters.ts
```

### Verify TypeScript Compilation
```bash
npx tsc --noEmit
```

## 🏗️ Architecture

### Request Flow
```
User Input
    ↓
query.ts
    ↓
claude.ts (queryLLM)
    ↓
ModelAdapterFactory
    ↓
[Capability Check]
    ↓
ResponsesAPIAdapter or ChatCompletionsAdapter
    ↓
API Call (openai.ts)
    ↓
Response
```

### Key Components

1. **ModelAdapterFactory**: Determines which adapter to use based on model capabilities
2. **ResponsesAPIAdapter**: Handles GPT-5 Responses API format
3. **ChatCompletionsAdapter**: Handles traditional Chat Completions format
4. **Model Registry**: Central configuration for all model capabilities

## 🔄 Migration from Legacy System

The system is designed for zero-downtime migration:

1. **Phase 1** ✅: Infrastructure created (no impact on existing code)
2. **Phase 2** ✅: Integration with environment variable toggle
3. **Phase 3**: Remove legacy hardcoded checks (optional)

## 📊 Performance

- **Zero overhead**: Capabilities are cached after first lookup
- **Smart fallback**: Automatically uses Chat Completions for custom endpoints
- **Streaming aware**: Falls back when streaming is needed but not supported

## 🛡️ Safety Features

1. **100% backward compatible**: Legacy system preserved
2. **Environment variable toggle**: Easy rollback if needed
3. **Graceful degradation**: Falls back to Chat Completions when needed
4. **Type-safe**: Full TypeScript support

## 🎯 Benefits

1. **No more hardcoded model checks**: Clean, maintainable code
2. **Easy to add new models**: Just update the registry
3. **Future-proof**: Ready for GPT-6, GLM-5, and beyond
4. **Unified interface**: Same code handles all API types

## 📝 Notes

- The system automatically detects official OpenAI endpoints
- Custom endpoints automatically use Chat Completions API
- Streaming requirements are handled transparently
- All existing model configurations are preserved

## 🚨 Troubleshooting

### Models not using correct API
- Check if `USE_NEW_ADAPTERS=true` is set
- Verify model is in the registry
- Check if custom endpoint is configured (forces Chat Completions)

### Type errors
- Run `npx tsc --noEmit` to check for issues
- Ensure all imports are correct

### Runtime errors
- Check console for adapter selection logs
- Verify API keys and endpoints are correct

## 📞 Support

For issues or questions:
1. Check the test output: `npx tsx src/test/testAdapters.ts`
2. Review the model registry in `src/constants/modelCapabilities.ts`
3. Check adapter selection logic in `src/services/modelAdapterFactory.ts`

---

**Status**: ✅ Production Ready with Environment Variable Toggle