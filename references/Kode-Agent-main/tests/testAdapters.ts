import { ModelAdapterFactory } from '@services/modelAdapterFactory'
import { ModelProfile } from '@utils/config'

export const testModels: ModelProfile[] = [
  {
    name: 'GPT-5 Test',
    modelName: 'gpt-5',
    provider: 'openai',
    apiKey: 'test-key',
    maxTokens: 8192,
    contextLength: 128000,
    reasoningEffort: 'medium',
    isActive: true,
    createdAt: Date.now(),
  },
  {
    name: 'GPT-4o Test',
    modelName: 'gpt-4o',
    provider: 'openai',
    apiKey: 'test-key',
    maxTokens: 4096,
    contextLength: 128000,
    isActive: true,
    createdAt: Date.now(),
  },
  {
    name: 'Claude Test',
    modelName: 'claude-3-5-sonnet-20241022',
    provider: 'anthropic',
    apiKey: 'test-key',
    maxTokens: 4096,
    contextLength: 200000,
    isActive: true,
    createdAt: Date.now(),
  },
  {
    name: 'O1 Test',
    modelName: 'o1',
    provider: 'openai',
    apiKey: 'test-key',
    maxTokens: 4096,
    contextLength: 128000,
    isActive: true,
    createdAt: Date.now(),
  },
  {
    name: 'GLM-5 Test',
    modelName: 'glm-5',
    provider: 'custom',
    apiKey: 'test-key',
    maxTokens: 8192,
    contextLength: 128000,
    baseURL: 'https://api.glm.ai/v1',
    isActive: true,
    createdAt: Date.now(),
  },
  {
    name: 'MiniMax Codex Test',
    modelName: 'codex-MiniMax-M2',
    provider: 'minimax',
    apiKey: 'test-key',
    maxTokens: 8192,
    contextLength: 128000,
    baseURL: 'https://api.minimaxi.com/v1',
    isActive: true,
    createdAt: Date.now(),
  },
  {
    name: 'DeepSeek Test',
    modelName: 'deepseek-chat',
    provider: 'custom',
    apiKey: 'test-key',
    maxTokens: 4096,
    contextLength: 128000,
    baseURL: 'https://api.deepseek.com/v1',
    isActive: true,
    createdAt: Date.now(),
  },
  {
    name: 'Qwen Test',
    modelName: 'qwen-max',
    provider: 'custom',
    apiKey: 'test-key',
    maxTokens: 8192,
    contextLength: 128000,
    baseURL: 'https://dashscope.aliyuncs.com/api/v1',
    isActive: true,
    createdAt: Date.now(),
  },
]

export const productionTestModels: ModelProfile[] = [
  {
    name: 'GPT-5 Production',
    modelName: process.env.TEST_GPT5_MODEL_NAME || 'gpt-5',
    provider: 'openai',
    apiKey: process.env.TEST_GPT5_API_KEY || '',
    baseURL: process.env.TEST_GPT5_BASE_URL || 'http://127.0.0.1:3000/openai',
    maxTokens: 8192,
    contextLength: 128000,
    reasoningEffort: 'high',
    isActive: !!process.env.TEST_GPT5_API_KEY,
    createdAt: Date.now(),
  },
  {
    name: 'MiniMax Codex Production',
    modelName: process.env.TEST_MINIMAX_MODEL_NAME || 'codex-MiniMax-M2',
    provider: 'minimax',
    apiKey: process.env.TEST_MINIMAX_API_KEY || '',
    baseURL: process.env.TEST_MINIMAX_BASE_URL || 'https://api.minimaxi.com/v1',
    maxTokens: 8192,
    contextLength: 128000,
    isActive: !!process.env.TEST_MINIMAX_API_KEY,
    createdAt: Date.now(),
  },
  {
    name: 'DeepSeek Production',
    modelName: process.env.TEST_DEEPSEEK_MODEL_NAME || 'deepseek-chat',
    provider: 'custom',
    apiKey: process.env.TEST_DEEPSEEK_API_KEY || '',
    baseURL:
      process.env.TEST_DEEPSEEK_BASE_URL || 'https://api.deepseek.com/v1',
    maxTokens: 4096,
    contextLength: 128000,
    isActive: !!process.env.TEST_DEEPSEEK_API_KEY,
    createdAt: Date.now(),
  },
  {
    name: 'Anthropic Claude Production',
    modelName:
      process.env.TEST_CLAUDE_MODEL_NAME || 'claude-3-5-sonnet-20241022',
    provider: 'anthropic',
    apiKey: process.env.TEST_CLAUDE_API_KEY || '',
    baseURL: process.env.TEST_CLAUDE_BASE_URL || 'https://api.anthropic.com',
    maxTokens: 4096,
    contextLength: 200000,
    isActive: !!process.env.TEST_CLAUDE_API_KEY,
    createdAt: Date.now(),
  },
  {
    name: 'GLM Production',
    modelName: process.env.TEST_GLM_MODEL_NAME || 'glm-4.5-air',
    provider: 'custom',
    apiKey: process.env.TEST_GLM_API_KEY || '',
    baseURL:
      process.env.TEST_GLM_BASE_URL || 'https://open.bigmodel.cn/api/paas/v4',
    maxTokens: 8192,
    contextLength: 128000,
    reasoningEffort: 'medium',
    isActive: !!process.env.TEST_GLM_API_KEY,
    createdAt: Date.now(),
  },
]

export function getChatCompletionsModels(
  models: ModelProfile[] = testModels,
): ModelProfile[] {
  return models.filter(model => {
    const shouldUseResponses = ModelAdapterFactory.shouldUseResponsesAPI(model)
    return !shouldUseResponses
  })
}

export function getResponsesAPIModels(
  models: ModelProfile[] = testModels,
): ModelProfile[] {
  return models.filter(model => {
    const shouldUseResponses = ModelAdapterFactory.shouldUseResponsesAPI(model)
    return shouldUseResponses
  })
}
